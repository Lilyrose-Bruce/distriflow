"""
staging.py - the STAGING TABLE: the list of order rows being prepared for one truck.

Classes (from the class diagram):
    CustomerLookup  - finds customers by name or id (built from the database)
    OrderLine       - ONE row: a product ordered by ONE customer. It can check itself.
    StagingTable    - the truck + all rows. Add / edit / delete rows, total weight, capacity.

Important rules (from the report):
    * Invalid rows are FLAGGED, kept in the table, and NOT counted until fixed or deleted.
    * Every error message names the row and the problem.
    * Row numbers match the spreadsheet (header = row 1).
"""
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from app.services.errors import PlanningError

TOTAL_TOLERANCE = 0.01   # how far a stated total may differ from quantity x unit weight


def parse_number(text) -> Optional[float]:
    """Turn text into a number, or return None if it is not a (finite) number."""
    try:
        number = float(str(text).strip())
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


class CustomerLookup:
    """Finds customers by id or by name. Names are matched ignoring upper/lower case."""

    def __init__(self, customers):
        self.by_id = {c.customer_id: c for c in customers}
        self.by_name: Dict[str, list] = {}
        for customer in customers:
            self.by_name.setdefault(customer.customer_name.strip().lower(), []).append(customer)


@dataclass
class OrderLine:
    row_id: int
    source: str                          # "file" or "manual"
    customer_name: str = ""
    customer_id: Optional[int] = None
    product: str = ""
    # What the user typed or the file contained, kept as TEXT so we can quote it in messages
    raw_quantity: str = ""
    raw_unit_weight: str = ""
    raw_total_weight: str = ""           # "" = no total given
    # Filled in by validate():
    quantity: Optional[int] = None
    unit_weight: Optional[float] = None
    total_weight: Optional[float] = None
    town: str = ""
    errors: List[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.errors

    def validate(self, lookup: CustomerLookup) -> None:
        """Check this row and fill errors, quantity, unit_weight, total_weight, customer."""
        self.errors = []
        self.quantity = self.unit_weight = self.total_weight = None
        label = f"Row {self.row_id}"

        # ---- customer must exist in the customer records ----
        customer = None
        if self.customer_id is not None:
            customer = lookup.by_id.get(self.customer_id)
            if customer is None:
                self.errors.append(f"{label}: customer number {self.customer_id} was not found in the customer records.")
        elif not self.customer_name.strip():
            self.errors.append(f"{label}: the customer name is missing.")
        else:
            matches = lookup.by_name.get(self.customer_name.strip().lower(), [])
            if len(matches) == 0:
                self.errors.append(f"{label}: customer '{self.customer_name}' was not found in the customer records.")
            elif len(matches) > 1:
                self.errors.append(
                    f"{label}: customer name '{self.customer_name}' matches {len(matches)} customers. "
                    "Choose the customer from the list."
                )
            else:
                customer = matches[0]
        if customer is not None:
            self.customer_id = customer.customer_id
            self.customer_name = customer.customer_name
            self.town = customer.town

        # ---- product ----
        if not self.product.strip():
            self.errors.append(f"{label}: the product is missing.")

        # ---- quantity: a whole number, more than 0 ----
        quantity = parse_number(self.raw_quantity)
        if self.raw_quantity.strip() == "":
            self.errors.append(f"{label}: the quantity is missing.")
        elif quantity is None:
            self.errors.append(f"{label}: quantity must be a whole number (found '{self.raw_quantity}').")
        elif quantity < 0:
            self.errors.append(f"{label}: quantity cannot be negative (found {quantity:g}).")
        elif quantity == 0:
            self.errors.append(f"{label}: quantity must be greater than 0.")
        elif abs(quantity - round(quantity)) > 1e-9:
            self.errors.append(f"{label}: quantity must be a whole number (found {quantity:g}).")
        else:
            self.quantity = int(round(quantity))

        # ---- unit weight: a number, more than 0 ----
        unit_weight = parse_number(self.raw_unit_weight)
        if self.raw_unit_weight.strip() == "":
            self.errors.append(f"{label}: the unit weight is missing.")
        elif unit_weight is None:
            self.errors.append(f"{label}: unit weight must be a number (found '{self.raw_unit_weight}').")
        elif unit_weight <= 0:
            self.errors.append(f"{label}: unit weight must be greater than 0 (found {unit_weight:g}).")
        else:
            self.unit_weight = unit_weight

        # ---- total weight: calculated, and must match the total in the file (if there is one) ----
        if self.quantity is not None and self.unit_weight is not None:
            calculated = self.quantity * self.unit_weight
            self.total_weight = round(calculated, 3)
            if self.raw_total_weight.strip() != "":
                stated = parse_number(self.raw_total_weight)
                if stated is None:
                    self.errors.append(f"{label}: total weight must be a number (found '{self.raw_total_weight}').")
                elif abs(stated - calculated) > TOTAL_TOLERANCE:
                    self.errors.append(
                        f"{label}: total weight {stated:g} does not match quantity x unit weight "
                        f"({self.quantity} x {self.unit_weight:g} = {calculated:g})."
                    )


class StagingTable:
    """The truck and the order rows for one plan."""

    def __init__(self):
        self.truck_id: Optional[int] = None
        self.truck_license_plate: str = ""
        self.truck_capacity: float = 0.0
        self.rows: List[OrderLine] = []
        self.next_row_id: int = 1

    # ---------------- truck ----------------
    def set_truck(self, truck) -> None:
        self.truck_id = truck.truck_id
        self.truck_license_plate = truck.license_plate
        self.truck_capacity = float(truck.max_weight_capacity)

    # ---------------- rows ----------------
    def replace_rows(self, lines: List[OrderLine], lookup: CustomerLookup) -> None:
        """Used by file upload: the new file replaces all current rows."""
        for line in lines:
            line.validate(lookup)
        self.rows = lines
        self.next_row_id = max([line.row_id for line in lines], default=0) + 1

    def add_row(self, customer_name: str, product: str, quantity, unit_weight, lookup: CustomerLookup) -> OrderLine:
        line = OrderLine(
            row_id=self.next_row_id,
            source="manual",
            customer_name=customer_name,
            product=product,
            raw_quantity=str(quantity),
            raw_unit_weight=str(unit_weight),
        )
        self.next_row_id += 1
        line.validate(lookup)
        self.rows.append(line)
        return line

    def find_row(self, row_id: int) -> Optional[OrderLine]:
        line = None
        for l in self.rows:
            if l.row_id == row_id:
                line = l
                return line
        return None

    def edit_row(self, row_id: int, lookup: CustomerLookup, customer_name=None, product=None,
                 quantity=None, unit_weight=None) -> OrderLine:
        """Change a row. Only the values you pass are changed. The total is always recalculated."""
        line = self.find_row(row_id)
        if line is None:
            raise KeyError(row_id)
        if customer_name is not None:
            # Find the customer ID using the existing by_name dictionary
            matches = lookup.by_name.get(customer_name.strip().lower(), [])
            if matches:
                line.customer_id = matches[0].customer_id
            else:
                # If the name isn't found, set ID to None so validation flags it later
                line.customer_id = None
                line.customer_name = customer_name
        if product is not None:
            line.product = product
        if quantity is not None:
            line.raw_quantity = str(quantity)
        if unit_weight is not None:
            line.raw_unit_weight = str(unit_weight)
        line.raw_total_weight = ""       # editing a row means "use the calculated total"
        line.validate(lookup)
        return line

    def delete_row(self, row_id: int) -> bool:
        line = self.find_row(row_id)
        if line is None:
            return False
        self.rows.remove(line)
        return True

    def clear(self) -> None:
        self.__init__()

    # ---------------- weights and capacity ----------------
    @property
    def valid_rows(self) -> List[OrderLine]:
        return [line for line in self.rows if line.is_valid]

    @property
    def error_count(self) -> int:
        return len([line for line in self.rows if not line.is_valid])

    @property
    def total_weight(self) -> float:
        """Total weight of VALID rows only. Rows with errors are not counted."""
        return round(sum(line.total_weight for line in self.valid_rows), 3)

    @property
    def is_within_capacity(self) -> bool:
        return self.truck_id is not None and self.total_weight <= self.truck_capacity

    @property
    def space_left(self) -> float:
        return round(max(0.0, self.truck_capacity - self.total_weight), 3)

    @property
    def percent_used(self) -> float:
        if self.truck_capacity <= 0:
            return 0.0
        return round(self.total_weight / self.truck_capacity * 100, 1)

    def capacity_message(self) -> Optional[str]:
        if self.truck_id is not None and self.total_weight > self.truck_capacity:
            over = self.total_weight - self.truck_capacity
            return (f"The staged weight ({self.total_weight:g} kg) is more than the truck capacity "
                    f"({self.truck_capacity:g} kg) by {over:g} kg. Remove or reduce some orders.")
        return None

    def messages(self) -> List[str]:
        """Every problem the user must know about: row errors first, then capacity."""
        result = [error for line in self.rows for error in line.errors]
        capacity = self.capacity_message()
        if capacity:
            result.append(capacity)
        return result

    # ---------------- ready to generate? ----------------
    def check_ready_to_generate(self) -> None:
        """Raise PlanningError (with a clear message) if a plan cannot be generated yet."""
        if self.truck_id is None:
            raise PlanningError("Select a truck before generating a plan.")
        if not self.rows:
            raise PlanningError("There are no orders. Upload an order file or add a row first.")
        if self.error_count > 0:
            raise PlanningError(f"Fix or delete the {self.error_count} row(s) with errors before generating a plan.")
        capacity = self.capacity_message()
        if capacity:
            raise PlanningError(capacity)

    @property
    def can_generate(self) -> bool:
        try:
            self.check_ready_to_generate()
        except PlanningError:
            return False
        return True
