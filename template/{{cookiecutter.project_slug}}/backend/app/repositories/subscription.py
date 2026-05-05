{%- if cookiecutter.enable_billing %}
"""Subscription repository."""

{%- if cookiecutter.use_postgresql %}
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models.subscription import Subscription, SubscriptionStatus


async def get_by_org(db: AsyncSession, organization_id: uuid.UUID) -> Subscription | None:
    result = await db.execute(select(Subscription).where(Subscription.organization_id == organization_id))
    return result.scalar_one_or_none()


async def get_by_stripe_id(db: AsyncSession, stripe_subscription_id: str) -> Subscription | None:
    result = await db.execute(
        select(Subscription).where(Subscription.stripe_subscription_id == stripe_subscription_id)
    )
    return result.scalar_one_or_none()


async def get_by_customer_id(db: AsyncSession, stripe_customer_id: str) -> Subscription | None:
    result = await db.execute(
        select(Subscription).where(Subscription.stripe_customer_id == stripe_customer_id)
    )
    return result.scalar_one_or_none()


async def create(db: AsyncSession, **kwargs) -> Subscription:
    sub = Subscription(**kwargs)
    db.add(sub)
    await db.flush()
    await db.refresh(sub)
    return sub


async def update(db: AsyncSession, *, db_sub: Subscription, **kwargs) -> Subscription:
    for k, v in kwargs.items():
        setattr(db_sub, k, v)
    await db.flush()
    await db.refresh(db_sub)
    return db_sub


async def delete(db: AsyncSession, *, db_sub: Subscription) -> None:
    await db.delete(db_sub)
    await db.flush()

{%- elif cookiecutter.use_sqlite %}
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db.models.subscription import Subscription, SubscriptionStatus


def get_by_org(db: Session, organization_id: str) -> Subscription | None:
    return db.execute(select(Subscription).where(Subscription.organization_id == organization_id)).scalar_one_or_none()


def get_by_stripe_id(db: Session, stripe_subscription_id: str) -> Subscription | None:
    return db.execute(
        select(Subscription).where(Subscription.stripe_subscription_id == stripe_subscription_id)
    ).scalar_one_or_none()


def get_by_customer_id(db: Session, stripe_customer_id: str) -> Subscription | None:
    return db.execute(
        select(Subscription).where(Subscription.stripe_customer_id == stripe_customer_id)
    ).scalar_one_or_none()


def create(db: Session, **kwargs) -> Subscription:
    sub = Subscription(**kwargs)
    db.add(sub)
    db.flush()
    db.refresh(sub)
    return sub


def update(db: Session, *, db_sub: Subscription, **kwargs) -> Subscription:
    for k, v in kwargs.items():
        setattr(db_sub, k, v)
    db.flush()
    db.refresh(db_sub)
    return db_sub


def delete(db: Session, *, db_sub: Subscription) -> None:
    db.delete(db_sub)
    db.flush()

{%- elif cookiecutter.use_mongodb %}
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.db.models.subscription import Subscription


async def get_by_org(db: AsyncIOMotorDatabase, organization_id: str) -> Subscription | None:
    return await Subscription.find_one(Subscription.organization_id == organization_id)


async def get_by_stripe_id(db: AsyncIOMotorDatabase, stripe_subscription_id: str) -> Subscription | None:
    return await Subscription.find_one(Subscription.stripe_subscription_id == stripe_subscription_id)


async def get_by_customer_id(db: AsyncIOMotorDatabase, stripe_customer_id: str) -> Subscription | None:
    return await Subscription.find_one(Subscription.stripe_customer_id == stripe_customer_id)


async def create(db: AsyncIOMotorDatabase, **kwargs) -> Subscription:
    sub = Subscription(**kwargs)
    await sub.insert()
    return sub


async def update(db: AsyncIOMotorDatabase, *, db_sub: Subscription, **kwargs) -> Subscription:
    for k, v in kwargs.items():
        setattr(db_sub, k, v)
    await db_sub.save()
    return db_sub

{%- endif %}
{%- else %}
"""Subscription repository — not enabled (enable_billing=false)."""
{%- endif %}
