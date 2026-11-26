"""
optimizer.py - makes the delivery sequence and the loading plan.

Steps inside Optimizer.generate():
    1. Group the staged rows by customer (each customer appears ONCE in the route).
    2. Ask the DistanceService (OSRM) for the road distance/time grids.
    3. Ask Google OR-Tools for the shortest route: leave the depot, visit every customer once,
       come back to the depot. The truck's capacity and the customers' opening hours are respected.
       If the opening hours make a route impossible, we plan without them and WARN the user.
    4. Work out arrival times, then the loading plan (EXACT REVERSE of the delivery order),
       then the metrics.

Node numbers: node 0 = the depot, nodes 1..n = the customers.
Units used inside the solver: distance in metres, time in seconds, weight in grams (whole numbers).
"""
import math
from typing import Dict, List, Optional, Tuple

from ortools.constraint_solver import pywrapcp, routing_enums_pb2

from app import config
from app.services.distance_service import DistanceService
from app.services.draft_plan import (
    DraftItem, DraftPlan, DraftStop, LoadingEntry, PlanMetrics, minutes_to_hhmm,
)
from app.services.errors import PlanningError
from app.services.staging import StagingTable

TWO_DAYS_S = 2 * 24 * 3600
ONE_DAY_S = 24 * 3600


