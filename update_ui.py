"""Qt helpers for background update checks and install prompts."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import QObject, QThread, pyqtSignal

from settings.update import get_skipped_version, set_skipped_version
from update import UpdateCheckResult, UpdateInfo, apply_update_and_restart, check_for_updates_result, is_frozen

if TYPE_CHECKING:
    from tray import SystemTray


class _UpdateCheckWorker(QThread):
    finished_check = pyqtSignal(object)

    def run(self) -> None:
        self.finished_check.emit(check_for_updates_result())


class UpdateController(QObject):
    """Coordinates GitHub release checks and in-app updates from the tray."""

    def __init__(self, tray: SystemTray) -> None:
        super().__init__(tray._tray)
        self._tray = tray
        self._worker: _UpdateCheckWorker | None = None
        self._pending: UpdateInfo | None = None
        self._checking = False

    @property
    def enabled(self) -> bool:
        return is_frozen()

    @property
    def pending_update(self) -> UpdateInfo | None:
        return self._pending

    @property
    def is_checking(self) -> bool:
        return self._checking

    def maybe_check_on_startup(self) -> None:
        if not self.enabled:
            return
        from settings.update import get_update_check_enabled

        if not get_update_check_enabled():
            return
        self.check_for_updates(silent=True)

    def check_for_updates(self, *, silent: bool = False) -> None:
        if not self.enabled or self._checking:
            return
        self._checking = True
        self._tray.refresh_update_menu_state()
        self._worker = _UpdateCheckWorker(self._tray._tray)
        self._worker.finished_check.connect(
            lambda info: self._on_check_finished(info, silent=silent)
        )
        self._worker.finished.connect(self._worker.deleteLater)
        self._worker.start()

    def install_pending_update(self) -> None:
        if self._pending is None:
            return
        self._tray.show_update_message("installing")
        if apply_update_and_restart(self._pending):
            self._tray.quit_for_update()
            return
        self._tray.show_update_message("install_failed")

    def skip_pending_update(self) -> None:
        if self._pending is None:
            return
        set_skipped_version(self._pending.version)
        self._pending = None
        self._tray.refresh_update_menu_state()

    def _on_check_finished(self, info: object, *, silent: bool) -> None:
        self._checking = False
        self._worker = None

        result = info if isinstance(info, UpdateCheckResult) else None
        update = None
        if result is not None and result.status == "update" and result.update is not None:
            skipped = get_skipped_version()
            if skipped != result.update.version:
                update = result.update

        self._pending = update
        self._tray.refresh_update_menu_state()

        if result is None or result.status == "error":
            if not silent:
                self._tray.show_update_message("check_failed")
            return

        if update is None:
            if not silent:
                self._tray.show_update_message("up_to_date")
            return

        self._tray.show_update_message("available", update)
