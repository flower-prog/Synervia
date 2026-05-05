{%- if cookiecutter.enable_billing %}
"""Handlers for customer.subscription.* webhook events."""

import logging
{%- if cookiecutter.use_postgresql %}
from datetime import UTC, datetime
import stripe
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.subscription import Subscription, SubscriptionStatus
import app.repositories.subscription as sub_repo
import app.repositories.plan as plan_repo
import app.repositories.organization as org_repo

logger = logging.getLogger(__name__)


async def _sync_from_stripe(
    db: AsyncSession, stripe_sub: stripe.Subscription
) -> Subscription:
    price_obj = stripe_sub["items"]["data"][0]["price"]
    price = await plan_repo.get_price_by_stripe_id(db, price_obj["id"])
    org = await org_repo.get_by_stripe_customer(db, stripe_sub.customer)

    if not org:
        logger.error("subscription_org_not_found", customer_id=stripe_sub.customer)
        raise ValueError(f"No org found for customer {stripe_sub.customer}")

    fields = dict(
        stripe_subscription_id=stripe_sub.id,
        stripe_customer_id=stripe_sub.customer,
        stripe_item_id=stripe_sub["items"]["data"][0]["id"],
        price_id=price.id if price else None,
        organization_id=org.id,
        seats_quantity=stripe_sub["items"]["data"][0].get("quantity", 1),
        status=SubscriptionStatus(stripe_sub.status),
        current_period_start=datetime.fromtimestamp(stripe_sub.current_period_start, UTC),
        current_period_end=datetime.fromtimestamp(stripe_sub.current_period_end, UTC),
        cancel_at_period_end=stripe_sub.cancel_at_period_end,
        canceled_at=datetime.fromtimestamp(stripe_sub.canceled_at, UTC) if stripe_sub.canceled_at else None,
        trial_start=datetime.fromtimestamp(stripe_sub.trial_start, UTC) if stripe_sub.trial_start else None,
        trial_end=datetime.fromtimestamp(stripe_sub.trial_end, UTC) if stripe_sub.trial_end else None,
    )

    existing = await sub_repo.get_by_stripe_id(db, stripe_sub.id)
    if existing:
        return await sub_repo.update(db, db_sub=existing, **fields)

    return await sub_repo.create(db, **fields)


async def handle_created(db: AsyncSession, event: stripe.Event) -> None:
    await _sync_from_stripe(db, event.data.object)


async def handle_updated(db: AsyncSession, event: stripe.Event) -> None:
    await _sync_from_stripe(db, event.data.object)


async def handle_deleted(db: AsyncSession, event: stripe.Event) -> None:
    stripe_sub = event.data.object
    sub = await sub_repo.get_by_stripe_id(db, stripe_sub.id)
    if sub:
        sub.status = SubscriptionStatus.CANCELED
        from datetime import datetime
        sub.canceled_at = datetime.fromtimestamp(stripe_sub.canceled_at, UTC) if stripe_sub.canceled_at else datetime.now(UTC)
        await db.flush()
{%- if cookiecutter.enable_email %}
    try:
        customer = stripe.Customer.retrieve(stripe_sub.customer)
        from app.email.service import get_email_service
        from app.core.config import settings
        import datetime as _dt
        period_end = stripe_sub.current_period_end
        access_until = _dt.datetime.fromtimestamp(period_end, _dt.UTC).strftime("%B %d, %Y") if period_end else "end of billing period"
        plan_name = stripe_sub.get("plan", {}).get("nickname", "subscription") if hasattr(stripe_sub, "get") else "subscription"
        email_svc = get_email_service()
        await email_svc.send_subscription_canceled(
            to=customer.email or "",
            name=customer.name or customer.email or "there",
            plan_name=plan_name,
            access_until=access_until,
            resubscribe_url=settings.BILLING_SUCCESS_URL,
        )
    except Exception:
        logger.exception("email_subscription_canceled_failed")
{%- endif %}


async def handle_trial_ending(db: AsyncSession, event: stripe.Event) -> None:
    stripe_sub = event.data.object
    logger.info("subscription_trial_ending", stripe_sub_id=stripe_sub.id)
{%- if cookiecutter.enable_email %}
    try:
        customer = stripe.Customer.retrieve(stripe_sub.customer)
        from app.email.service import get_email_service
        from app.core.config import settings
        import datetime as _dt
        trial_end_ts = stripe_sub.trial_end or 0
        now_ts = _dt.datetime.now(_dt.UTC).timestamp()
        days_left = max(1, int((trial_end_ts - now_ts) / 86400))
        email_svc = get_email_service()
        await email_svc.send_trial_ending(
            to=customer.email or "",
            name=customer.name or customer.email or "there",
            days_left=days_left,
            upgrade_url=settings.BILLING_SUCCESS_URL,
        )
    except Exception:
        logger.exception("email_trial_ending_failed")
{%- endif %}

