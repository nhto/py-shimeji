"""Walkable surfaces derived from on-screen windows (Windows) or screen floor only."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Literal

from PyQt6.QtCore import QRect

from config import MIN_WINDOW_HEIGHT, MIN_WINDOW_WIDTH, PET_HEIGHT, PET_WIDTH, TOP_PERCH_MARGIN_PX

Side = Literal["left", "right"]


@dataclass(frozen=True)
class HorizontalLedge:
    """A horizontal surface the pet can stand on."""

    left: int
    right: int  # right edge of the ledge in screen coordinates
    stand_y: int  # pet widget top-left y when standing here
    ledge_id: str
    pet_width: int = PET_WIDTH
    hwnd: int = 0  # 0 for the screen floor

    def max_pet_x(self) -> int:
        """Rightmost valid pet top-left x on this ledge."""
        return self.right - self.pet_width + 1

    def contains_pet_x(self, pet_x: int) -> bool:
        return self.left <= pet_x <= self.max_pet_x()


@dataclass(frozen=True)
class VerticalLedge:
    """A vertical window edge the pet can climb."""

    edge_x: int
    top: int
    bottom: int
    side: Side
    hwnd: int
    pet_width: int = PET_WIDTH

    def pet_x(self) -> int:
        overlap = 6
        # edge_x is Win32 RECT.right (exclusive) on the right; both sides hug the
        # window edge with a small outward overlap.
        return self.edge_x - self.pet_width + overlap

    def pet_overlaps_height(self, pet_top: int, pet_bottom: int) -> bool:
        margin = 8
        return pet_bottom > self.top + margin and pet_top < self.bottom - margin


class SurfaceTracker:
    """
    Collects horizontal and vertical ledges from visible desktop windows.

    On non-Windows platforms only the screen floor ledge is available.
    """

    def __init__(self) -> None:
        self._horizontal: list[HorizontalLedge] = []
        self._vertical: list[VerticalLedge] = []
        self._pet_width = PET_WIDTH
        self._pet_height = PET_HEIGHT
        self._enabled = sys.platform == "win32"
        if self._enabled:
            self._init_win32()

    def set_pet_dimensions(self, pet_width: int, pet_height: int) -> None:
        """Update the pet footprint used for ledge geometry and collision."""
        self._pet_width = max(1, pet_width)
        self._pet_height = max(1, pet_height)

    def refresh(
        self, play_area: QRect, exclude_hwnds: int | set[int] | None = None
    ) -> None:
        """Rebuild ledge lists for the current play area and window layout."""
        if exclude_hwnds is None:
            exclude_set: set[int] = set()
        elif isinstance(exclude_hwnds, int):
            exclude_set = {exclude_hwnds} if exclude_hwnds else set()
        else:
            exclude_set = exclude_hwnds
        floor = HorizontalLedge(
            left=play_area.left(),
            right=play_area.right(),
            stand_y=play_area.bottom() - self._pet_height + 1,
            ledge_id="screen",
            pet_width=self._pet_width,
        )
        self._horizontal = [floor]
        self._vertical = []

        if not self._enabled:
            return

        for hwnd, rect in self._enumerate_windows(exclude_set):
            width = rect.right - rect.left
            height = rect.bottom - rect.top
            if width < MIN_WINDOW_WIDTH or height < MIN_WINDOW_HEIGHT:
                continue
            if rect.bottom <= play_area.top() or rect.top >= play_area.bottom():
                continue

            # Win32 RECT.right is exclusive; clamp to the play area so pets cannot
            # walk off the visible screen edge on partially off-screen windows.
            ledge_left = max(rect.left, play_area.left())
            ledge_right = min(rect.right - 1, play_area.right())
            if ledge_right - ledge_left < self._pet_width - 1:
                continue

            ledge_top = max(rect.top, play_area.top())
            ledge_bottom = min(rect.bottom, play_area.bottom())
            if ledge_bottom - ledge_top >= MIN_WINDOW_HEIGHT:
                self._vertical.append(
                    VerticalLedge(
                        edge_x=rect.left,
                        top=ledge_top,
                        bottom=ledge_bottom,
                        side="left",
                        hwnd=hwnd,
                        pet_width=self._pet_width,
                    )
                )
                self._vertical.append(
                    VerticalLedge(
                        edge_x=rect.right,
                        top=ledge_top,
                        bottom=ledge_bottom,
                        side="right",
                        hwnd=hwnd,
                        pet_width=self._pet_width,
                    )
                )

            # Skip title bars that would clamp to the screen top; they create
            # bogus perches (e.g. maximized windows) where the pet gets stuck.
            min_window_top = play_area.top() + self._pet_height - 1
            if rect.top < min_window_top:
                continue

            stand_y = rect.top - self._pet_height + 1
            if stand_y < play_area.top() + TOP_PERCH_MARGIN_PX:
                continue

            self._horizontal.append(
                HorizontalLedge(
                    left=ledge_left,
                    right=ledge_right,
                    stand_y=stand_y,
                    ledge_id=f"hwnd:{hwnd}",
                    pet_width=self._pet_width,
                    hwnd=hwnd,
                )
            )

    def horizontal_ledges(self) -> list[HorizontalLedge]:
        return self._horizontal

    def vertical_ledges(self) -> list[VerticalLedge]:
        return self._vertical

    def floor_ledge(self, play_area: QRect) -> HorizontalLedge:
        return HorizontalLedge(
            left=play_area.left(),
            right=play_area.right(),
            stand_y=play_area.bottom() - self._pet_height + 1,
            ledge_id="screen",
            pet_width=self._pet_width,
        )

    def find_ledge_at(self, pet_x: int, pet_y: int) -> HorizontalLedge | None:
        """Return the highest ledge supporting the pet at the given position."""
        feet_y = pet_y + self._pet_height - 1
        best: HorizontalLedge | None = None
        for ledge in self._horizontal:
            if not ledge.contains_pet_x(pet_x):
                continue
            surface_feet = ledge.stand_y + self._pet_height - 1
            if abs(feet_y - surface_feet) <= 4:
                if best is None or ledge.stand_y < best.stand_y:
                    best = ledge
        return best

    def find_landing_ledge(
        self,
        pet_x: int,
        pet_y: int,
        next_feet_y: int,
        exclude_ledge_id: str | None = None,
    ) -> HorizontalLedge | None:
        """Pick the topmost ledge the pet would land on while falling."""
        current_feet = pet_y + self._pet_height - 1
        best: HorizontalLedge | None = None
        for ledge in self._horizontal:
            if exclude_ledge_id is not None and ledge.ledge_id == exclude_ledge_id:
                continue
            if not ledge.contains_pet_x(pet_x):
                continue
            surface_feet = ledge.stand_y + self._pet_height - 1
            # Require feet to be strictly above the surface so a fall starting on
            # a ledge does not re-land on the same perch on the first tick.
            if current_feet < surface_feet <= next_feet_y:
                if best is None or ledge.stand_y < best.stand_y:
                    best = ledge
        return best

    def climb_candidate(
        self,
        pet_x: int,
        pet_top: int,
        pet_bottom: int,
        direction: int,
        next_x: int,
        standing_on_hwnd: int = 0,
    ) -> VerticalLedge | None:
        """Return a vertical edge the pet should start climbing, if any."""
        tolerance = 4
        candidates: list[VerticalLedge] = []
        for ledge in self._vertical:
            if ledge.hwnd == standing_on_hwnd:
                continue
            if not ledge.pet_overlaps_height(pet_top, pet_bottom):
                continue
            if direction > 0 and ledge.side == "left":
                if next_x + self._pet_width >= ledge.edge_x - tolerance:
                    if pet_x + self._pet_width <= ledge.edge_x + tolerance:
                        candidates.append(ledge)
            elif direction < 0 and ledge.side == "right":
                if next_x <= ledge.edge_x + tolerance:
                    if pet_x >= ledge.edge_x - tolerance:
                        candidates.append(ledge)
        if not candidates:
            return None
        if direction > 0:
            return min(candidates, key=lambda item: item.edge_x)
        return max(candidates, key=lambda item: item.edge_x)

    def vertical_for_window(self, hwnd: int, side: Side) -> VerticalLedge | None:
        for ledge in self._vertical:
            if ledge.hwnd == hwnd and ledge.side == side:
                return ledge
        return None

    # ------------------------------------------------------------------
    # Win32 enumeration
    # ------------------------------------------------------------------

    def _init_win32(self) -> None:
        import ctypes
        from ctypes import wintypes

        self._ctypes = ctypes
        self._user32 = ctypes.windll.user32
        self._wintypes = wintypes

        class RECT(ctypes.Structure):
            _fields_ = [
                ("left", ctypes.c_long),
                ("top", ctypes.c_long),
                ("right", ctypes.c_long),
                ("bottom", ctypes.c_long),
            ]

        self._RECT = RECT
        self._WNDENUMPROC = ctypes.WINFUNCTYPE(
            wintypes.BOOL, wintypes.HWND, wintypes.LPARAM
        )
        # Desktop/shell HWND classes are not real climbable surfaces.
        self._SKIP_WINDOW_CLASSES = frozenset(
            {
                "Progman",
                "WorkerW",
                "Shell_TrayWnd",
                "Shell_SecondaryTrayWnd",
                "DV2ControlHost",
                "Windows.UI.Core.CoreWindow",
            }
        )

    def _enumerate_windows(self, exclude_hwnds: set[int]) -> list[tuple[int, object]]:
        import ctypes

        results: list[tuple[int, object]] = []

        def callback(hwnd: int, _lparam: int) -> bool:
            if hwnd in exclude_hwnds:
                return True
            if not self._user32.IsWindowVisible(hwnd):
                return True
            if self._user32.IsIconic(hwnd):
                return True

            class_name = ctypes.create_unicode_buffer(256)
            if self._user32.GetClassNameW(hwnd, class_name, 256):
                if class_name.value in self._SKIP_WINDOW_CLASSES:
                    return True

            rect = self._RECT()
            if not self._user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                return True

            width = rect.right - rect.left
            height = rect.bottom - rect.top
            if width <= 0 or height <= 0:
                return True

            results.append((int(hwnd), rect))
            return True

        proc = self._WNDENUMPROC(callback)
        self._user32.EnumWindows(proc, 0)
        return results
