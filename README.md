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
.venv\Scripts\activate

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
│   └── sprites/     # Optional PNG sprite frames
└── requirements.txt
```

## Sprites (optional)

Place PNG files in `assets/sprites/`. Expected names:

| State   | Files                          |
|---------|--------------------------------|
| Idle    | `idle_1.png`, `idle_2.png`     |
| Walk    | `walk_1.png`, `walk_2.png`     |
| Fall    | `fall_1.png`                   |
| Drag    | `drag_1.png`                   |

If files are missing, the app draws a colored vector fallback (circle with eyes) so it runs without assets.

## Controls

- **Left-click + drag** — pick up the pet (DRAGGED state)
- **Release on floor** — return to IDLE
- **Release in mid-air** — FALLING until the bottom of the available screen area

## Behavior

- **IDLE** — stands still; may switch to WALKING after a random delay
- **WALKING** — moves horizontally; flips direction or returns to IDLE at screen edges
- **FALLING** — gravity until the floor (`QScreen.availableGeometry()` respects taskbar/dock)
- **DRAGGED** — user-controlled; normal animation pauses while held