{%- elif cookiecutter.use_sqlite %}
import stripe
from datetime import UTC, datetime
from sqlalchemy.orm import Session

from app.db.models.subscription import Subscription
import app.repositories.subscription as sub_repo
import app.repositories.plan as plan_repo
import app.repositories.organization as org_repo

logger = logging.getLogger(__name__)


def _sync_from_stripe(db: Session, stripe_sub: stripe.Subscription) -> Subscription:
    price_obj = stripe_sub["items"]["data"][0]["price"]
    price = plan_repo.get_price_by_stripe_id(db, price_obj["id"])
    org = org_repo.get_by_stripe_customer(db, stripe_sub.customer)

    if not org:
        raise ValueError(f"No org found for customer {stripe_sub.customer}")

    fields = dict(
        stripe_subscription_id=stripe_sub.id,
        stripe_customer_id=stripe_sub.customer,
        stripe_item_id=stripe_sub["items"]["data"][0]["id"],
        price_id=str(price.id) if price else None,
        organization_id=str(org.id),
        seats_quantity=stripe_sub["items"]["data"][0].get("quantity", 1),
        status=stripe_sub.status,
        current_period_start=datetime.fromtimestamp(stripe_sub.current_period_start, UTC),
        current_period_end=datetime.fromtimestamp(stripe_sub.current_period_end, UTC),
        cancel_at_period_end=stripe_sub.cancel_at_period_end,
    )

    existing = sub_repo.get_by_stripe_id(db, stripe_sub.id)
    if existing:
        return sub_repo.update(db, db_sub=existing, **fields)
    return sub_repo.create(db, **fields)


def handle_created(db: Session, event: stripe.Event) -> None:
    _sync_from_stripe(db, event.data.object)


def handle_updated(db: Session, event: stripe.Event) -> None:
    _sync_from_stripe(db, event.data.object)


def handle_deleted(db: Session, event: stripe.Event) -> None:
    stripe_sub = event.data.object
    sub = sub_repo.get_by_stripe_id(db, stripe_sub.id)
    if sub:
        sub.status = "canceled"
        db.flush()
{%- if cookiecutter.enable_email %}
    try:
        import asyncio, datetime as _dt
        customer = stripe.Customer.retrieve(stripe_sub.customer)
        from app.email.service import get_email_service
        from app.core.config import settings
        period_end = stripe_sub.current_period_end
        access_until = _dt.datetime.fromtimestamp(period_end, _dt.UTC).strftime("%B %d, %Y") if period_end else "end of billing period"
        email_svc = get_email_service()
        asyncio.get_event_loop().run_until_complete(email_svc.send_subscription_canceled(
            to=customer.email or "",
            name=customer.name or customer.email or "there",
            plan_name="subscription",
            access_until=access_until,
            resubscribe_url=settings.BILLING_SUCCESS_URL,
        ))
    except Exception:
        logger.exception("email_subscription_canceled_failed")
{%- endif %}


def handle_trial_ending(db: Session, event: stripe.Event) -> None:
    stripe_sub = event.data.object
    logger.info("subscription_trial_ending", extra={"stripe_sub_id": stripe_sub.id})
{%- if cookiecutter.enable_email %}
    try:
        import asyncio, datetime as _dt
        customer = stripe.Customer.retrieve(stripe_sub.customer)
        from app.email.service import get_email_service
        from app.core.config import settings
        trial_end_ts = stripe_sub.trial_end or 0
        days_left = max(1, int((trial_end_ts - _dt.datetime.now(_dt.UTC).timestamp()) / 86400))
        email_svc = get_email_service()
        asyncio.get_event_loop().run_until_complete(email_svc.send_trial_ending(
            to=customer.email or "",
            name=customer.name or customer.email or "there",
            days_left=days_left,
            upgrade_url=settings.BILLING_SUCCESS_URL,
        ))
    except Exception:
        logger.exception("email_trial_ending_failed")
{%- endif %}

