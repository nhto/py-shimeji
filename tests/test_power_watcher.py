"""Unit tests for system sleep hide/restore behavior."""

from __future__ import annotations

from dataclasses import dataclass

from power_watcher import (
    PBT_APMSUSPEND,
    PBT_APMRESUMECRITICAL,
    PBT_APMRESUMESUSPEND,
    PowerStateWatcher,
)


@dataclass
class FakePet:
    visible: bool = True
    show_calls: int = 0
    hide_calls: int = 0

    def isVisible(self) -> bool:
        return self.visible

    def show(self) -> None:
        self.show_calls += 1
        self.visible = True

    def hide(self) -> None:
        self.hide_calls += 1
        self.visible = False


def _make_watcher(pets: list[FakePet]) -> PowerStateWatcher:
    watcher = PowerStateWatcher([], parent=None)
    watcher._enabled = False
    watcher._filter = None
    watcher.set_pets(pets)  # type: ignore[arg-type]
    return watcher


def test_suspend_hides_visible_pets_and_resume_restores() -> None:
    visible_pet = FakePet(visible=True)
    hidden_pet = FakePet(visible=False)
    watcher = _make_watcher([visible_pet, hidden_pet])

    assert watcher.handle_power_event(PBT_APMSUSPEND) is True
    assert visible_pet.visible is False
    assert visible_pet.hide_calls == 1
    assert hidden_pet.hide_calls == 0

    assert watcher.handle_power_event(PBT_APMRESUMESUSPEND) is True
    assert visible_pet.visible is True
    assert visible_pet.show_calls == 1
    assert hidden_pet.show_calls == 0


def test_resume_critical_restores_visibility() -> None:
    pet = FakePet(visible=True)
    watcher = _make_watcher([pet])

    watcher.handle_power_event(PBT_APMSUSPEND)
    pet.show_calls = 0

    assert watcher.handle_power_event(PBT_APMRESUMECRITICAL) is True
    assert pet.visible is True
    assert pet.show_calls == 1


def test_unknown_power_event_is_ignored() -> None:
    pet = FakePet(visible=True)
    watcher = _make_watcher([pet])

    assert watcher.handle_power_event(0x9999) is False
    assert pet.visible is True


def test_repeat_suspend_and_resume_are_idempotent() -> None:
    pet = FakePet(visible=True)
    watcher = _make_watcher([pet])

    watcher.handle_power_event(PBT_APMSUSPEND)
    watcher.handle_power_event(PBT_APMSUSPEND)
    assert pet.hide_calls == 1

    watcher.handle_power_event(PBT_APMRESUMESUSPEND)
    watcher.handle_power_event(PBT_APMRESUMESUSPEND)
    assert pet.show_calls == 1


def test_set_pets_while_suspended_hides_new_visible_pets() -> None:
    pet = FakePet(visible=True)
    watcher = _make_watcher([pet])
    watcher.handle_power_event(PBT_APMSUSPEND)

    new_pet = FakePet(visible=True)
    watcher.set_pets([pet, new_pet])  # type: ignore[arg-type]

    assert new_pet.visible is False
    assert new_pet.hide_calls == 1

    watcher.handle_power_event(PBT_APMRESUMESUSPEND)
    assert pet.visible is True
    assert new_pet.visible is False
