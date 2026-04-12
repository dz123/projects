# personal_coach — Project Notes

## Overview
AI-powered running coach and health analytics system. Syncs Garmin fitness data and uses Google Gemini AI to provide personalized coaching via a multi-agent LangGraph system.

Cloned from: https://github.com/zhnzhang61/PersonalCoach.git

## Setup
- Python 3.12+, uses `uv` package manager
- Requires a `.env` file with `GEMINI_KEY=...`
- Requires Garmin authentication (see README.md for Service Ticket login flow)

## Running
```bash
# Streamlit dashboard
uv run python dashboard.py

# FastAPI server
uv run uvicorn api_server:app --reload

# Sync Garmin data
uv run python garmin_sync.py

# First-time / re-login
uv run python garmin_ticket_login.py --open-browser --compat
```

## Key Files
| File | Purpose |
|------|---------|
| `agentic_coach.py` | LangGraph multi-agent system (coach + doctor nodes) |
| `data_processor.py` | Data pipeline, 3-tier AI memory, health ledger |
| `garmin_sync.py` | Garmin Connect API sync (introspects API dynamically) |
| `garmin_ticket_login.py` | Service Ticket → OAuth2 exchange (bypasses Cloudflare) |
| `migrate.py` | Migrate existing pirate-garmin token to Garth format |
| `dashboard.py` | Streamlit web UI (~800 lines) |
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
  blocks/                  # Training block definitions
  derived/                 # daily_health_metrics.csv
  memory/                  # AI semantic + episodic memory
  chat_memory.db           # SQLite conversation checkpoint
```
`data/` is gitignored — never commit it.

## Notes
- Documentation was originally in Chinese; translated to English in this copy
- License: PolyForm Noncommercial 1.0.0 — personal use only