class Optimizer:
    def __init__(self, distance_service: DistanceService, depot_name: str = None,
                 depot_latitude: float = None, depot_longitude: float = None,
                 departure_minute: int = None, service_minutes: int = None,
                 max_seconds: int = None, max_stops: int = None):
        self.distance_service = distance_service
        self.depot_name = depot_name if depot_name is not None else config.DEPOT_NAME
        self.depot_latitude = depot_latitude if depot_latitude is not None else config.DEPOT_LATITUDE
        self.depot_longitude = depot_longitude if depot_longitude is not None else config.DEPOT_LONGITUDE
        self.departure_minute = departure_minute if departure_minute is not None else config.DEPARTURE_TIME_MINUTES
        self.service_minutes = service_minutes if service_minutes is not None else config.SERVICE_MINUTES_PER_STOP
        self.max_seconds = max_seconds if max_seconds is not None else config.OPTIMIZER_MAX_SECONDS
        self.max_stops = max_stops if max_stops is not None else config.MAX_STOPS

    # =====================================================================
    # generate: the main method
    # =====================================================================
    def generate(self, staging: StagingTable, customers_by_id: Dict[int, object]) -> DraftPlan:
        staging.check_ready_to_generate()

        # 1. group the rows by customer, keeping the order they first appear
        groups: Dict[int, list] = {}
        for line in staging.valid_rows:
            groups.setdefault(line.customer_id, []).append(line)
        customer_ids = list(groups.keys())

        if len(customer_ids) > self.max_stops:
            raise PlanningError(
                f"This plan has {len(customer_ids)} customers. The maximum is {self.max_stops} customers per truck."
            )
        for customer_id in customer_ids:
            if customer_id not in customers_by_id:
                raise PlanningError(f"Customer number {customer_id} no longer exists. Fix or delete that row.")

        # 2. road distances and times (node 0 = depot)
        points = [(self.depot_latitude, self.depot_longitude)]
        points += [(customers_by_id[cid].latitude, customers_by_id[cid].longitude) for cid in customer_ids]
        distances_m, durations_s = self.distance_service.get_matrix(points)

        # opening hours for every node, in seconds (the depot has no limit)
        windows_s = [(0, TWO_DAYS_S)]
        for cid in customer_ids:
            customer = customers_by_id[cid]
            windows_s.append((customer.open_time * 60, customer.close_time * 60))

        demands_g = [0] + [
            int(round(sum(line.total_weight for line in groups[cid]) * 1000)) for cid in customer_ids
        ]
        # + 1 gram per stop so rounding to whole grams can never make a legal load look too heavy
        capacity_g = int(round(staging.truck_capacity * 1000)) + len(customer_ids)

        # 3. solve. First WITH opening hours; if impossible, again without them.
        departure_s = self.departure_minute * 60
        service_s = self.service_minutes * 60
        warnings: List[str] = []
        limit_with_windows, limit_without_windows = self._time_limits(len(customer_ids))
        route = self._solve(distances_m, durations_s, windows_s, demands_g, capacity_g,
                            departure_s, service_s, True, limit_with_windows)
        windows_used = route is not None
        if route is None:
            route = self._solve(distances_m, durations_s, windows_s, demands_g, capacity_g,
                                departure_s, service_s, False, limit_without_windows)
        if route is None:
            raise PlanningError("No route could be found for these orders.")
        # Safety check: every customer must be visited exactly once. Never hand back a half plan.
        if sorted(route) != list(range(1, len(customer_ids) + 1)):
            raise PlanningError("The route solver did not visit every customer, so no plan was made.")

        # 4. arrival times, stops, loading plan, metrics
        schedule, back_at_depot_s = self.calculate_schedule(route, durations_s, windows_s, departure_s, service_s)

        stops: List[DraftStop] = []
        previous_node = 0
        for position, node in enumerate(route, start=1):
            customer = customers_by_id[customer_ids[node - 1]]
            lines = groups[customer.customer_id]
            arrival_s, start_s, window_ok = schedule[position - 1]
            items = [DraftItem(line.product, line.quantity, line.unit_weight, line.total_weight) for line in lines]
            stop = DraftStop(
                stop_id=customer.customer_id, 
                stop_sequence=position,
                customer_id=customer.customer_id,
                customer_name=customer.customer_name,
                town=customer.town,
                latitude=customer.latitude,      # <--- ADD THIS
                longitude=customer.longitude,
                items=items,
                stop_weight=round(sum(item.total_weight for item in items), 3),
                leg_distance_km=round(distances_m[previous_node][node] / 1000, 1),
                leg_travel_minutes=round(durations_s[previous_node][node] / 60, 1),
                arrival_minute=int(round(arrival_s / 60)),
                arrival_time=minutes_to_hhmm(arrival_s / 60),
                window_open=customer.open_time,
                window_close=customer.close_time,
                window_ok=window_ok,
            )
            stops.append(stop)
            if not window_ok:
                warnings.append(
                    f"{customer.customer_name}: the truck arrives at {stop.arrival_time} but the customer closes at "
                    f"{minutes_to_hhmm(customer.close_time)}."
                )
            previous_node = node

        if not windows_used:
            warnings.insert(0, "The customers' opening hours could not all be met, so the route was planned "
                               "for the shortest distance only. Check the warnings below.")

        loading_plan = self.build_loading_plan(stops)
        windows_respected = all(stop.window_ok for stop in stops)
        metrics = self.calculate_metrics(route, distances_m, durations_s, staging.total_weight, windows_respected)

        return DraftPlan(
            truck_id=staging.truck_id,
            truck_license_plate=staging.truck_license_plate,
            truck_capacity=staging.truck_capacity,
            depot_name=self.depot_name,
            depot_latitude=self.depot_latitude,     
            depot_longitude=self.depot_longitude,
            stops=stops,
            loading_plan=loading_plan,
            metrics=metrics,
            original_metrics=PlanMetrics(**vars(metrics)),     # a separate copy
            return_leg_distance_km=round(distances_m[previous_node][0] / 1000, 1),
            return_leg_travel_minutes=round(durations_s[previous_node][0] / 60, 1),
            finish_time=minutes_to_hhmm(back_at_depot_s / 60),
            warnings=warnings,
            node_customer_ids=[0] + customer_ids,
            distance_matrix_m=distances_m,
            duration_matrix_s=durations_s,
        )

    # =====================================================================
    # the OR-Tools route solver
    # =====================================================================
    def _time_limits(self, stop_count: int) -> Tuple[int, int]:
        """How many seconds each attempt may think: (with opening hours, without them).

        The two attempts SHARE one budget (OPTIMIZER_MAX_SECONDS), so even in the worst case
        the whole optimization stays well inside the 40-second requirement (OSRM time is extra).
        """
        if stop_count <= 10:
            return 5, 5                       # small plans are solved almost instantly anyway
        total = max(2, min(self.max_seconds, stop_count))
        with_windows = max(1, int(total * 0.6))
        return with_windows, max(1, total - with_windows)

    def _solve(self, distances_m, durations_s, windows_s, demands_g, capacity_g,
               departure_s, service_s, use_windows: bool, time_limit_seconds: int) -> Optional[List[int]]:
        """Return the customer nodes in visiting order, or None if there is no solution."""
        node_count = len(distances_m)
        stop_count = node_count - 1

        manager = pywrapcp.RoutingIndexManager(node_count, 1, 0)   # 1 truck, depot = node 0
        routing = pywrapcp.RoutingModel(manager)

        # What we want to make small: the total distance driven
        def distance_callback(from_index, to_index):
            return int(round(distances_m[manager.IndexToNode(from_index)][manager.IndexToNode(to_index)]))

        distance_index = routing.RegisterTransitCallback(distance_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(distance_index)

        # Capacity rule: the weight on the truck can never go over its capacity
        def demand_callback(from_index):
            return demands_g[manager.IndexToNode(from_index)]

        demand_index = routing.RegisterUnaryTransitCallback(demand_callback)
        routing.AddDimensionWithVehicleCapacity(demand_index, 0, [capacity_g], True, "Capacity")

        # Opening hours rule (only when use_windows is True)
        if use_windows:
            def time_callback(from_index, to_index):
                from_node = manager.IndexToNode(from_index)
                to_node = manager.IndexToNode(to_index)
                offloading = service_s if from_node != 0 else 0
                return int(round(durations_s[from_node][to_node])) + offloading

            time_index = routing.RegisterTransitCallback(time_callback)
            # slack = waiting time allowed when the truck arrives before a customer opens
            routing.AddDimension(time_index, ONE_DAY_S, TWO_DAYS_S, False, "Time")
            time_dimension = routing.GetDimensionOrDie("Time")
            time_dimension.CumulVar(routing.Start(0)).SetRange(departure_s, departure_s)
            for node in range(1, node_count):
                opens, closes = windows_s[node]
                time_dimension.CumulVar(manager.NodeToIndex(node)).SetRange(opens, closes)

        # How hard to search
        parameters = pywrapcp.DefaultRoutingSearchParameters()
        parameters.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        if stop_count <= 10:
            # small plans: a quick descent is enough
            parameters.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GREEDY_DESCENT
        else:
            # bigger plans: keep improving until the time limit
            parameters.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        parameters.time_limit.seconds = time_limit_seconds

        solution = routing.SolveWithParameters(parameters)
        if solution is None:
            return None

        order = []
        index = routing.Start(0)
        while not routing.IsEnd(index):
            node = manager.IndexToNode(index)
            if node != 0:
                order.append(node)
            index = solution.Value(routing.NextVar(index))
        return order

    # =====================================================================
    # pure helper methods (no OR-Tools, easy to test, reused by Sprint 3)
    # =====================================================================
    @staticmethod
    def calculate_schedule(route: List[int], durations_s, windows_s, departure_s: int,
                           service_s: int) -> Tuple[List[Tuple[float, float, bool]], float]:
        """Walk along the route and work out the times.

        Returns ([(arrival, service_start, window_ok), ...], time_back_at_depot) in seconds.
        If the truck arrives before the customer opens it waits until opening time.
        """
        clock = departure_s
        previous = 0
        result = []
        for node in route:
            clock += durations_s[previous][node]
            arrival = clock
            opens, closes = windows_s[node]
            service_start = max(arrival, opens)
            result.append((arrival, service_start, service_start <= closes))
            clock = service_start + service_s
            previous = node
        clock += durations_s[previous][0]
        return result, clock

    @staticmethod
    def build_loading_plan(stops: List[DraftStop]) -> List[LoadingEntry]:
        """The loading order is the EXACT REVERSE of the delivery order.

        The LAST customer's goods are loaded FIRST (deepest in the truck) and the FIRST
        customer's goods are loaded LAST (next to the doors). loading_sequence 1 = first loaded.
        """
        plan: List[LoadingEntry] = []
        sequence = 1
        for stop in reversed(stops):
            for item in stop.items:
                item.loading_sequence = sequence
                plan.append(LoadingEntry(
                    loading_sequence=sequence,
                    stop_sequence=stop.stop_sequence,
                    customer_name=stop.customer_name,
                    product=item.product,
                    quantity=item.quantity,
                    total_weight=item.total_weight,
                ))
                sequence += 1
        return plan

    @staticmethod
    def calculate_metrics(route: List[int], distances_m, durations_s, total_weight: float,
                          time_windows_respected: bool) -> PlanMetrics:
        """Total distance and driving time of the whole round trip (depot -> stops -> depot)."""
        distance = 0.0
        duration = 0.0
        previous = 0
        for node in route + [0]:
            distance += distances_m[previous][node]
            duration += durations_s[previous][node]
            previous = node
        return PlanMetrics(
            total_distance_km=round(distance / 1000, 1),
            total_travel_minutes=round(duration / 60, 1),
            total_weight=round(total_weight, 3),
            stops_count=len(route),
            time_windows_respected=time_windows_respected,
        )
