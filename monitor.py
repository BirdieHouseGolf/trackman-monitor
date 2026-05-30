import asyncio
import smtplib
import re
import os
import sys
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

CONTROL_ROOM_URL = (
    "https://portal.trackmangolf.com/facility/"
    "RmFjaWxpdHkKZGYxNjJjZTgzLTE5YmQtNGFlZi05ZWI5LTQ3MTgyODQzOTc2Zg=="
    "/control-room-indoor/overview"
)


async def get_bay_status():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        )
        page = await context.new_page()

        try:
            # ── Step 1: Log in ────────────────────────────────────────────────
            print("Navigating to login page...")
            await page.goto("https://portal.trackmangolf.com/login", wait_until="domcontentloaded", timeout=30_000)
            await page.wait_for_selector('input[placeholder="E-mail or username"]', timeout=30_000)
            await page.screenshot(path="login-page.png", full_page=True)

            await page.fill('input[placeholder="E-mail or username"]', os.environ["TM_EMAIL"])
            await page.fill('input[type="password"]', os.environ["TM_PASSWORD"])
            await page.click('button:has-text("SIGN IN")')
            await page.wait_for_load_state("networkidle", timeout=30_000)
            print(f"Logged in — current URL: {page.url}")

            # ── Step 2: Navigate to control room ─────────────────────────────
            print("Navigating to Control Room...")
            await page.goto(CONTROL_ROOM_URL, wait_until="networkidle", timeout=30_000)

            # Wait for the status badges to appear
            await page.wait_for_selector("text=Offline", timeout=20_000)

            page_content = await page.content()

            # ── Step 3: Parse status counts ──────────────────────────────────
            def extract_count(label):
                pattern = rf'{label}\s*\((\d+)\)'
                match = re.search(pattern, page_content)
                return int(match.group(1)) if match else 0

            available = extract_count("Available")
            occupied  = extract_count("Occupied")
            offline   = extract_count("Offline")
            alerts    = extract_count("Alerts")

            # Also grab bay-level details for the email body
            bay_details = []
            bay_cards = await page.query_selector_all("[class*='bay'], [class*='Bay']")
            # Fallback: just use the summary counts — reliable enough
            print(f"Status → Available: {available}, Occupied: {occupied}, Offline: {offline}, Alerts: {alerts}")

            return {
                "available": available,
                "occupied":  occupied,
                "offline":   offline,
                "alerts":    alerts,
                "url":       page.url,
            }

        except PlaywrightTimeout as e:
            print(f"Timeout error: {e}")
            raise
        finally:
            await browser.close()


def send_alert_email(status: dict):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    subject = f"🚨 Birdie House Alert — {status['offline']} Bay(s) Offline [{now}]"

    body_html = f"""
    <html><body style="font-family: Arial, sans-serif; color: #333;">
      <h2 style="color:#c0392b;">⚠️ Birdie House Bay Alert</h2>
      <p>Detected at: <strong>{now} ET</strong></p>
      <table style="border-collapse:collapse; width:300px;">
        <tr style="background:#f2f2f2;">
          <th style="padding:8px; border:1px solid #ddd; text-align:left;">Status</th>
          <th style="padding:8px; border:1px solid #ddd; text-align:center;">Count</th>
        </tr>
        <tr>
          <td style="padding:8px; border:1px solid #ddd;">🟢 Available</td>
          <td style="padding:8px; border:1px solid #ddd; text-align:center;">{status['available']}</td>
        </tr>
        <tr>
          <td style="padding:8px; border:1px solid #ddd;">🔵 Occupied</td>
          <td style="padding:8px; border:1px solid #ddd; text-align:center;">{status['occupied']}</td>
        </tr>
        <tr style="background:#ffe8e8;">
          <td style="padding:8px; border:1px solid #ddd;"><strong>⚫ Offline</strong></td>
          <td style="padding:8px; border:1px solid #ddd; text-align:center;"><strong>{status['offline']}</strong></td>
        </tr>
        <tr style="background:#fff3cd;">
          <td style="padding:8px; border:1px solid #ddd;">🔴 Alerts</td>
          <td style="padding:8px; border:1px solid #ddd; text-align:center;">{status['alerts']}</td>
        </tr>
      </table>
      <br>
      <a href="{CONTROL_ROOM_URL}" style="
        display:inline-block; padding:10px 20px;
        background:#c0392b; color:white; text-decoration:none;
        border-radius:4px; font-weight:bold;">
        Open Trackman Portal
      </a>
      <br><br>
      <p style="color:#888; font-size:12px;">This alert was sent automatically by the Birdie House monitor.</p>
    </body></html>
    """

    alert_emails = os.environ.get("ALERT_EMAILS", os.environ["GMAIL_USER"])

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = os.environ["GMAIL_USER"]
    msg["To"]      = alert_emails
    msg.attach(MIMEText(body_html, "html"))

    print(f"Sending alert to: {alert_emails}")
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(os.environ["GMAIL_USER"], os.environ["GMAIL_APP_PASSWORD"])
        server.sendmail(os.environ["GMAIL_USER"], alert_emails.split(","), msg.as_string())
    print("Alert email sent ✓")


async def main():
    print(f"=== Trackman Bay Monitor — {datetime.now().isoformat()} ===")

    try:
        status = await get_bay_status()
    except Exception as e:
        print(f"ERROR fetching status: {e}")
        sys.exit(1)

    trigger_alert = status["offline"] > 0 or status["alerts"] > 0

    if trigger_alert:
        print("⚠️  Alert condition detected — sending email...")
        send_alert_email(status)
    else:
        print("✅ All bays healthy — no alert needed.")

    # Exit with code 1 if alert fired (useful for GH Actions logging)
    sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
