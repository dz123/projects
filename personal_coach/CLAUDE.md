# personal_coach — Project Notes

## Overview
AI-powered running coach and health analytics system. Syncs Garmin fitness data and uses Google Gemini AI to provide personalized coaching via a multi-agent LangGraph system.

Cloned from: https://github.com/zhnzhang61/PersonalCoach.git

## Setup
- Python 3.12+, uses `uv` package manager
- Requires a `.env` file with `GEMINI_KEY=...`
- Requires Garmin authentication (see README.md for Service Ticket login flow)
- `openpyxl` is installed as an extra dependency (used for importing training plans from Excel)

## Running
```bash
# Streamlit dashboard
uv run python dashboard.py

# FastAPI server
uv run uvicorn api_server:app --reload

# Sync Garmin data
uv run python garmin_sync.py

# First-time / re-login (interactive terminal required)
uv run python garmin_ticket_login.py --open-browser --compat
```

The dashboard is accessible on the local network at the IP shown in the terminal output (port 8501).
To open the firewall on Windows: `netsh advfirewall firewall add rule name="Streamlit" dir=in action=allow protocol=TCP localport=8501`

## Key Files
| File | Purpose |
|------|---------|
| `agentic_coach.py` | LangGraph multi-agent system (coach + doctor nodes) |
| `data_processor.py` | Data pipeline, 3-tier AI memory, health ledger |
| `garmin_sync.py` | Garmin Connect API sync (introspects API dynamically) |
| `garmin_ticket_login.py` | Service Ticket → OAuth2 exchange (bypasses Cloudflare) |
| `migrate.py` | Migrate existing pirate-garmin token to Garth format |
| `dashboard.py` | Streamlit web UI — month-based calendar training view |
| `api_server.py` | FastAPI REST API |
| `ai_analyst.py` | Standalone HR zone calibration via Gemini |

## Architecture

### Multi-Agent System (agentic_coach.py)
- **Coach node**: handles running/training questions
- **Doctor node**: handles health/recovery/HRV/sleep questions
- **Router**: uses Gemini at temperature=0 to decide which agent handles each message
- Conversation persisted to SQLite via `langgraph-checkpoint-sqlite`

### 3-Tier AI Memory (data_processor.py)
1. **Semantic** (`data/memory/user_profile.json`): permanent user profile (age, max HR, injuries, preferences)
2. **Episodic** (`data/memory/episodic_logs.json`): AI-generated summaries of past workouts for RAG
3. **Working**: assembled on-demand from health ledger + workout metadata for each analysis

### Garmin Auth (garmin_ticket_login.py)
Garmin's Cloudflare protection blocks automated login. Workaround:
1. User logs in manually via browser → copies Service Ticket (`ST-...-sso`) from redirect URL
2. Script exchanges ST → pirate-garmin native OAuth2 session → Garth oauth2_token.json

**Important**: `garmin_sync.py` detects non-interactive stdin (e.g. when called from Streamlit) and exits with `[AUTH_REQUIRED]` instead of hanging on `input()`. The dashboard surfaces a Re-authorize section in the sidebar in this case.

## Dashboard UI (dashboard.py)

### Training Tab — Month Calendar View
- **Month selector**: April 2026 – November 2026 (NYC Marathon training block)
- **Grid**: rows = calendar weeks (Mon–Sun), 8 columns — 7 days + a **Week Total** column
- Days outside the current month are greyed out
- **Each day cell** has two sections:
  - **Top (Plan)**: planned workout text, editable via ✏️ popover (saved to `data/blocks/daily_plans.json`)
  - **Bottom (Actual)**: Garmin activity summary (name, distance, pace, avg HR)
- **▼ Details** on a day cell opens a detail panel below the grid (lap editor, telemetry charts, AI analysis, follow-up chat)
- **▼ Details** on the Week Total column opens a **weekly overlay panel** showing HR, Pace, and Elevation charts with all runs from that week overlaid as separate colored lines
- Opening one detail panel closes the other

### Telemetry Charts
- HR, Pace, Elevation tabs — expanded by default
- Elevation tab shows "n/a" message for treadmill/no-GPS activities (`directElevation` not present in those Garmin telemetry files)

### Training Plan Import
The training plan for **Yuxi Wu — 2026 NYC Marathon** was imported from:
`C:\Users\danie\Downloads\Yuxi _ Marathon Training Plan.xlsx`, sheet `Yuxi- 2026 NYC Marathon Trainin`

Structure: rows alternate between a date-header row (cols 7–13 = Mon–Sun dates) and a plan row (cols 7–13 = workout text). Run `import_plan.py` or re-run the inline script in the conversation to re-import. Plans are stored in `data/blocks/daily_plans.json` — user edits via the UI take precedence over the Excel baseline on re-import.

Race date: **2026-11-01** (NYC Marathon). Goal: 3:35:00.

### Sidebar
- **Data Management**: Download Garmin Data, Update Health Ledger
- **Re-authorize Garmin**: SSO link + ticket paste field + Authorize button (use this instead of running `garmin_ticket_login.py` when the token expires while the dashboard is running)
- **AI Telemetry Settings**: downsampling interval slider
- **Auxiliary Log**: log non-Garmin activities (strength, cross-training, etc.)

## Data Directory (`data/`)
```
data/
  get_activities/          # Activity summaries from Garmin
  get_activity_splits/     # Lap-by-lap data
  get_activity_details/    # Telemetry (HR, pace, cadence per second)
  get_activity_hr_in_timezones/
  get_sleep_data/
  get_rhr_day/
  get_hrv_data/
  get_stress_data/
  manual_inputs/           # User-labeled lap categories, run notes, chat history
  blocks/
    training_blocks.json   # Block definitions (start/end date, event type)
    daily_plans.json        # Per-day planned workouts (keyed by YYYY-MM-DD)
    auxiliary_log.json      # Non-Garmin activity log
  derived/                 # daily_health_metrics.csv
  memory/                  # AI semantic + episodic memory
  chat_memory.db           # SQLite conversation checkpoint
```
`data/` is gitignored — never commit it.

## Notes
- Documentation was originally in Chinese; translated to English in this copy
- License: PolyForm Noncommercial 1.0.0 — personal use only
- Streamlit 1.55 removed `use_container_width` on widgets after 2025-12-31 deadline; use `width='stretch'` for charts and omit the parameter for buttons
