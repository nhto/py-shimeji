"""Unit tests for PetStateMachine transitions."""

from __future__ import annotations

from states import PetState, PetStateMachine


def test_force_state_notifies_listener(qapp) -> None:
    changes: list[tuple[PetState, PetState]] = []

    def on_change(old: PetState, new: PetState) -> None:
        changes.append((old, new))

    machine = PetStateMachine(on_state_changed=on_change)
    machine._behavior_timer.stop()

    machine.force_state(PetState.SIT)
    assert machine.state == PetState.SIT
    assert changes[-1] == (PetState.WALKING, PetState.SIT)


def test_begin_cursor_chase_enters_chase_state(qapp) -> None:
    machine = PetStateMachine(on_state_changed=lambda *_: None)
    machine._behavior_timer.stop()
    machine.force_state(PetState.IDLE)

    machine.begin_cursor_chase()
    assert machine.state == PetState.CHASING_CURSOR


def test_idle_transitions_to_walk_when_timer_expires(qapp) -> None:
    changes: list[tuple[PetState, PetState]] = []
    machine = PetStateMachine(on_state_changed=lambda old, new: changes.append((old, new)))
    machine._behavior_timer.stop()
    machine.force_state(PetState.IDLE)
    machine._next_idle_walk_ms = 100
    machine._next_sit_ms = 99_999

    machine._on_behavior_tick()
    assert machine.state == PetState.WALKING
    assert changes[-1] == (PetState.IDLE, PetState.WALKING)


def test_idle_transitions_to_sit_before_walk(qapp) -> None:
    machine = PetStateMachine(on_state_changed=lambda *_: None)
    machine._behavior_timer.stop()
    machine.force_state(PetState.IDLE)
    machine._next_sit_ms = 100
    machine._next_idle_walk_ms = 99_999

    machine._on_behavior_tick()
    assert machine.state == PetState.SIT


def test_paused_skips_behavior_tick(qapp) -> None:
    machine = PetStateMachine(on_state_changed=lambda *_: None)
    machine._behavior_timer.stop()
    machine.force_state(PetState.IDLE)
    machine.pause()
    machine._next_idle_walk_ms = 0

    machine._on_behavior_tick()
    assert machine.state == PetState.IDLE


def test_set_direction_rejects_invalid_values(qapp) -> None:
    machine = PetStateMachine(on_state_changed=lambda *_: None)
    try:
        machine.set_direction(0)
        raised = False
    except ValueError:
        raised = True
    assert raised


def test_begin_sit_for_uses_fixed_duration(qapp) -> None:
    machine = PetStateMachine(on_state_changed=lambda *_: None)
    machine._behavior_timer.stop()
    machine.force_state(PetState.WALKING)

    machine.begin_sit_for(1_500)
    assert machine.state == PetState.SIT
    assert machine._next_idle_walk_ms == 1_500
