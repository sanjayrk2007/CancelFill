from typing import Dict, Set

class InvalidTransition(Exception):
    def __init__(self, entity: str, from_state: str, to_state: str) -> None:
        self.entity = entity
        self.from_state = from_state
        self.to_state = to_state
        super().__init__(f"Invalid transition for {entity}: {from_state} -> {to_state}")

class OfferExpired(Exception):
    def __init__(self, message: str = "This offer is no longer available") -> None:
        super().__init__(message)

class NotFoundError(Exception):
    pass

SLOT_TRANSITIONS: Dict[str, Set[str]] = {
    "AVAILABLE": {"BOOKED", "HELD"},
    "BOOKED": {"AVAILABLE"},
    "HELD": {"BOOKED", "AVAILABLE"},
}

HOLD_TRANSITIONS: Dict[str, Set[str]] = {
    "ACTIVE": {"CONFIRMED", "EXPIRED", "DECLINED"},
}

WAITLIST_TRANSITIONS: Dict[str, Set[str]] = {
    "WAITING": {"OFFERED", "CANCELLED"},
    "OFFERED": {"CONFIRMED", "DECLINED", "EXPIRED"},
}

BOOKING_TRANSITIONS: Dict[str, Set[str]] = {
    "CONFIRMED": {"CANCELLED"},
}

ENTITY_TRANSITIONS: Dict[str, Dict[str, Set[str]]] = {
    "Slot": SLOT_TRANSITIONS,
    "Hold": HOLD_TRANSITIONS,
    "WaitlistEntry": WAITLIST_TRANSITIONS,
    "Booking": BOOKING_TRANSITIONS,
}

def assert_transition(arg1: str, arg2: str, arg3: str | None = None) -> None:
    if arg3 is not None:
        entity = arg1
        current_state = arg2
        next_state = arg3
        allowed = ENTITY_TRANSITIONS.get(entity, {}).get(current_state, set())
        if next_state not in allowed:
            raise InvalidTransition(entity, current_state, next_state)
    else:
        current_state = arg1
        next_state = arg2
        found_entity = None
        for ent, trans in ENTITY_TRANSITIONS.items():
            if current_state in trans:
                found_entity = ent
                if next_state in trans[current_state]:
                    return
        raise InvalidTransition(found_entity or "Entity", current_state, next_state)
