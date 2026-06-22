# py-shimeji

A lightweight desktop pet (Shimeji-style) built with **Python 3.10+** and **PyQt6**.

The pet lives in a frameless, transparent, always-on-top window. It idles, walks along the screen edge, falls with gravity when dropped, and can be dragged anywhere with the mouse.

## Requirements

- Python 3.10 or newer
- PyQt6

## Setup

```bash
# Create and activate a virtual environment (recommended)
python -m venv .venv

# Windows
source .venv/Scripts/activate

# macOS / Linux
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Run

```bash
python main.py
```

## Project layout

```
py-shimeji/
├── main.py          # Application entry point
├── config.py        # Constants, paths, timing, colors
├── states.py        # PetState enum and FSM
├── pet_window.py    # Window, input, physics, rendering
├── assets/
│   └── sprites/
│       ├── pet_1/   # PNG set for pet 1
│       └── pet_2/   # PNG set for pet 2
└── requirements.txt
```

## Sprites (optional)

Each pet loads its own PNG set from a separate folder:

```
assets/sprites/
├── pet_1/
│   ├── idle_1.png
│   ├── idle_2.png
│   ├── walk_1.png
│   ├── walk_2.png
│   ├── fall_1.png
│   └── drag_1.png
└── pet_2/
    └── (same filenames)
```

Expected filenames in each folder:

| State   | Files                          |
|---------|--------------------------------|
| Idle    | `idle_1.png`, `idle_2.png`     |
| Walk    | `walk_1.png`, `walk_2.png`     |
| Fall    | `fall_1.png`                   |
| Drag    | `drag_1.png`                   |

If files are missing for a pet, that pet stays **hidden on startup** and uses a colored vector fallback only if you show it from the tray.

You can also change a pet's sprites at runtime from the **system tray** menu: **Change Pet N sprites...** opens a folder picker, reloads that pet, and shows it when PNGs are found.

## Controls

- **Left-click + drag** — pick up a pet (DRAGGED state)
- **Release on floor** — return to IDLE
- **Release in mid-air** — FALLING until the bottom of the available screen area
- **System tray** — show/hide each pet, change sprite folders, or quit the app

## Multiple pets

By default the app spawns **two** desktop pets (`MAX_PETS` in `config.py`). They start at different positions along the taskbar edge, load sprites from `assets/sprites/pet_1/` and `assets/sprites/pet_2/`, and use distinct fallback colors when PNGs are missing (pink and teal). Each pet has its own behavior, physics, and drag handling.

## Behavior

- **IDLE** — stands still; may switch to WALKING after a random delay
- **WALKING** — moves horizontally; flips direction or returns to IDLE at screen edges
- **FALLING** — gravity until the floor (`QScreen.availableGeometry()` respects taskbar/dock)
- **DRAGGED** — user-controlled; normal animation pauses while held
