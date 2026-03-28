from __future__ import annotations

import os
import ssl
import smtplib
from email.message import EmailMessage
from typing import Iterable


def send_email(subject: str, body: str, to_emails: Iterable[str]) -> None:
    """
    Sends an email using SMTP credentials stored in environment variables.

    Required environment variables:
      STOCKAI_EMAIL_USER   (e.g., youraddress@gmail.com)
      STOCKAI_EMAIL_PASS   (Gmail App Password or SMTP password)
    Optional:
      STOCKAI_SMTP_HOST    (default: smtp.gmail.com)
      STOCKAI_SMTP_PORT    (default: 465)
    """
    user = os.environ.get("STOCKAI_EMAIL_USER")
    password = os.environ.get("STOCKAI_EMAIL_PASS")
    host = os.environ.get("STOCKAI_SMTP_HOST", "smtp.gmail.com")
    port = int(os.environ.get("STOCKAI_SMTP_PORT", "465"))

    if not user or not password:
        raise RuntimeError("Missing STOCKAI_EMAIL_USER or STOCKAI_EMAIL_PASS env vars.")

    msg = EmailMessage()
    msg["From"] = user
    msg["To"] = ", ".join(to_emails)
    msg["Subject"] = subject
    msg.set_content(body)

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(host, port, context=context) as server:
        server.login(user, password)
        server.send_message(msg)
