"""
permissions.py - which role may do what.

The class diagram says: Administrator extends Dispatcher. In plain words, an
Administrator can do EVERYTHING a Dispatcher can do, plus record maintenance.
We show that with a level number: a higher level includes all lower levels.
"""
ADMINISTRATOR = "administrator"
DISPATCHER = "dispatcher"

ROLE_LEVEL = {
    DISPATCHER: 1,
    ADMINISTRATOR: 2,
}


def has_role(user_role: str, minimum_role: str) -> bool:
    """True if user_role is the same as, or higher than, minimum_role."""
    return ROLE_LEVEL.get(user_role, 0) >= ROLE_LEVEL[minimum_role]
