# Trackman Bay Monitor — Claude Code Briefing

## What this project does
Automated monitor that checks the Trackman Facility Portal (Birdie House) every 15 minutes via GitHub Actions. Uses Playwright (headless Chrome) to log in, read the Control Room Indoor dashboard, and send an HTML email alert if any bays are Offline or in Alert state.

## Project files
```
trackman-monitor/
├── CLAUDE.md                          ← you are here
├── monitor.py                         ← main script (Playwright + Gmail SMTP)
├── README.md                          ← setup instructions
└── .github/
    └── workflows/
        └── monitor.yml                ← GitHub Actions cron schedule
```

## Current status
- `monitor.py` — written, not yet tested end-to-end
- `monitor.yml` — written, pushed to GitHub repo
- GitHub Secrets — configured by user (see below)
- **Remaining**: test the manual workflow run; debug any login/selector issues

## Target portal
- URL: `https://portal.trackmangolf.com/facility/RmFjaWxpdHkKZGYxNjJjZTgzLTE5YmQtNGFlZi05ZWI5LTQ3MTgyODQzOTc2Zg==/control-room-indoor/overview`
- Requires email + password login at `https://portal.trackmangolf.com/login`
- JS-rendered React app (cannot use simple HTTP requests — must use Playwright)
- Dashboard shows bay status badges: `Available (N)`, `Occupied (N)`, `Offline (N)`, `Alerts (N)`
- Alert condition: `offline > 0` OR `alerts > 0`

## GitHub Secrets (already configured by user)
| Secret | Purpose |
|--------|---------|
| `TM_EMAIL` | Trackman portal login email |
| `TM_PASSWORD` | Trackman portal login password |
| `GMAIL_USER` | Gmail address to send FROM |
| `GMAIL_APP_PASSWORD` | Gmail App Password (16-char token, not real password) |
| `ALERT_EMAILS` | Comma-separated alert recipients |

## monitor.py — how it works
1. Launches headless Chromium via Playwright
2. Navigates to `/login`, fills email + password, clicks submit
3. Waits for `networkidle`, then navigates to the control room URL
4. Waits for `text=Offline` selector to appear (confirms page loaded)
5. Reads full page HTML, uses regex to extract counts from `Offline (N)` / `Alerts (N)` badges
6. If alert condition met → sends HTML email via Gmail SMTP SSL (port 465)
7. Exits 0 always (non-zero would mark GH Action as failed)

## monitor.yml — schedule
- Cron: `*/15 * * * *` (every 15 minutes)
- Also has `workflow_dispatch` for manual test runs
- Runs on `ubuntu-latest`, installs Python 3.11 + Playwright + Chromium

## Known risks / things to debug
- **Login flow**: The portal may have changed its form selectors. If login fails, inspect the actual input field selectors at `/login` and update `page.fill()` calls in `monitor.py`
- **Selector fragility**: The `text=Offline` selector works if the page renders that exact string. If the portal changes wording, update accordingly
- **MFA**: If Trackman ever adds MFA, the current script will break — would need to handle OTP
- **GitHub Actions `.github` folder**: Must be committed with exact path `.github/workflows/monitor.yml` — the leading dot can cause issues when uploading via GitHub UI

## Business context
- Facility: Birdie House Inc., 1010 Belfast Rd, Ottawa
- 8 simulator bays (BH01–BH08) running Trackman iO technology
- 24/7 automated operation — offline bays = lost revenue, no staff on site overnight
- Co-owners: Brendan + Cody Mummery
- Previous IT work: diagnosed/fixed recurring Trackman freeze issues (Marvell AQtion NIC → migrated to Intel I226-V ports)

## Local dev / testing
To run locally (requires secrets as env vars):
```bash
pip install playwright
playwright install chromium
playwright install-deps chromium

export TM_EMAIL="..."
export TM_PASSWORD="..."
export GMAIL_USER="..."
export GMAIL_APP_PASSWORD="..."
export ALERT_EMAILS="..."

python monitor.py
```

## Potential improvements (not yet built)
- Alert cooldown: avoid repeat emails every 15 min for the same ongoing outage (use a state file or GitHub Actions cache)
- Bay-level detail in email: currently shows aggregate counts — could scrape individual bay names/statuses
- Webhook/SMS: add Twilio or a webhook alongside email for faster notification
- Didsbury location: second location at 280 Didsbury Rd West, Kanata opening Nov 2026 — will need its own portal URL when live
