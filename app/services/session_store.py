"""
session_store.py - the server-side "session storage".

Each logged-in user has ONE working session holding:
    * the staging table (truck + order rows)
    * the draft plan

It lives in the server's memory, not in the database. Only an approved plan is saved
to the database (Sprint 3). The session is removed on logout, and after
INACTIVITY_TIMEOUT_MINUTES without activity.

Limits (fine for a diploma project): everything is lost if the server restarts, and it only
works with ONE server process (do not start uvicorn with --workers).
"""
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, Optional

from app import config
from app.services.draft_plan import DraftPlan
from app.services.staging import StagingTable


@dataclass
class UserSession:
    staging: StagingTable = field(default_factory=StagingTable)
    draft: Optional[DraftPlan] = None
    last_activity: float = 0.0

    def touch(self):
        """Update the timestamp so the session doesn't expire."""
        self.last_activity = time.time()

    def reorder_stop_sequence(self, new_stop_ids: list):
        if not self.draft:
            return
        
        # Map the old stops by CUSTOMER ID (since that's what the frontend is sending)
        stop_dict = {s.customer_id: s for s in self.draft.stops}
        
        # Rebuild the stop list in the new order
        try:
            self.draft.stops = [stop_dict[sid] for sid in new_stop_ids]
        except KeyError as e:
            raise ValueError(f"Customer ID {e} not found in draft.")
            
        # Renumber the sequences (1, 2, 3...)
        for i, s in enumerate(self.draft.stops, start=1):
            s.stop_sequence = i
            
        # Recalculate the loading plan (Reverse Order)
        from app.services.optimizer import Optimizer
        self.draft.loading_plan = Optimizer.build_loading_plan(self.draft.stops)
        
        # Recalculate the metrics
        route_nodes = []
        for stop in self.draft.stops:
            node_idx = self.draft.node_customer_ids.index(stop.customer_id)
            route_nodes.append(node_idx)
            
        self.draft.metrics = Optimizer.calculate_metrics(
            route=route_nodes,
            distances_m=self.draft.distance_matrix_m,
            durations_s=self.draft.duration_matrix_s,
            total_weight=self.draft.metrics.total_weight,
            time_windows_respected=self.draft.metrics.time_windows_respected
        )


class SessionStore:
    def __init__(self, timeout_minutes: Optional[int] = None, clock: Callable[[], float] = time.time):
        # "clock" can be replaced in tests, so we can pretend time passes
        self.timeout_seconds = (timeout_minutes or config.SESSION_TIMEOUT_MINUTES) * 60
        self.clock = clock
        self._sessions: Dict[int, UserSession] = {}
        self._lock = threading.Lock()   # FastAPI can run several requests at once

    def get(self, user_id: int) -> UserSession:
        """Return the user's session. Creates a new empty one if there is none or it expired."""
        now = self.clock()
        with self._lock:
            session = self._sessions.get(user_id)
            if session is None or now - session.last_activity > self.timeout_seconds:
                session = UserSession()
                self._sessions[user_id] = session
            session.last_activity = now
            return session

    def clear(self, user_id: int) -> None:
        """Forget everything for this user (used by logout)."""
        with self._lock:
            self._sessions.pop(user_id, None)

    def purge_expired(self) -> int:
        """Remove sessions nobody has used for a long time. Returns how many were removed."""
        now = self.clock()
        with self._lock:
            old_ids = [uid for uid, s in self._sessions.items() if now - s.last_activity > self.timeout_seconds]
            for uid in old_ids:
                del self._sessions[uid]
            return len(old_ids)


# One shared store for the whole running application
_store = SessionStore()


def get_session_store() -> SessionStore:
    """FastAPI dependency. Tests replace it with a fresh store."""
    return _store
