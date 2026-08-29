from __future__ import annotations

import smtplib
from email.message import EmailMessage
from typing import Any

from .config import Settings


class Mailer:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @staticmethod
    def render(template: str, values: dict[str, str]) -> str:
        rendered = template
        for key, value in values.items():
            rendered = rendered.replace("{{" + key + "}}", value)
        return rendered

    def send(self, message: dict[str, Any], business: dict[str, Any]) -> str:
        review_url = f"{self.settings.public_base_url}/r/{message['token']}"
        values = {
            "name": message["name"],
            "business_name": business["name"],
            "sender_name": business["sender_name"],
            "review_url": review_url,
        }
        subject = self.render(message["subject"], values)
        body = self.render(message["body"], values)
        if self.settings.email_provider == "demo":
            return "demo"

        email = EmailMessage()
        email["Subject"] = subject
        email["From"] = f"{business['sender_name']} <{business['reply_to']}>"
        email["To"] = message["email"]
        email["Reply-To"] = business["reply_to"]
        email.set_content(body)

        with smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port, timeout=20) as smtp:
            if self.settings.smtp_use_tls:
                smtp.starttls()
            if self.settings.smtp_username:
                smtp.login(self.settings.smtp_username, self.settings.smtp_password)
            smtp.send_message(email)
        return "smtp"
