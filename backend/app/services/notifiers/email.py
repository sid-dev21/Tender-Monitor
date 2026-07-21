"""Email notifier: render the Jinja2 report and send via SMTP (aiosmtplib).

In dev/tests SMTP points at MailHog (localhost:1025, no TLS/auth). For the real
Gmail smoke test, set SMTP_HOST=smtp.gmail.com, SMTP_PORT=587, SMTP_USE_TLS=true,
and an app password (see ai/email roadmap memory).
"""

from __future__ import annotations

from email.message import EmailMessage
from pathlib import Path

import aiosmtplib
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.config import get_settings
from app.core.logging import logger
from app.models.tender import Tender

_TEMPLATE_DIR = Path(__file__).resolve().parents[2] / "templates" / "email"
_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=select_autoescape(["html"]),
)


def _rows(tenders: list[Tender]) -> list[dict[str, str]]:
    rows = []
    for t in tenders:
        rows.append(
            {
                "title": t.title,
                "reference_number": t.reference_number,
                "deadline_str": t.deadline.strftime("%d/%m/%Y") if t.deadline else "-",
                "budget_str": (
                    f"{t.estimated_budget:,.0f} {t.currency}"
                    if t.estimated_budget is not None
                    else "-"
                ),
            }
        )
    return rows


async def send_tender_report(recipients: list[str], tenders: list[Tender]) -> None:
    """Send the HTML+text tender report to up to 5 recipients."""
    if not recipients:
        return
    settings = get_settings()
    context = {"count": len(tenders), "tenders": _rows(tenders)}
    html = _env.get_template("tender_report.html").render(**context)
    text = _env.get_template("tender_report.txt").render(**context)

    message = EmailMessage()
    message["From"] = settings.smtp_from_email
    message["To"] = ", ".join(recipients[:5])  # defensive cap
    message["Subject"] = f"Tender Monitor - {len(tenders)} nouveaux appels d'offres"
    message.set_content(text)
    message.add_alternative(html, subtype="html")

    kwargs: dict = {
        "hostname": settings.smtp_host,
        "port": settings.smtp_port,
        "use_tls": settings.smtp_port == 465,
        "start_tls": settings.smtp_use_tls and settings.smtp_port != 465,
    }
    if settings.smtp_username:
        kwargs["username"] = settings.smtp_username
        kwargs["password"] = settings.smtp_password

    await aiosmtplib.send(message, **kwargs)
    logger.info("Sent tender report to {} recipient(s)", len(recipients))


def _smtp_kwargs() -> dict:
    settings = get_settings()
    kwargs: dict = {
        "hostname": settings.smtp_host,
        "port": settings.smtp_port,
        "use_tls": settings.smtp_port == 465,
        "start_tls": settings.smtp_use_tls and settings.smtp_port != 465,
    }
    if settings.smtp_username:
        kwargs["username"] = settings.smtp_username
        kwargs["password"] = settings.smtp_password
    return kwargs


async def send_password_reset(recipient: str, reset_url: str) -> None:
    """Send a password-reset link. Raises on SMTP failure (caller decides policy)."""
    settings = get_settings()
    text = (
        "Vous avez demandé la réinitialisation de votre mot de passe Tender Monitor.\n\n"
        f"Ouvrez ce lien pour choisir un nouveau mot de passe :\n{reset_url}\n\n"
        f"Ce lien expire dans {settings.reset_token_expire_minutes} minutes. "
        "Si vous n'êtes pas à l'origine de cette demande, ignorez cet email."
    )
    html = (
        '<div style="font-family:system-ui,Arial,sans-serif;color:#1a1a2e">'
        "<h2>Réinitialisation du mot de passe</h2>"
        "<p>Vous avez demandé la réinitialisation de votre mot de passe "
        "Tender Monitor.</p>"
        f'<p><a href="{reset_url}" style="display:inline-block;background:#c9982a;'
        'color:#fff;padding:12px 20px;border-radius:8px;text-decoration:none">'
        "Choisir un nouveau mot de passe</a></p>"
        f"<p style=\"color:#666;font-size:13px\">Ce lien expire dans "
        f"{settings.reset_token_expire_minutes} minutes. Si vous n'êtes pas à "
        "l'origine de cette demande, ignorez cet email.</p></div>"
    )

    message = EmailMessage()
    message["From"] = settings.smtp_from_email
    message["To"] = recipient
    message["Subject"] = "Tender Monitor - Réinitialisation du mot de passe"
    message.set_content(text)
    message.add_alternative(html, subtype="html")

    await aiosmtplib.send(message, **_smtp_kwargs())
    logger.info("Sent password-reset email to {}", recipient)
