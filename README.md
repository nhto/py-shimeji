# py-shimeji

A lightweight desktop pet (Shimeji-style) built with **Python 3.10+** and **PyQt6**.

The pet lives in a frameless, transparent, always-on-top window. It idles, walks along the screen edge, chases your cursor, falls with gravity when dropped, and can be dragged anywhere with the mouse.

Optional extras:

- **AI chat** with a customizable pet name (default **Bubu**) via [OpenRouter](https://openrouter.ai/)
- **Hong Kong weather** — hourly conditions and warning alerts from the [Hong Kong Observatory](https://www.hko.gov.hk/) open-data API
- **Outlook mail/calendar** notifications on Windows (classic COM or Microsoft Graph)

## Requirements

- Python 3.10 or newer
- PyQt6
- An OpenRouter API key (optional — only needed for chat)
- **Weather alerts (optional):** no API key — uses HKO public data (Hong Kong locations only)
- **Outlook integration (optional, Windows only):** classic Outlook desktop signed in to your account (see [Outlook integration](#outlook-integration))

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

You can add your OpenRouter API key from the tray menu (**Preferences**) or manually:

```bash
cp .env.example .env
```

Edit `.env`:

```env
OPENROUTER_API_KEY=sk-or-v1-...
```

Keys saved from **Preferences** are written to `.env` and take effect immediately — no restart needed.

### Weather alerts (Hong Kong)

py-shimeji can show **hourly weather reports** and **warning / special-tip alerts** from the [Hong Kong Observatory](https://www.hko.gov.hk/) open-data API. No API key is required.

| Feature | Behavior |
|---------|----------|
| **Hourly report** | Once per hour (at `:00`), the chosen pet shows temperature, humidity, and forecast for your location |
| **Warnings & tips** | New or cancelled HKO warnings and special weather tips trigger immediate alerts with a **View on HKO** bubble action that opens the matching Observatory page |
| **Language** | Follows the UI language from **Preferences** (English, Simplified Chinese, or Traditional Chinese) |

Tray → **Weather**:

| Menu item | Description |
|-----------|-------------|
| **HKO weather notifications** | Toggle polling on or off |
| **Weather settings...** | Pick an HKO station (27 Hong Kong locations), warning poll interval (60–3600 s, default 600), which pet shows bubbles, and whether to notify while pets are paused |

When no visible pet can show a bubble (hidden pets, or paused with notifications disabled), alerts fall back to the **system tray balloon** instead.

Weather state (last hourly key, known warnings/tips) is stored in `.app_settings.json` under `weather`. Disable the feature entirely from **Weather settings...** if you do not want network requests to `data.weather.gov.hk`.

### Outlook integration

| Mode | When to use |
|------|-------------|
| **Classic Outlook (COM)** | **Recommended** if your org blocks Graph (most work/school accounts) |
| **Microsoft 365 / New Outlook (Graph)** | Only if you can register an Azure app **and** IT grants consent |

#### No Microsoft Graph access?

Many universities and companies **do not allow** personal/third-party apps to use Graph on work mailboxes. **New Outlook has no other API** — py-shimeji cannot read it without Graph.

**Your workable option: switch to Classic Outlook + COM** (use this if COM connectivity worked during setup):

1. **Turn off New Outlook** — in the New Outlook window, use the toggle at the top-right (*Try new Outlook* → switch off), **or** open **Outlook (classic)** from the Windows Start menu (not the “New” icon).
2. Sign in to your work account in classic Outlook and wait for sync.
3. In py-shimeji: tray → **Outlook** → **Outlook settings...** → **Classic Outlook desktop (COM)** → Save.
4. Tray → **Outlook** → **Connect**.

Verify with:

```powershell
.venv\Scripts\python scripts\test_outlook_com.py
```

You do **not** need `AZURE_CLIENT_ID` for this path.

#### New Outlook / Graph (optional — needs IT)

Only use this if your organization allows it:

1. Register a **public client / native** app in [Azure Portal](https://portal.azure.com/) → Microsoft Entra ID → App registrations.
2. Redirect URI: `http://localhost`
3. API permissions: `User.Read`, `Mail.Read`, `Calendars.Read` (+ **admin consent** for work accounts)
4. Add to `.env`:

```env
AZURE_CLIENT_ID=your-application-client-id
AZURE_TENANT_ID=organizations
```

5. Tray → **Outlook** → settings → **Microsoft 365 / New Outlook (Graph API)** → **Connect** → browser sign-in.

#### Classic Outlook (COM) reference

```powershell
.venv\Scripts\python scripts\test_outlook_com.py
.venv\Scripts\python scripts\demo_outlook_com_client.py
```

**Real-time mail (classic COM only):** when connected via **Classic Outlook desktop (COM)**, new mail can trigger pet bubbles via inbox `OnItemAdd` / `NewMailEx` events. **Mail polling still runs every 45s as a backup** — required when using the New Outlook UI, because COM events often do not fire there even though inbox reads work. If pets are hidden, notifications appear in the **system tray** instead.

#### Classic vs New Outlook toggle

| UI | COM read | COM real-time events | Graph API |
|----|----------|----------------------|-----------|
| **Classic Outlook** (`OUTLOOK.EXE`, toggle off) | Yes | Yes (with polling backup) | Yes (if configured) |
| **New Outlook** (toggle on) | Often yes | Usually no — rely on polling | Yes (if IT allows) |

To switch to classic: open Outlook → top-right **Try new Outlook** toggle → **off**. Or launch **Outlook** from Start (not “New Outlook”). Restart classic Outlook after switching.

List every mailbox in your profile (shared mailboxes, delegated inboxes):

```powershell
.venv\Scripts\python scripts\test_outlook_com.py --stores
```

Enable **Include shared and additional mailboxes** in **Outlook settings...** to poll all of those inboxes (COM only).

#### Notification settings

In tray → **Outlook** → **Outlook settings...**:

| Setting | Description |
|---------|-------------|
| **Notify pet** | Choose which pet shows speech bubbles, or **First visible pet** |
| **Show notifications while pets are paused** | When off, paused pets use the tray balloon instead of bubbles |
| **Include shared and additional mailboxes** | Poll every inbox in the Outlook profile (COM) |

Outlook logging records **sender and subject only** — never full message bodies.

#### Non-Windows

Outlook tray menu items are **hidden on macOS and Linux**. Chat and pets work normally without Outlook.

## Run

```bash
python main.py
```

## Build a standalone app (Windows)

You can package py-shimeji into a folder you can zip and share — no Python install required on the recipient's machine.

### Quick build

**Git Bash / macOS / Linux:**

```bash
./scripts/build.sh
```

**PowerShell:**

```powershell
.\scripts\build.ps1
```

This creates `dist/py-shimeji/` with `py-shimeji.exe` and bundled dependencies. Zip that folder to share.

> In Git Bash, use `./scripts/build.sh` — not `.\scripts\build.ps1` (backslashes are escape characters in bash).

### Manual build

```bash
pip install -r requirements-dev.txt
pyinstaller --noconfirm --clean py-shimeji.spec
```

On Windows, copy the env template next to the executable (the build script does this automatically):

```powershell
Copy-Item -Force .env.example dist\py-shimeji\.env.example
```

### Share the build

1. Run the build (above).
2. Zip the entire `dist\py-shimeji\` folder (~100 MB), or use `.\scripts\build-release.ps1` to create a versioned zip automatically.
3. Recipients unzip anywhere and run `py-shimeji.exe` — no Python install needed.
4. Optional: rename `.env.example` to `.env` and add an OpenRouter key, or set the key from **Preferences** after first launch.

### Releases, auto-update, and installer

**Version** is defined in `version.py`. The tray tooltip shows `py-shimeji v{version}`.

**GitHub Releases** (tag `v*` e.g. `v0.1.0`) are built by [`.github/workflows/release.yml`](.github/workflows/release.yml) and publish:

| Asset | Purpose |
|-------|---------|
| `py-shimeji-{version}.zip` | Portable folder — used by in-app auto-update |
| `py-shimeji-setup-{version}.exe` | Inno Setup installer for `%LocalAppData%\Programs\py-shimeji` |

**In-app updates** (packaged `.exe` only):

- On startup, the app checks [GitHub Releases](https://github.com/nhto/py-shimeji/releases) after a short delay (can be disabled in `.app_settings.json` with `"update_check_enabled": false`).
- Tray → **Check for updates...** — manual check.
- When an update is available: **Install update v…** downloads the portable zip, replaces the app folder (keeping `.env` and JSON settings), and restarts via `py-shimeji-updater.exe`.

**Build a release locally:**

```powershell
.\scripts\build-release.ps1              # zip only
.\scripts\build-release.ps1 -Installer   # zip + Inno Setup installer
.\scripts\build-release.ps1 -Installer -Sign   # also Authenticode-sign exes
```

Signing uses `scripts\sign.ps1` when `WINDOWS_SIGN_CERT_PATH` (PFX) and `WINDOWS_SIGN_CERT_PASSWORD` are set. Signed builds reduce Windows SmartScreen warnings for shared installers.

**CI secrets for signed releases** (optional):

| Secret | Description |
|--------|-------------|
| `WINDOWS_SIGN_CERT_BASE64` | Base64-encoded `.pfx` code-signing certificate |
| `WINDOWS_SIGN_CERT_PASSWORD` | PFX password |

Without these secrets, CI still builds and uploads unsigned artifacts.

### After building

| Item | Location when running the `.exe` |
|------|----------------------------------|
| Default sprites | Bundled inside the app |
| `.env` (API key) | Next to `py-shimeji.exe` (created when you save a key from **Preferences**) |
| `.app_settings.json` | Next to `py-shimeji.exe` |
| `.chat_settings.json` | Next to `py-shimeji.exe` |
| Custom sprite folders | Any path you pick in the tray (unchanged) |

A copy of `.env.example` is placed next to the executable so recipients can configure chat manually if they prefer.

**Note:** Window climbing (walking on title bars) works on Windows only, same as the Python source build. The packaged app is built and tested for Windows.

## Project layout

```
py-shimeji/
├── main.py          # Application entry point
├── config.py        # Backward-compatible re-exports (prefer settings/ and i18n/)
├── settings/
│   ├── paths.py     # Project paths, .env loading
│   ├── core.py      # Gameplay constants and speech-bubble limits
│   ├── persistence.py  # .app_settings.json read/write
│   ├── behavior.py  # Speed, chase, pet count, ambient speech
│   ├── outlook.py   # Outlook integration settings
│   ├── weather.py   # HKO weather notification settings
│   ├── chat.py      # OpenRouter API key, chat model/language, pet name
│   ├── hotkeys.py   # Global hotkey bindings
│   ├── sprites.py   # Sprite pack discovery
│   └── update.py    # Auto-update check preferences
├── i18n/
│   ├── strings.py   # Localized UI label dictionaries
│   └── locale.py    # localized(), language pickers
├── tests/           # pytest unit tests
├── states.py        # PetState enum and FSM
├── pet_window.py    # Window, input, physics, rendering
├── surfaces.py      # Walkable ledges from desktop windows (Windows)
├── display.py       # Monitor / taskbar geometry change handling
├── tray.py          # System tray icon and menu
├── chat_window.py   # Pet chat panel (OpenRouter)
├── chat_context.py  # Live weather/Outlook context for chat prompts
├── speech_bubble.py # On-pet ambient / chat speech bubbles
├── bubble_patterns.py  # Speech-bubble background patterns
├── api_key_dialog.py  # Preferences dialog (OpenRouter + UI language)
├── pet_name_dialog.py  # Pet display name settings
├── behavior_settings_dialog.py  # Speed, chase, pet count, ambient speech
├── dialog_theme.py  # Shared styling for dialogs and chat
├── sprite_picker_dialog.py  # Visual sprite pack picker
├── shimeji_pack.py          # Shimeji actions.xml compatibility layer
├── codex_pet.py             # Codex Pet spritesheet compatibility layer
├── outlook_models.py        # MailItem / CalendarEvent dataclasses
├── outlook_text.py          # Outlook notification text formatting
├── outlook_actions.py       # Outlook tray menu actions
├── outlook_com_client.py    # Classic Outlook COM client (Windows)
├── outlook_com_constants.py # MAPI folder/property constants
├── outlook_graph_auth.py    # MSAL sign-in for Graph API
├── outlook_graph_client.py  # Microsoft Graph mail/calendar client
├── outlook_backend.py       # COM vs Graph backend factory
├── outlook_poll_worker.py   # Background mail/calendar fetch
├── outlook_com_events.py    # Real-time classic Outlook inbox COM events
├── outlook_monitor.py       # Polling, dedup, pet notifications
├── outlook_logging.py       # Safe log formatting (subject/sender only)
├── outlook_status.py        # Tray connection state + unread polling
├── outlook_settings_dialog.py  # Outlook connect status and toggles
├── weather_client.py        # HKO open-data fetch and parsing
├── weather_actions.py       # Open HKO warning pages from bubble actions
├── weather_monitor.py       # Hourly reports and warning alerts
├── weather_poll_worker.py   # Background HKO polling
├── weather_settings_dialog.py  # Weather location and notification toggles
├── weather_text.py          # Weather speech-bubble text formatting
├── py-shimeji.spec  # PyInstaller build spec
├── py-shimeji-updater.spec  # Updater helper for in-app updates
├── version.py       # App version and GitHub repo id
├── update.py        # GitHub Releases check and auto-update
├── update_ui.py     # Tray-integrated update controller
├── updater.py       # Small helper exe that applies updates on disk
├── scripts/
│   ├── build.sh               # One-command build (Git Bash / Unix)
│   ├── build.ps1              # One-command build (PowerShell)
│   ├── build-release.ps1      # Versioned zip + optional installer
│   ├── sign.ps1               # Authenticode signing helper
│   ├── installer.iss          # Inno Setup installer script
│   ├── convert_shimeji_pack.py  # Shimeji actions.xml → py-shimeji PNG converter
│   ├── convert_codex_pet.py     # Codex Pet spritesheet → py-shimeji PNG converter
│   ├── test_outlook_com.py    # Phase 0: Outlook COM feasibility check (Windows)
│   └── demo_outlook_com_client.py  # Phase 1: inbox/calendar COM client demo
├── assets/
│   └── sprites/
│       ├── pet_1/   # PNG set for pet 1
│       └── pet_2/   # PNG set for pet 2
├── requirements.txt
├── requirements-dev.txt  # PyInstaller, pytest, and other dev tools
├── .env.example     # Template for OPENROUTER_API_KEY
└── README.md
```

### Unit tests

```powershell
pip install -r requirements-dev.txt
.venv\Scripts\python -m pytest tests/ -v
```

Coverage includes pet state transitions, hotkey parsing, Outlook mail dedup/snooze, speech-bubble text formatting, and HKO weather parsing/alerts.

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

### Community Shimeji packs (actions.xml)

Many [Shimeji-EE](https://github.com/Gohan/shimeji-ee) sprite packs use `conf/actions.xml` with custom frame names (`shime1.png`, `shime2.png`, …) instead of py-shimeji's `idle_1.png` / `walk_1.png` layout. py-shimeji loads these packs directly — point **Change Pet N sprites...** at the pack folder (the one that contains `conf/actions.xml` and the PNG files).

| py-shimeji state | Mapped from Shimeji actions (first match) |
|------------------|-------------------------------------------|
| Idle             | `Stand`, `Look`, …                        |
| Walk / climb     | `Walk`, `Run`, `Dash`, …                  |
| Sit              | `Sit`, `Sprawl`, `Sleep`, …               |
| Fall             | `Falling`, `GrabWall`, …                  |
| Drag             | `Pinched`, `Resisting`, …                 |

To permanently convert a pack to native PNG names (for sharing or editing), use the **Convert to py-shimeji PNGs…** button in the sprite picker, or run:

```bash
python scripts/convert_shimeji_pack.py "C:\path\to\ShimejiPack"
```

Converted packs are written to `assets/sprites/imported/<pack-name>/` and appear in the sprite picker grid.

### Codex Pet packs (spritesheet)

[Codex Pets](https://codexpet.xyz/spec/) use a `pet.json` manifest plus a single `spritesheet.webp` (or `.png`) atlas — typically 1536×1872 (v1) or 1536×2288 (v2) with an 8-column grid of 192×208 px cells. py-shimeji loads these packs directly — point **Change Pet N sprites...** at the Codex pet folder (the one that contains `pet.json` and the spritesheet), or at `~/.codex/pets/<pet-id>/` on your machine.

| py-shimeji state | Mapped from Codex spritesheet row |
|------------------|-----------------------------------|
| Idle             | Row 0 (`idle`)                    |
| Walk             | Row 1 (`running-right`)           |
| Sit              | Row 6 (`waiting`)                 |
| Fall             | Row 4 (`jumping`)                 |
| Drag             | Row 4 (`jumping`, in-air while held) |

To permanently convert a pack to native PNG names, use the **Convert to py-shimeji PNGs…** button in the sprite picker, or run:

```bash
python scripts/convert_codex_pet.py "C:\Users\you\.codex\pets\codie"
```

## Controls

- **Left-click + drag** — pick up a pet (DRAGGED state); disable **Click-through** in the tray first if it is enabled
- **Double-click** — poke the pet (random phrase, brief sit, or walk-in-place animation)
- **Right-click** — open the tray menu at the pet
- **Release on floor** — return to walking / idle
- **Release in mid-air** — FALLING until the nearest ledge or floor
- **System tray** — show/hide each pet, chat, **Preferences** (API key and UI language), **Change pet name...**, **Pet behavior...**, **Weather** (Hong Kong), **Outlook** (Windows), pause pets (reduce motion), toggle click-through, change sprite folders, check for updates, or quit

### Global hotkeys (Windows)

Shortcuts are shown in the tray menu next to each action. Defaults:

| Action | Default shortcut |
|--------|------------------|
| Show/hide all pets | `Ctrl+Alt+H` |
| Open chat | `Ctrl+Alt+B` |
| Pause pets (reduce motion) | `Ctrl+Alt+P` |
| Click-through | `Ctrl+Alt+C` |

Bindings are stored in `.app_settings.json` under `hotkeys`. Set a binding to an empty string to disable it.

## Pet behavior settings

Open **Pet behavior...** from the system tray to adjust:

- **Movement speed** — walk, climb, and fall speed (50%–200%)
- **Cursor chase chance** — how often idle pets walk toward your mouse
- **Number of pets** — 1–4; extra pets appear immediately without restarting
- **Ambient speech bubbles** — short random phrases while pets wander, plus reactions when they bump or land

Settings are saved to `.app_settings.json` and take effect right away.

## Multiple pets

By default the app spawns **two** desktop pets. You can change the count (1–4) from **Pet behavior...** in the tray. They start at different positions along the taskbar edge, load sprites from `assets/sprites/pet_1/` and `assets/sprites/pet_2/` (and `pet_3` / `pet_4` when added), and use distinct fallback colors when PNGs are missing (pink and teal). Each pet has its own behavior, physics, and drag handling. Pets can bump and nudge each other when walking on the same ledge.

## Behavior

- **IDLE** — stands still; may switch to WALKING after a random delay, start **chasing the cursor**, or SIT after standing idle longer
- **CHASING_CURSOR** — walks along the current ledge toward the mouse; sits underneath when the cursor stays still nearby
- **SIT** — rests in place; returns to IDLE or resumes chasing when the cursor moves away
- **WALKING** — moves horizontally; flips direction or returns to IDLE at screen edges
- **CLIMBING** — climbs window edges (Windows only) to reach title bars and ledges
- **FALLING** — gravity until the nearest ledge or floor (`QScreen.availableGeometry()` respects taskbar/dock)
- **DRAGGED** — user-controlled; normal animation pauses while held

Cursor chase tuning constants live in `settings/core.py` and `settings/behavior.py` and can be adjusted from **Pet behavior...** in the tray.

## Preferences

Open **Preferences** from the system tray to manage:

- **OpenRouter API key** — required for chat; stored in `.env`
- **Reply language** — English, Simplified Chinese (`zh-Hans`), or Traditional Chinese (`zh-Hant`); also drives tray/menu labels and HKO weather text

Changes apply immediately to the tray menu and open chat window.

## Chat

Open **Chat with {name}** from the system tray (or right-click a pet). Your pet replies via OpenRouter with streaming text, optional image upload (supported models only), and persisted model/language preferences in `.chat_settings.json`.

When **HKO weather** or **Outlook** is enabled, each chat request includes a short live context block in the system prompt (current temperature/humidity, active warnings, unread mail count, next meeting) so questions like “What’s the weather?” or “Any mail?” can be answered from that data without you pasting details.

Rename the pet from **Change pet name...** in the tray (default **Bubu**). The new name appears in chat, speech bubbles, and tray notifications.

If no API key is configured:

- The tray shows a short setup notification on startup
- Use **Preferences** in the tray menu to add or clear your key
- The chat window displays offline status and setup instructions
- The message composer stays disabled until a valid key is saved

## Click-through

Enable **Click-through (pass mouse clicks)** from the system tray when you want pets visible but not in the way — mouse clicks pass through to apps below. Turn it off again before dragging a pet.

## Pause pets (reduce motion)

Enable **Pause pets (reduce motion)** from the system tray when you want pets visible but still — useful for meetings, screen sharing, or accessibility. Pets snap to the nearest ledge or floor, stop walking and animating, and stay in a sit pose. The setting is remembered across restarts.

You can still drag pets while paused if click-through is off. Turn pause off to resume normal behavior.

## Privacy and security

py-shimeji runs locally on your machine. Optional features send or store data as described below.

| Data | Stored locally | Sent over the network |
|------|----------------|------------------------|
| OpenRouter API key | Plain text in `.env` next to the executable (or project root in dev) | Sent to [OpenRouter](https://openrouter.ai/) as a Bearer token when you chat |
| Chat messages and images | In memory for the current session only (not persisted to disk) | Sent to OpenRouter when you message your pet |
| Live weather / Outlook chat context | In memory (latest poll snapshots) | Short summary (temp, warnings, unread count, next meeting title/time) included in the chat system prompt when those features are enabled |
| Chat model / language / pet name | `.chat_settings.json` | Not sent except as part of chat API requests |
| HKO weather data | Last hourly key and known warning/tip IDs in `.app_settings.json` | Fetches public JSON from `data.weather.gov.hk` when weather alerts are enabled |
| MSAL sign-in tokens | `graph_token_cache` in `.app_settings.json` (plain text) | Used to call Microsoft Graph when Outlook (Graph mode) is connected |
| Outlook mail notifications | Seen-mail IDs and snooze state in `.app_settings.json` | Mail is read via Outlook COM or Graph on your PC; not uploaded elsewhere |
| On-screen / tray alerts | — | Sender, subject, and up to ~60 characters of body preview shown in speech bubbles or the system tray |

**What is not logged:** Outlook debug logs record sender and subject only — never full message bodies.

**Auto-updates:** Frozen builds may download release zips from [GitHub Releases](https://github.com/nhto/py-shimeji/releases) over HTTPS. User files (`.env`, `.app_settings.json`, `.chat_settings.json`) are preserved during updates.

**Reporting issues:** If you find a security vulnerability, please open a [GitHub issue](https://github.com/nhto/py-shimeji/issues) or contact the maintainer privately rather than posting details publicly.
