"""
errors.py - the three kinds of "expected" problems in Sprint 2.

An exception is Python's way of saying "stop, something went wrong". We make our own
so the routers can turn each one into a clear message for the user.
"""


class FileReadError(Exception):
    """The uploaded file cannot be used (wrong type, missing columns, empty...)."""


class PlanningError(Exception):
    """The plan cannot be made (no rows, errors left, over capacity, too many stops...)."""


class DistanceServiceError(Exception):
    """The road-distance service (OSRM) failed or gave an answer we cannot use."""
