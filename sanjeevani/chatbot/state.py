from dataclasses import dataclass, field
from typing import Any


@dataclass
class ConversationState:
    intent: str | None = None
    step: str = "start"
    data: dict[str, Any] = field(default_factory=dict)


_states: dict[int, ConversationState] = {}


def get_state(patient_id: int) -> ConversationState:
    if patient_id not in _states:
        _states[patient_id] = ConversationState()
    return _states[patient_id]


def reset_state(patient_id: int):
    _states[patient_id] = ConversationState()


def update_state(
    patient_id: int,
    *,
    intent: str | None = None,
    step: str | None = None,
    **data,
):
    state = get_state(patient_id)

    if intent is not None:
        state.intent = intent

    if step is not None:
        state.step = step

    state.data.update(data)

    return state
