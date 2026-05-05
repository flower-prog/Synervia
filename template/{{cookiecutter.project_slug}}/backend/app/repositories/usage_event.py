{%- if cookiecutter.enable_billing and cookiecutter.enable_credits_system %}
"""UsageEvent repository."""

{%- if cookiecutter.use_postgresql %}
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.db.models.credit_transaction import UsageEvent


async def create(
    db: AsyncSession,
    *,
    organization_id: uuid.UUID,
    model: str,
    provider: str,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cached_tokens: int = 0,
    credits_charged: int = 0,
    ai_framework: str = "",
    actor_user_id: uuid.UUID | None = None,
    conversation_id: uuid.UUID | None = None,
) -> UsageEvent:
    event = UsageEvent(
        organization_id=organization_id,
        model=model,
        provider=provider,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cached_tokens=cached_tokens,
        credits_charged=credits_charged,
        ai_framework=ai_framework,
        actor_user_id=actor_user_id,
        conversation_id=conversation_id,
    )
    db.add(event)
    await db.flush()
    await db.refresh(event)
    return event


async def list_for_org(
    db: AsyncSession,
    organization_id: uuid.UUID,
    *,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[UsageEvent], int]:
    count_q = select(func.count()).where(UsageEvent.organization_id == organization_id)
    total = (await db.execute(count_q)).scalar_one()
    rows_q = (
        select(UsageEvent)
        .where(UsageEvent.organization_id == organization_id)
        .order_by(UsageEvent.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(rows_q)
    return list(result.scalars().all()), total


async def aggregate_for_org(
    db: AsyncSession,
    organization_id: uuid.UUID,
) -> dict:
    """Return total tokens and credits for dashboard."""
    q = select(
        func.sum(UsageEvent.input_tokens).label("total_input"),
        func.sum(UsageEvent.output_tokens).label("total_output"),
        func.sum(UsageEvent.cached_tokens).label("total_cached"),
        func.sum(UsageEvent.credits_charged).label("total_credits"),
        func.count().label("total_calls"),
    ).where(UsageEvent.organization_id == organization_id)
    row = (await db.execute(q)).one()
    return {
        "total_input_tokens": row.total_input or 0,
        "total_output_tokens": row.total_output or 0,
        "total_cached_tokens": row.total_cached or 0,
        "total_credits_charged": row.total_credits or 0,
        "total_calls": row.total_calls or 0,
    }

{%- elif cookiecutter.use_sqlite %}
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from app.db.models.credit_transaction import UsageEvent


def create(
    db: Session,
    *,
    organization_id: str,
    model: str,
    provider: str,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cached_tokens: int = 0,
    credits_charged: int = 0,
    ai_framework: str = "",
    actor_user_id: str | None = None,
    conversation_id: str | None = None,
) -> UsageEvent:
    event = UsageEvent(
        organization_id=organization_id,
        model=model,
        provider=provider,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cached_tokens=cached_tokens,
        credits_charged=credits_charged,
        ai_framework=ai_framework,
        actor_user_id=actor_user_id,
        conversation_id=conversation_id,
    )
    db.add(event)
    db.flush()
    db.refresh(event)
    return event


def list_for_org(
    db: Session,
    organization_id: str,
    *,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[UsageEvent], int]:
    total = db.execute(
        select(func.count()).where(UsageEvent.organization_id == organization_id)
    ).scalar_one()
    rows = list(
        db.execute(
            select(UsageEvent)
            .where(UsageEvent.organization_id == organization_id)
            .order_by(UsageEvent.created_at.desc())
            .offset(skip)
            .limit(limit)
        ).scalars().all()
    )
    return rows, total


def aggregate_for_org(db: Session, organization_id: str) -> dict:
    q = select(
        func.sum(UsageEvent.input_tokens).label("total_input"),
        func.sum(UsageEvent.output_tokens).label("total_output"),
        func.sum(UsageEvent.cached_tokens).label("total_cached"),
        func.sum(UsageEvent.credits_charged).label("total_credits"),
        func.count().label("total_calls"),
    ).where(UsageEvent.organization_id == organization_id)
    row = db.execute(q).one()
    return {
        "total_input_tokens": row.total_input or 0,
        "total_output_tokens": row.total_output or 0,
        "total_cached_tokens": row.total_cached or 0,
        "total_credits_charged": row.total_credits or 0,
        "total_calls": row.total_calls or 0,
    }

{%- elif cookiecutter.use_mongodb %}
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.db.models.credit_transaction import UsageEvent


async def create(
    db: AsyncIOMotorDatabase,
    *,
    organization_id: str,
    model: str,
    provider: str,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cached_tokens: int = 0,
    credits_charged: int = 0,
    ai_framework: str = "",
    actor_user_id: str | None = None,
    conversation_id: str | None = None,
) -> UsageEvent:
    event = UsageEvent(
        organization_id=organization_id,
        model=model,
        provider=provider,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cached_tokens=cached_tokens,
        credits_charged=credits_charged,
        ai_framework=ai_framework,
        actor_user_id=actor_user_id,
        conversation_id=conversation_id,
    )
    await event.insert()
    return event


async def list_for_org(
    db: AsyncIOMotorDatabase,
    organization_id: str,
    *,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[UsageEvent], int]:
    query = UsageEvent.find(UsageEvent.organization_id == organization_id)
    total = await query.count()
    rows = await query.sort("-created_at").skip(skip).limit(limit).to_list()
    return rows, total

{%- endif %}
{%- else %}
"""UsageEvent repository — not enabled."""
{%- endif %}
