## Garmin Error 429

Garmin now enforces strict Cloudflare anti-bot protection, which means automated browser login (e.g. Playwright) frequently triggers `HTTP 429 Too Many Requests` and infinite CAPTCHA loops.

This solution works by **manually obtaining a one-time Service Ticket** from the browser, then immediately exchanging it via a project script. The result is a long-lived `OAuth2` credential usable by the standard `garminconnect` (Garth) library.

**Security note**: Never commit Service Tickets, passwords, or tokens to the repository, screenshots, or git history. If you ever hardcoded an `ST-...` value inside `.venv`, delete it or reinstall `pirate-garmin` (see "Restoring pirate_garmin in the virtual environment" below).

---

### Step 1: Manually obtain a one-time Service Ticket

> **Important**: The Service Ticket (`ST-xxxx`) is single-use and expires within roughly 1 minute. You must run the exchange script **immediately** after obtaining it.

1. Open a **new Incognito/Private** browser window.
2. Press `F12` to open Developer Tools and switch to the **Network** tab.
3. **Critical**: Check the **Preserve log** checkbox at the top of the Network panel.
4. Navigate to the following mobile SSO login URL:
   ```text
   https://sso.garmin.com/mobile/sso/en_US/sign-in?clientId=GCM_ANDROID_DARK&service=https://mobile.integration.garmin.com/gcm/android
   ```
5. Enter your credentials and log in (complete any CAPTCHA if prompted).
6. After login the page will redirect and show "This site can't be reached" — **this is expected**.
7. Immediately copy the **full URL** from the browser address bar, or just the Service Ticket after `ticket=`:
   ```text
   ST-xxxxxxx-xxxxxxxxxxxxxx-sso
   ```

---

### Step 2: One-command exchange and Garth setup (recommended)

No need to modify anything inside `.venv`. From the project root, run:

```bash
# Option A: Pass the redirect URL or ST string directly (fastest)
uv run python garmin_ticket_login.py --url "https://...ticket=ST-...."

# or
uv run python garmin_ticket_login.py --ticket "ST-....-sso"

# Option B: Run without arguments, then paste the redirect URL (or just ST-...-sso) when prompted
uv run python garmin_ticket_login.py

# Option C: Auto-open the login page in browser, then paste the address bar URL when prompted
uv run python garmin_ticket_login.py --open-browser
```

The script will:

1. Use `pirate_garmin`'s exchange logic to convert the ST into a long-lived session, saved to `~/.local/share/pirate-garmin/native-oauth2.json` (override with `--app-dir`).
2. Write the DI token into `~/.garth/oauth2_token.json`.

Optional flags:

- `--compat`: Also generate `oauth1_token.json` and `domain_profile.json` placeholder files (see Step 3) for backwards compatibility with older `garminconnect` versions that check for OAuth1.
- `--run-sync`: Automatically run `uv run python garmin_sync.py` after a successful exchange.

Example (exchange + compat stubs + data sync):

```bash
uv run python garmin_ticket_login.py --url "$PASTED_URL" --compat --run-sync
```

---

### Step 3: Migrate an existing `native-oauth2.json` (optional)

If you already generated `~/.local/share/pirate-garmin/native-oauth2.json` through another method, just write it into Garth:

```bash
uv run python migrate.py
```

(`migrate.py` and `garmin_ticket_login.py` share the same migration logic.)

---

### Step 4: OAuth1 check for older `garminconnect` (optional)

If you still get errors about a missing `oauth1_token.json`, use the `--compat` flag above, or manually create placeholder files:

```python
import json
import os

garth_dir = os.path.expanduser("~/.garth")

with open(os.path.join(garth_dir, "oauth1_token.json"), "w") as f:
    json.dump({"oauth_token": "dummy", "oauth_token_secret": "dummy"}, f)

with open(os.path.join(garth_dir, "domain_profile.json"), "w") as f:
    json.dump({}, f)

print("Compatibility stub files created.")
```

---

### Restoring `pirate_garmin` in the virtual environment (if previously modified)

Editing files inside `.venv` is not recommended long-term; upgrades or dependency syncs will overwrite your changes. If you previously hardcoded a ticket in `auth.py`, reinstall the package to restore upstream behavior:

```bash
uv sync --reinstall-package pirate-garmin
```

---

### Legacy flow (not recommended): Patching `pirate-garmin` + `login`

If you still need to manually modify `create_native_session` and run `pirate-garmin login`, refer to historical commits or backups. **The new workflow should always use `garmin_ticket_login.py`** to avoid modifying `site-packages`.

## License & Commercial Use

This project uses a **Dual Licensing** model, balancing open-source sharing with intellectual property protection:

### 1. Personal & Non-Commercial Use

This project is released under the [PolyForm Noncommercial License 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0/).

- **Allowed**: Free use, study, modification, and execution in non-profit environments by individual users.
- **Prohibited**: Using this project's core logic, AI architecture, or API integration in any for-profit product, paid service, internal commercial system, or as part of a commercial application.

### 2. Commercial Licensing

If you wish to integrate this project's code or architecture (e.g. Garmin auth bypass logic, multi-tier AI memory model, LangGraph sports analysis flow) into a commercial product, paid SaaS, or enterprise application, **you must obtain formal written authorization from the author**.

- For commercial use, contact the author: [zhnzhang61@gmail.com](mailto:zhnzhang61@gmail.com)
- Commercial licensing includes more stable technical support and removes the non-commercial restrictions.

---

## Disclaimer

1. **No official affiliation**: This is an independently developed personal research project with no affiliation, sponsorship, or endorsement from **Garmin**.
2. **Use at your own risk**: This project calls non-public Garmin Connect APIs. Users should strictly comply with Garmin's Terms of Service. The author is **not responsible** for account bans, data loss, or any legal disputes resulting from frequent API calls or reverse engineering.
3. **Data security**: This project runs locally and does not upload any private data. Never commit `.env` files or the `data/` directory containing personal accounts, ST tickets, or API keys to any public repository.

---

## Acknowledgements

This project stands on the shoulders of giants. Thanks to the following open-source projects for their support and inspiration:

- [Streamlit](https://github.com/streamlit/streamlit) (Apache 2.0) - Elegant dashboard frontend framework.
- [LangGraph](https://github.com/langchain-ai/langgraph) (MIT) - Multi-agent reasoning and memory for the AI coach.
- [python-garminconnect](https://github.com/cyberjunky/python-garminconnect) (MIT) - Garmin API wrapper.
- [pirate-garmin](https://github.com/petergardfjall/pirate-garmin) - Key reverse-engineering insights for mobile auth flow.
- [Pandas](https://github.com/pandas-dev/pandas) & [Altair](https://github.com/altair-viz/altair) - Data processing and visualization.

*Note: All referenced third-party libraries are owned by their respective authors and governed by their own open-source licenses.*
