"""Shared, branded transactional email delivery for Unwind Africa."""

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string


def send_branded_email(
    subject,
    recipients,
    *,
    preheader,
    title,
    paragraphs=(),
    code=None,
    details=(),
    button_label=None,
    button_url=None,
    footer_note=None,
    from_email=None,
    fail_silently=False,
):
    """Send a responsive HTML email with a plain-text fallback."""
    context = {
        "preheader": preheader,
        "title": title,
        "paragraphs": list(paragraphs),
        "code": code,
        "details": list(details),
        "button_label": button_label,
        "button_url": button_url,
        "footer_note": footer_note,
    }
    plain_lines = [title, "", *context["paragraphs"]]
    if code:
        plain_lines.extend(["", f"Your verification code: {code}"])
    if details:
        plain_lines.extend(["", *(f"{label}: {value}" for label, value in details)])
    if button_label and button_url:
        plain_lines.extend(["", f"{button_label}: {button_url}"])
    if footer_note:
        plain_lines.extend(["", footer_note])
    plain_lines.extend(["", "Unwind Africa", "Your time, well spent."])

    message = EmailMultiAlternatives(
        subject=subject,
        body="\n".join(str(line) for line in plain_lines),
        from_email=from_email or settings.DEFAULT_FROM_EMAIL,
        to=list(recipients),
    )
    message.attach_alternative(
        render_to_string("Web/emails/transactional.html", context), "text/html"
    )
    return message.send(fail_silently=fail_silently)
