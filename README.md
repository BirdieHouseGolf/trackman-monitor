# Birdie House — Trackman Bay Monitor

Checks the Trackman Facility Portal every 15 minutes and sends an email alert if any bays are **Offline** or in **Alert** state.

---

## Setup (one-time, ~10 minutes)

### 1. Create a private GitHub repo

Go to [github.com/new](https://github.com/new) and create a **private** repo called `trackman-monitor`.

Upload both files:
- `monitor.py`
- `.github/workflows/monitor.yml`

Or clone and push:
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/trackman-monitor.git
git push -u origin main
```

---

### 2. Create a Gmail App Password

The monitor sends email through your Gmail account using an **App Password** (not your real password — this is a separate 16-char token).

1. Go to your Google Account → **Security**
2. Enable **2-Step Verification** if not already on
3. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
4. Select **Mail** + **Other (Custom)** → type "Trackman Monitor" → Generate
5. Copy the 16-character password (you'll only see it once)

---

### 3. Add GitHub Secrets

In your GitHub repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

Add these 5 secrets:

| Secret Name         | Value                                         |
|---------------------|-----------------------------------------------|
| `TM_EMAIL`          | Your Trackman portal login email              |
| `TM_PASSWORD`       | Your Trackman portal password                 |
| `GMAIL_USER`        | Gmail address to send FROM (e.g. `info@birdiehousegolf.ca` or a personal Gmail) |
| `GMAIL_APP_PASSWORD`| The 16-char App Password from Step 2          |
| `ALERT_EMAILS`      | Comma-separated alert recipients, e.g. `you@gmail.com,cody@gmail.com` |

> ⚠️ Note: `GMAIL_USER` must be a **Gmail** address (not a custom domain unless it routes through Google Workspace). If `info@birdiehousegolf.ca` is on Google Workspace, it works fine.

---

### 4. Test it manually

Go to your repo → **Actions** tab → **Trackman Bay Monitor** → **Run workflow** → **Run workflow**

You'll see the logs in real time. If a bay is offline, you'll get an email. If all bays are healthy, the run completes with `✅ All bays healthy`.

---

## How it works

```
Every 15 min
    ↓
GitHub Actions spins up Ubuntu VM
    ↓
Playwright launches headless Chrome
    ↓
Logs into portal.trackmangolf.com
    ↓
Navigates to Control Room Indoor
    ↓
Reads "Offline (X)" and "Alerts (X)" badges
    ↓
If X > 0 → sends HTML email alert with bay counts + portal link
If X = 0 → logs "All bays healthy", no email
```

---

## Customization

**Change check frequency** — edit the cron line in `monitor.yml`:
- Every 10 min: `'*/10 * * * *'`
- Every 30 min: `'*/30 * * * *'`
- Only during business hours (8am–midnight ET): `'*/15 12-4 * * *'` *(UTC offset)*

**Add Alerts-only notifications** — the script already alerts on `alerts > 0` in addition to `offline > 0`.

**GitHub Actions free tier** — GitHub gives 2,000 free minutes/month on private repos. Each run takes ~2–3 min. At 15-min intervals that's ~96 runs/day × 3 min = ~288 min/day → well within the free 2,000 min/month limit.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| Login fails | Double-check `TM_EMAIL` / `TM_PASSWORD` secrets; try logging in manually first |
| Email not sending | Verify the App Password is correct; ensure 2FA is enabled on the Gmail account |
| Timeout errors | Trackman portal may be slow — the script has 30s timeouts, should be fine |
| `text=Offline` not found | Portal UI may have changed — open an issue or update the selector in `monitor.py` |
