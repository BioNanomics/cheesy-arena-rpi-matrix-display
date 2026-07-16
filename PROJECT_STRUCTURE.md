# Project Structure

This document walks through every file and directory in the repo, what it does, and why it matters to the project. It's a companion to `README.md` (usage/config) and `IMPLEMENTATION_PLAN.md` (the build plan).

**A note on `plan.md`:** several files in this repo (`IMPLEMENTATION_PLAN.md`, `README.md`, code comments) reference `plan.md` as "the full target system spec" — but `plan.md` itself is not present in this repository. It appears to have existed only outside version control (e.g. pasted into a chat/planning session) and was never committed. `IMPLEMENTATION_PLAN.md` is the closest thing to an authoritative spec actually in the repo, and is treated as such below.

## What this project is

A Raspberry Pi + Adafruit RGB Matrix HAT drives a 64x32 LED panel that mirrors live match data from [Cheesy Arena](https://github.com/Team254/cheesy-arena)'s FMS (Field Management System): team number, driver-station connection status, and full-screen E-Stop/Bypass overrides. It's built in two parts:

- **Part A — Hardware bring-up**: a standalone smoke test proving the Pi → HAT → panel chain works, with no dependency on Cheesy Arena or websockets at all.
- **Part B — FMS-driven display**: the full pipeline that connects to Cheesy Arena over a websocket and renders live station state to the panel.

Part B is deliberately layered so the parsing/state/rendering logic is fully testable on a dev machine with no hardware attached — only one module (`sinks.py`'s `MatrixSink`) ever imports the hardware library, and it does so lazily.

---

## Core pipeline

Data flows: `fms_client.py` (websocket → parsed snapshot) → `state.py` (snapshot → display mode, dedupe) → `renderer.py` (mode → PIL image) → `sinks.py` (image → PNG file or physical panel). `main.py` wires all four together; `config.py` supplies their settings.

### `fms_client.py`
Owns the websocket connection to Cheesy Arena: builds the connection URL, runs a reconnect loop (`run_forever`) that automatically re-establishes the handshake if the FMS drops or reboots, and parses raw `arenaStatus` JSON messages into a `StationSnapshot` (`parse_station_snapshot`). Significant because it's where the original prototype's key bug got fixed: it reads the connection field as `station_data.get("DsConn")`, correcting the old code's `"sConn"` typo. `handle_message` also wraps parsing/dispatch in a try/except so one malformed message or a downstream rendering error can't kill the whole websocket connection.

### `state.py`
Defines the data model and the priority logic for what the panel should show. `StationSnapshot` is the parsed-out shape of one alliance station's status; `DisplayMode` is the enum of screens (`ESTOP`, `BYPASS`, `NORMAL`, `IDLE`); `compute_mode()` encodes the priority hierarchy EStop > Bypass > Team Assigned > Idle. `StateTracker.should_redraw()` remembers the last-drawn state so the renderer/sink are only invoked when something actually changed, generalizing the original prototype's ad hoc `previous_state` string comparison.

### `renderer.py`
Turns a `(DisplayMode, StationSnapshot)` pair into a 64x32 `PIL.Image` — one function per mode (`render_estop`, `render_bypass`, `render_normal`, `render_idle`), dispatched by `render()`. `render_normal` splits the panel into a team-number zone and a connection-status-dot zone, and auto-shrinks the team-number font (`_fit_team_font`) so a 5-digit team number doesn't collide with the status dot. `render_idle` composites `assets/refinery_logo.png` if present, falling back to a `"----"` placeholder (marked `# TODO`) since the real logo hasn't been supplied yet. The single most important design constraint here: this module **never imports `rgbmatrix`**, so it stays importable and unit-testable on any machine, Pi or not.

### `sinks.py`
Defines where a rendered frame goes. `CanvasSink` is the abstract base (`show(image)`); `FileSink` writes each frame to a PNG (used for dev/preview, no hardware needed); `MatrixSink` pushes frames to the real panel via the `rgbmatrix` library. `MatrixSink.__init__` imports `rgbmatrix` lazily, inside the constructor — this is the one place in the whole codebase where the hardware dependency is loaded, which is what lets `fms_client`, `state`, `renderer`, and `main.py --sink=file` all run and be tested on a plain dev machine.

### `main.py`
The entry point. Loads config, builds a sink, sets up a `StateTracker`, and calls `fms_client.run_forever()` with a handler that: checks whether the state changed, logs a human-readable status block to the console, and renders + pushes the new frame to the sink. Also prints the same kind of status output the original `fms_ws_test.py` prototype did, so console behavior is preserved even though the internals moved into proper modules.

### `config.py`
Defines the `Config` dataclass and `load_config()`, which reads settings from `CHEESY_*` environment variables (FMS IP, target station, sink type, matrix dimensions/hardware mapping/GPIO tuning) with `argparse` flags (`--fms-ip`, `--station`, `--sink`) as dev-convenience overrides. Env-vars-as-source-of-truth matches how the systemd deployment supplies config (`EnvironmentFile=`) and keeps live-event-specific values (like the FMS IP) out of git.

---

## Hardware bring-up (Part A)

### `hardware_test.py`
A standalone smoke-test script with **zero dependency** on the FMS/websocket code — just `Pillow` and `rgbmatrix`. It draws a green border box with white "HELLO" text and pushes it to the panel. Its purpose is narrow but critical: prove the physical Pi → HAT → panel chain works *before* any of the more complex pipeline code is brought into the loop, so a wiring/driver issue and a software bug never get confused with each other. It also doubles as the first real exercise of the `Image → SetImage` call that `MatrixSink` later reuses.

### `docs/PI_SETUP.md`
The on-site runbook for going from a blank SD card to a working smoke test: flashing Raspberry Pi OS Lite, disabling onboard audio (its PWM conflicts with the GPIO pins the HAT uses for panel timing — skipping this causes flicker), installing build dependencies, building `rpi-rgb-led-matrix` from source (it isn't pip-installable), creating a `--system-site-packages` venv so it can see the system-installed `rgbmatrix` module, running the smoke test with `sudo` (GPIO needs root), and finally installing the systemd service. Also has a troubleshooting section for the most common bring-up failures (nothing lights up, wrong colors, flickering, `ImportError: No module named rgbmatrix`).

---

## Legacy / historical

### `fms_ws_test.py`
The original Phase-1 console prototype: connects to the FMS websocket and prints station status/team info to the terminal whenever it changes. Superseded entirely by `main.py`, but kept in the repo as historical reference. Notably, it still contains the `sConn` typo bug (reads `station_data.get("sConn")` instead of `"DsConn"`) — this was caught when the parsing logic moved into `fms_client.py`, and a regression test (`tests/test_fms_client.py::test_ds_conn_is_parsed_from_the_correct_key`) exists specifically to make sure it can't silently come back.

---

## Tests & dev tooling

### `conftest.py`
A one-line pytest fixture file that inserts the repo root onto `sys.path`, so test modules can do `from state import ...` etc. without the project needing to be installed as a package.

### `tests/test_state.py`
Unit tests for `compute_mode()`'s priority ordering (EStop > Bypass > Normal > Idle) and `StateTracker`'s change-detection behavior.

### `tests/test_fms_client.py`
Unit tests for websocket message parsing, including the `DsConn` regression test, a check that a missing/typo'd station logs a visible warning (rather than failing silently, which was a regression risk during the refactor), a nickname-defaulting regression test, and a test that `handle_message` swallows exceptions raised inside the snapshot callback so a bad render/hardware call can't take down the websocket connection.

### `tests/test_renderer.py`
Unit tests for the rendering pipeline: correct output size per mode, correct background colors for ESTOP/BYPASS, correct status-dot color for connected/disconnected, IDLE mode not crashing when there's no team, custom width/height honoring (a regression test — `WIDTH`/`HEIGHT` used to be hardcoded, decoupled from `config.py`'s configurable matrix dimensions), and the team-number font auto-shrink behavior for wide (5-digit) team numbers.

### `tests/fixtures/arena_status_samples.json`
Five canonical `arenaStatus` JSON payloads — `estop`, `bypass`, `normal_connected`, `normal_disconnected`, `idle` — that both the test suite and `tools/preview.py` use as shared, realistic sample data instead of each writing its own throwaway payloads.

### `tools/preview.py`
Replays every fixture in `arena_status_samples.json` through the real `parse_station_snapshot → compute_mode → render` pipeline and writes one PNG per mode into `out/`. This is the fastest way to visually check what the panel *would* show for each state, entirely off-hardware — no websocket connection or Pi required.

---

## Assets & deployment

### `assets/fonts/Silkscreen-Bold.ttf` (+ `Silkscreen-OFL.txt`)
A bundled pixel font used by `renderer.py` for all on-panel text. Bundled (rather than relying on a system font) because Raspberry Pi OS Lite ships no fonts by default, and bundling guarantees dev-machine renders and Pi renders look identical. `Silkscreen-OFL.txt` is the font's SIL Open Font License text, included for license compliance.

### `assets/refinery_logo.png`
Referenced by `renderer.py`'s `render_idle()` for the IDLE-mode screen, but the file doesn't exist yet — `renderer.py` checks for its presence and falls back to a `"----"` text placeholder until the real logo asset is supplied.

### `systemd/cheesy-display.service`
The systemd unit that runs `main.py` unattended on the Pi: `Restart=always` / `RestartSec=3` for crash recovery, `WantedBy=multi-user.target` for boot-start, and `EnvironmentFile=/etc/cheesy-display/config.env` to inject live-event config. Combined with `fms_client.py`'s own reconnect loop, this is what satisfies the "headless resiliency" goal — the display recovers from process crashes, FMS server restarts, and full Pi reboots without anyone touching it.

### `systemd/config.env.example`
A template env file matching every `CHEESY_*` variable `config.py` reads, meant to be copied to `/etc/cheesy-display/config.env` on the Pi and edited with the real FMS IP/station for a given event. Keeping this as an example file (rather than a real config file) keeps event-specific values out of git.

### `requirements.txt`
The two pip-installable runtime dependencies: `websocket-client` and `Pillow`. Notably does **not** include `rgbmatrix` — that library is built from source on the Pi per `docs/PI_SETUP.md`, not pip-installed, which is also why `sinks.py` imports it lazily instead of at module load time.

---

## Docs

### `README.md`
User-facing overview: features, prerequisites, configuration table, usage examples (preview/dev/hardware), test instructions, and a roadmap/history section.

### `IMPLEMENTATION_PLAN.md`
The build plan for the whole project, split into Part A (hardware bring-up) and Part B (FMS-driven display), including the module structure, the key "renderer never touches hardware" design decision, the state machine, rendering spec per mode, config/deployment approach, and delivery order. In the absence of a committed `plan.md`, this is the most complete record of the project's intended design in the repo.

---

## Generated / config (not part of the pipeline)

- **`out/`** — PNG output from `tools/preview.py`; git-ignored, regenerated on demand, not source.
- **`.gitignore`** — standard ignore rules (e.g. `out/`, Python caches, venvs).