{%- elif cookiecutter.use_mongodb %}
import stripe
from datetime import UTC, datetime
from motor.motor_asyncio import AsyncIOMotorDatabase

import app.repositories.subscription as sub_repo
import app.repositories.plan as plan_repo
import app.repositories.organization as org_repo
from app.db.models.subscription import Subscription, SubscriptionStatus

logger = logging.getLogger(__name__)


async def _sync_from_stripe(db: AsyncIOMotorDatabase, stripe_sub: stripe.Subscription) -> Subscription:
    price_obj = stripe_sub["items"]["data"][0]["price"]
    price = await plan_repo.get_price_by_stripe_id(db, price_obj["id"])
    org = await org_repo.get_by_stripe_customer(db, stripe_sub.customer)

    if not org:
        raise ValueError(f"No org found for customer {stripe_sub.customer}")

    existing = await sub_repo.get_by_stripe_id(db, stripe_sub.id)
    if existing:
        return await sub_repo.update(
            db,
            db_sub=existing,
            status=SubscriptionStatus(stripe_sub.status),
            cancel_at_period_end=stripe_sub.cancel_at_period_end,
            current_period_start=datetime.fromtimestamp(stripe_sub.current_period_start, UTC),
            current_period_end=datetime.fromtimestamp(stripe_sub.current_period_end, UTC),
        )

    return await sub_repo.create(
        db,
        organization_id=str(org.id),
        stripe_subscription_id=stripe_sub.id,
        stripe_customer_id=stripe_sub.customer,
        stripe_item_id=stripe_sub["items"]["data"][0]["id"],
        price_id=str(price.id) if price else "",
        seats_quantity=stripe_sub["items"]["data"][0].get("quantity", 1),
        status=SubscriptionStatus(stripe_sub.status),
        current_period_start=datetime.fromtimestamp(stripe_sub.current_period_start, UTC),
        current_period_end=datetime.fromtimestamp(stripe_sub.current_period_end, UTC),
        cancel_at_period_end=stripe_sub.cancel_at_period_end,
    )


async def handle_created(db: AsyncIOMotorDatabase, event: stripe.Event) -> None:
    await _sync_from_stripe(db, event.data.object)


async def handle_updated(db: AsyncIOMotorDatabase, event: stripe.Event) -> None:
    await _sync_from_stripe(db, event.data.object)


async def handle_deleted(db: AsyncIOMotorDatabase, event: stripe.Event) -> None:
    stripe_sub = event.data.object
    sub = await sub_repo.get_by_stripe_id(db, stripe_sub.id)
    if sub:
        sub.status = SubscriptionStatus.CANCELED
        await sub.save()
{%- if cookiecutter.enable_email %}
    try:
        customer = stripe.Customer.retrieve(stripe_sub.customer)
        from app.email.service import get_email_service
        from app.core.config import settings
        import datetime as _dt
        period_end = stripe_sub.current_period_end
        access_until = _dt.datetime.fromtimestamp(period_end, _dt.UTC).strftime("%B %d, %Y") if period_end else "end of billing period"
        email_svc = get_email_service()
        await email_svc.send_subscription_canceled(
            to=customer.email or "",
            name=customer.name or customer.email or "there",
            plan_name="subscription",
            access_until=access_until,
            resubscribe_url=settings.BILLING_SUCCESS_URL,
        )
    except Exception:
        logger.exception("email_subscription_canceled_failed")
{%- endif %}


async def handle_trial_ending(db: AsyncIOMotorDatabase, event: stripe.Event) -> None:
    stripe_sub = event.data.object
    logger.info("subscription_trial_ending", extra={"stripe_sub_id": stripe_sub.id})
{%- if cookiecutter.enable_email %}
    try:
        customer = stripe.Customer.retrieve(stripe_sub.customer)
        from app.email.service import get_email_service
        from app.core.config import settings
        import datetime as _dt
        trial_end_ts = stripe_sub.trial_end or 0
        days_left = max(1, int((trial_end_ts - _dt.datetime.now(_dt.UTC).timestamp()) / 86400))
        email_svc = get_email_service()
        await email_svc.send_trial_ending(
            to=customer.email or "",
            name=customer.name or customer.email or "there",
            days_left=days_left,
            upgrade_url=settings.BILLING_SUCCESS_URL,
        )
    except Exception:
        logger.exception("email_trial_ending_failed")
{%- endif %}

{%- endif %}
{%- else %}
"""subscription_events — not enabled (enable_billing=false)."""
{%- endif %}
