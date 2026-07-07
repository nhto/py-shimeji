"""Finite state machine for Shimeji pet behavior."""

from __future__ import annotations

import random
from enum import Enum, auto
from typing import Callable

from PyQt6.QtCore import QObject, QTimer

from config import (
    BEHAVIOR_INTERVAL_MS,
    IDLE_TO_SIT_MAX_MS,
    IDLE_TO_SIT_MIN_MS,
    IDLE_TO_WALK_MAX_MS,
    IDLE_TO_WALK_MIN_MS,
    SIT_TO_IDLE_MAX_MS,
    SIT_TO_IDLE_MIN_MS,
    WALK_TO_IDLE_MAX_MS,
    WALK_TO_IDLE_MIN_MS,
)


class PetState(Enum):
    """Distinct behavioral modes for the desktop pet."""

    IDLE = auto()
    SIT = auto()
    WALKING = auto()
    CHASING_CURSOR = auto()
    CLIMBING = auto()
    FALLING = auto()
    DRAGGED = auto()


class PetStateMachine(QObject):
    """
    Manages pet behavior state transitions.

    DRAGGED and FALLING are entered externally (user input / physics).
    IDLE, SIT, and WALKING transition randomly on a timer when not interrupted.
    """

    def __init__(
        self,
        on_state_changed: Callable[[PetState, PetState], None],
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._state: PetState = PetState.WALKING
        self._direction: int = 1  # 1 = right, -1 = left
        self._on_state_changed = on_state_changed
        self._paused: bool = False
        self._next_idle_walk_ms: int = self._random_walk_duration()
        self._next_sit_ms: int = self._random_idle_to_sit_duration()

        self._behavior_timer = QTimer(self)
        self._behavior_timer.setInterval(BEHAVIOR_INTERVAL_MS)
        self._behavior_timer.timeout.connect(self._on_behavior_tick)
        self._behavior_timer.start()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def state(self) -> PetState:
        return self._state

    @property
    def direction(self) -> int:
        """Horizontal facing: 1 (right) or -1 (left)."""
        return self._direction

    def flip_direction(self) -> None:
        self._direction *= -1

    def set_direction(self, direction: int) -> None:
        if direction not in (-1, 1):
            raise ValueError("direction must be -1 or 1")
        self._direction = direction

    def pause(self) -> None:
        """Pause automatic IDLE/WALK transitions (e.g. while dragged)."""
        self._paused = True

    def resume(self) -> None:
        """Resume automatic behavior after drag ends."""
        self._paused = False
        self._reset_idle_timers()

    def force_state(self, new_state: PetState) -> None:
        """Immediately transition without going through random logic."""
        if new_state == PetState.IDLE:
            self._reset_idle_timers()
        self._transition(new_state)

    def begin_walking(self) -> None:
        """Resume horizontal movement with a fresh walk duration."""
        self._next_idle_walk_ms = self._random_walk_duration()
        self._transition(PetState.WALKING)

    def begin_sit(self) -> None:
        """Sit in place until the sit timer expires (e.g. user right-click)."""
        self._next_idle_walk_ms = self._random_sit_duration()
        self._transition(PetState.SIT)

    def begin_sit_for(self, duration_ms: int) -> None:
        """Sit for a fixed duration (e.g. double-click poke)."""
        self._next_idle_walk_ms = max(BEHAVIOR_INTERVAL_MS, duration_ms)
        self._transition(PetState.SIT)

    def begin_cursor_chase(self) -> None:
        """Walk toward the mouse cursor on the current ledge."""
        self._transition(PetState.CHASING_CURSOR)

    def extend_sit(self) -> None:
        """Reset the sit timer (e.g. while sitting under a still cursor)."""
        if self._state == PetState.SIT:
            self._next_idle_walk_ms = self._random_sit_duration()

    def notify_boundary_hit(self) -> None:
        """Called when the pet reaches a horizontal screen edge while walking."""
        if self._state == PetState.WALKING:
            self._next_idle_walk_ms = self._random_walk_duration()

    # ------------------------------------------------------------------
    # Internal behavior loop
    # ------------------------------------------------------------------

    def _on_behavior_tick(self) -> None:
        if self._paused or self._state in (
            PetState.DRAGGED,
            PetState.FALLING,
            PetState.CLIMBING,
            PetState.CHASING_CURSOR,
        ):
            return

        if self._state == PetState.IDLE:
            self._next_idle_walk_ms -= BEHAVIOR_INTERVAL_MS
            self._next_sit_ms -= BEHAVIOR_INTERVAL_MS

            if self._next_sit_ms <= 0:
                self._transition(PetState.SIT)
                self._next_idle_walk_ms = self._random_sit_duration()
                return

            if self._next_idle_walk_ms <= 0:
                self._transition(PetState.WALKING)
                self._next_idle_walk_ms = self._random_walk_duration()
                self._next_sit_ms = self._random_idle_to_sit_duration()
            return

        if self._state == PetState.SIT:
            self._next_idle_walk_ms -= BEHAVIOR_INTERVAL_MS
            if self._next_idle_walk_ms <= 0:
                self._transition(PetState.WALKING)
                self._next_idle_walk_ms = self._random_walk_duration()
                self._next_sit_ms = self._random_idle_to_sit_duration()
            return

        if self._state == PetState.WALKING:
            self._next_idle_walk_ms -= BEHAVIOR_INTERVAL_MS
            if self._next_idle_walk_ms <= 0:
                self._transition(PetState.IDLE)
                self._reset_idle_timers()

    def _transition(self, new_state: PetState) -> None:
        if new_state == self._state:
            return
        old_state = self._state
        self._state = new_state
        self._on_state_changed(old_state, new_state)

    def _reset_idle_timers(self) -> None:
        self._next_idle_walk_ms = self._random_idle_duration()
        self._next_sit_ms = self._random_idle_to_sit_duration()

    @staticmethod
    def _random_idle_duration() -> int:
        return random.randint(IDLE_TO_WALK_MIN_MS, IDLE_TO_WALK_MAX_MS)

    @staticmethod
    def _random_walk_duration() -> int:
        return random.randint(WALK_TO_IDLE_MIN_MS, WALK_TO_IDLE_MAX_MS)

    @staticmethod
    def _random_idle_to_sit_duration() -> int:
        return random.randint(IDLE_TO_SIT_MIN_MS, IDLE_TO_SIT_MAX_MS)

    @staticmethod
    def _random_sit_duration() -> int:
        return random.randint(SIT_TO_IDLE_MIN_MS, SIT_TO_IDLE_MAX_MS)
