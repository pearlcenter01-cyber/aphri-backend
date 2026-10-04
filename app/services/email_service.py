import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from app.config import settings


class EmailService:

    @staticmethod
    def _send(to: str, subject: str, body: str) -> bool:
        if not settings.SMTP_HOST or not settings.SMTP_USER or not settings.SMTP_PASSWORD:
            print("❌ EmailService: SMTP not configured")
            return False

        msg = MIMEMultipart()
        msg["From"] = settings.SMTP_FROM or settings.SMTP_USER
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        try:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=20) as server:
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.sendmail(msg["From"], [to], msg.as_string())
            print(f"✅ Email sent to {to}: {subject}")
            return True
        except Exception as e:
            print(f"❌ EmailService error: {e}")
            return False

    @staticmethod
    def send_translation_request(
        user_email: str,
        user_name: str,
        partner_name: str,
        session_id: str,
        english_report: dict,
    ) -> bool:
        subject = f"Amharic translation request — {user_email}"
        body = (
            f"New Amharic translation request\n"
            f"================================\n\n"
            f"User email:    {user_email}\n"
            f"User name:     {user_name}\n"
            f"Partner name:  {partner_name}\n"
            f"Session id:    {session_id}\n"
            f"Score:         {english_report.get('score')}\n\n"
            f"--- English report below ---\n\n"
            f"{english_report}\n\n"
            f"--- End of report ---\n"
        )
        return EmailService._send(settings.TRANSLATION_INBOX, subject, body)