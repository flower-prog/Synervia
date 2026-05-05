{%- if cookiecutter.enable_newsletter_signup %}
"""Newsletter signup endpoint."""

import logging
from typing import Any

from fastapi import APIRouter, status
from pydantic import BaseModel, EmailStr

logger = logging.getLogger(__name__)

router = APIRouter()


class NewsletterSignupIn(BaseModel):
    email: EmailStr
    name: str | None = None


@router.post("/newsletter/signup", status_code=status.HTTP_201_CREATED)
async def newsletter_signup(body: NewsletterSignupIn) -> Any:
    """Subscribe an email to the newsletter."""
    logger.info("newsletter_signup", extra={"email": body.email})
{%- if cookiecutter.enable_email %}
    try:
        from app.email.service import get_email_service, EmailKey
        email_svc = get_email_service()
        await email_svc.send(
            key=EmailKey.NEWSLETTER_WELCOME,
            to=body.email,
            context={"app_name": "{{ cookiecutter.project_name }}"},
        )
    except Exception:
        logger.exception("newsletter_welcome_email_failed")
{%- endif %}
    return {"message": "Subscribed successfully", "email": body.email}

{%- else %}
"""Marketing routes — not enabled."""
{%- endif %}
