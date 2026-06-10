"""
Stage 3 — Send Personalised Outreach Emails via Brevo
------------------------------------------------------
INPUT  : list of contact dicts from Stage 2
OUTPUT : sends emails, returns list of send results

Brevo Transactional Email API:
  POST https://api.brevo.com/v3/smtp/email
  Docs: https://developers.brevo.com/reference/sendtransacemail

IMPORTANT: Before this works, you must verify your sending domain
in Brevo dashboard:
  Settings -> Senders & IPs -> Domains -> Add jayantworks.xyz
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

BREVO_API_KEY = os.getenv("BREVO_API_KEY")
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "jayant@jayantworks.xyz")
SENDER_NAME = os.getenv("SENDER_NAME", "Jayant Raj")
BASE_URL = "https://api.brevo.com/v3"


def compose_email(contact: dict) -> tuple[str, str]:
    """
    Compose a personalised subject + HTML body for a contact.

    ── THIS IS YOURS TO CUSTOMISE ──
    The pipeline only fires it; the copy and pitch are entirely yours.
    Edit the subject and body below to match your actual pitch.

    Args:
        contact: dict with keys: name, title, email, company

    Returns:
        (subject, html_body)
    """
    first_name = contact["name"].split()[0] if contact["name"] else "there"
    company = contact["company"].replace(".com", "").replace(".io", "").title()
    title = contact.get("title", "")

    subject = f"Quick question, {first_name}"

    html_body = f"""
    <p>Hi {first_name},</p>

    <p>I came across {company} and was really impressed by what you're building.</p>

    <p>I'm Jayant — a software engineer who specialises in building
    automated outreach and data pipelines. I've been working on tooling
    that helps {title.lower() if title else "leaders"} like yourself
    cut manual prospecting time by 80%.</p>

    <p>Would you be open to a 15-minute call this week to see if there's
    a fit?</p>

    <p>Best,<br>
    {SENDER_NAME}<br>
    <a href="https://jayantworks.xyz">jayantworks.xyz</a></p>
    """

    return subject, html_body


def send_emails(contacts: list[dict]) -> list[dict]:
    """
    Sends a personalised email to each contact via Brevo.

    Args:
        contacts: list of contact dicts from Stage 2

    Returns:
        list of result dicts with email, status, message_id
    """
    print(f"\n[Stage 3] Sending emails to {len(contacts)} contacts...")

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "api-key": BREVO_API_KEY,
    }

    results = []

    for contact in contacts:
        email = contact.get("email")
        name = contact.get("name", "")

        if not email:
            print(f"  x Skipping {name} - no email")
            continue

        subject, html_body = compose_email(contact)

        payload = {
            "sender": {
                "name": SENDER_NAME,
                "email": SENDER_EMAIL,
            },
            "to": [{"email": email, "name": name}],
            "subject": subject,
            "htmlContent": html_body,
        }

        try:
            response = requests.post(
                f"{BASE_URL}/smtp/email",
                headers=headers,
                json=payload,
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            message_id = data.get("messageId", "unknown")

            print(f"  + Sent to {email} (messageId: {message_id})")
            results.append({
                "email": email,
                "name": name,
                "company": contact.get("company"),
                "status": "sent",
                "message_id": message_id,
            })

        except requests.exceptions.HTTPError as e:
            print(f"  x Failed for {email}: {e.response.status_code} - {e.response.text}")
            results.append({
                "email": email,
                "name": name,
                "company": contact.get("company"),
                "status": "failed",
                "error": e.response.text,
            })
        except Exception as e:
            print(f"  x Error for {email}: {e}")
            results.append({
                "email": email,
                "name": name,
                "company": contact.get("company"),
                "status": "error",
                "error": str(e),
            })

    sent = sum(1 for r in results if r["status"] == "sent")
    print(f"[Stage 3] Done - {sent}/{len(results)} emails sent successfully")
    return results


if __name__ == "__main__":
    # Quick test with a dummy contact (won't actually send without domain verified)
    test_contacts = [
        {
            "name": "Test User",
            "title": "CEO",
            "email": "test@example.com",
            "company": "example.com",
        }
    ]
    send_emails(test_contacts)
