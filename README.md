# py-shimeji

A lightweight desktop pet (Shimeji-style) built with **Python 3.10+** and **PyQt6**.

The pet lives in a frameless, transparent, always-on-top window. It idles, walks along the screen edge, chases your cursor, falls with gravity when dropped, and can be dragged anywhere with the mouse. Optional AI chat with **Bubu** is powered by [OpenRouter](https://openrouter.ai/).

## Requirements

- Python 3.10 or newer
- PyQt6
- An OpenRouter API key (optional — only needed for chat)

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

### Chat setup (optional)

You can add your OpenRouter API key from the tray menu (**OpenRouter API key...**) or manually:

```bash
cp .env.example .env
```

Edit `.env`:

```env
OPENROUTER_API_KEY=sk-or-v1-...
```

Keys saved from the tray menu are written to `.env` and take effect immediately — no restart needed.

## Run

```bash
python main.py
```

## Project layout

```
py-shimeji/
├── main.py          # Application entry point
├── config.py        # Constants, paths, timing, chat settings
├── states.py        # PetState enum and FSM
├── pet_window.py    # Window, input, physics, rendering
├── surfaces.py      # Walkable ledges from desktop windows (Windows)
├── display.py       # Monitor / taskbar geometry change handling
├── tray.py          # System tray icon and menu
├── chat_window.py   # Bubu chat panel (OpenRouter)
├── api_key_dialog.py  # OpenRouter API key settings dialog
├── assets/
│   └── sprites/
│       ├── pet_1/   # PNG set for pet 1
│       └── pet_2/   # PNG set for pet 2
├── .env.example     # Template for OPENROUTER_API_KEY
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
│   ├── sit_1.png
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
| Sit     | `sit_1.png` (optional; falls back to idle) |
| Fall    | `fall_1.png`                   |
| Drag    | `drag_1.png`                   |

If files are missing for a pet, that pet stays **hidden on startup** and uses a colored vector fallback only if you show it from the tray.

You can also change a pet's sprites at runtime from the **system tray** menu: **Change Pet N sprites...** opens a folder picker, reloads that pet, and shows it when PNGs are found.

## Controls

- **Left-click + drag** — pick up a pet (DRAGGED state); disable **Click-through** in the tray first if it is enabled
- **Right-click** — open the tray menu at the pet
- **Release on floor** — return to walking / idle
- **Release in mid-air** — FALLING until the nearest ledge or floor
- **System tray** — show/hide each pet, chat with Bubu, manage your OpenRouter API key, toggle click-through, change sprite folders, or quit

## Multiple pets

By default the app spawns **two** desktop pets (`MAX_PETS` in `config.py`). They start at different positions along the taskbar edge, load sprites from `assets/sprites/pet_1/` and `assets/sprites/pet_2/`, and use distinct fallback colors when PNGs are missing (pink and teal). Each pet has its own behavior, physics, and drag handling. Pets can bump and nudge each other when walking on the same ledge.

## Behavior

- **IDLE** — stands still; may switch to WALKING after a random delay, start **chasing the cursor**, or SIT after standing idle longer
- **CHASING_CURSOR** — walks along the current ledge toward the mouse; sits underneath when the cursor stays still nearby
- **SIT** — rests in place; returns to IDLE or resumes chasing when the cursor moves away
- **WALKING** — moves horizontally; flips direction or returns to IDLE at screen edges
- **CLIMBING** — climbs window edges (Windows only) to reach title bars and ledges
- **FALLING** — gravity until the nearest ledge or floor (`QScreen.availableGeometry()` respects taskbar/dock)
- **DRAGGED** — user-controlled; normal animation pauses while held

Cursor chase tuning constants (`CURSOR_CHASE_CHANCE`, `CURSOR_SIT_DISTANCE_PX`, etc.) live in `config.py`.

## Chat with Bubu

Open **Chat with bubu** from the system tray (or right-click a pet). Bubu replies via OpenRouter with streaming text, optional image upload (supported models only), and persisted model/language preferences in `.chat_settings.json`.

If no API key is configured:

- The tray shows a short setup notification on startup
- Use **OpenRouter API key...** in the tray menu to add or clear your key
- The chat window displays offline status and setup instructions
- The message composer stays disabled until a valid key is saved

## Click-through

Enable **Click-through (pass mouse clicks)** from the system tray when you want pets visible but not in the way — mouse clicks pass through to apps below. Turn it off again before dragging a pet.
