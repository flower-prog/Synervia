{%- if cookiecutter.enable_billing and cookiecutter.enable_teams %}
"""Billing routes — Plans, Checkout, Portal, Subscription management, Credits."""

from typing import Any

from fastapi import APIRouter, Header, Query, Request, status

from app.api.deps import ActiveOrg, BillingSvc, CurrentUser, DBSession
from app.schemas.billing import (
    CheckoutSessionCreate,
    CheckoutSessionRead,
    PlanList,
    PlanRead,
    PortalSessionRead,
    SubscriptionChangePlan,
    SubscriptionRead,
{%- if cookiecutter.enable_credits_system %}
    CreditBalanceRead,
    CreditTransactionList,
    UsageAggregateRead,
{%- endif %}
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Public — Plans (no auth)
# ---------------------------------------------------------------------------

@router.get("/plans", response_model=PlanList)
{%- if cookiecutter.use_postgresql or cookiecutter.use_mongodb %}
async def list_plans(db: DBSession) -> Any:
    """Return all active plans with their prices. Suitable for the pricing page."""
    import app.repositories.plan as plan_repo
    plans = await plan_repo.list_active_plans(db)
    return PlanList(plans=plans)
{%- else %}
def list_plans(db: DBSession) -> Any:
    import app.repositories.plan as plan_repo
    plans = plan_repo.list_active_plans(db)
    return PlanList(plans=plans)
{%- endif %}


@router.get("/plans/{code}", response_model=PlanRead)
{%- if cookiecutter.use_postgresql or cookiecutter.use_mongodb %}
async def get_plan(code: str, db: DBSession) -> Any:
    """Return a single active plan by code."""
    import app.repositories.plan as plan_repo
    from app.core.exceptions import NotFoundError
    plan = await plan_repo.get_plan_by_code(db, code)
    if not plan:
        raise NotFoundError(message="Plan not found", details={"code": code})
    return plan
{%- else %}
def get_plan(code: str, db: DBSession) -> Any:
    import app.repositories.plan as plan_repo
    from app.core.exceptions import NotFoundError
    plan = plan_repo.get_plan_by_code(db, code)
    if not plan:
        raise NotFoundError(message="Plan not found", details={"code": code})
    return plan
{%- endif %}


# ---------------------------------------------------------------------------
# Checkout & Portal (JWT required)
# ---------------------------------------------------------------------------

@router.post("/checkout", response_model=CheckoutSessionRead, status_code=status.HTTP_201_CREATED)
{%- if cookiecutter.use_postgresql or cookiecutter.use_mongodb %}
async def create_checkout_session(
    data: CheckoutSessionCreate,
    current_user: CurrentUser,
    active_org: ActiveOrg,
    billing_service: BillingSvc,
) -> Any:
    """Create a Stripe Checkout session and return the redirect URL."""
    import app.repositories.organization as org_repo
    org = await org_repo.get_by_id(billing_service.db, active_org.id)
    if org is None:
        from app.core.exceptions import NotFoundError
        raise NotFoundError(message="Organization not found")

    url = await billing_service.create_checkout_session(
        org,
        user=current_user,
        seats=data.seats,
        price_id=str(data.price_id),
        success_url=data.success_url,
        cancel_url=data.cancel_url,
    )
    return CheckoutSessionRead(url=url)
{%- else %}
def create_checkout_session(
    data: CheckoutSessionCreate,
    current_user: CurrentUser,
    active_org: ActiveOrg,
    billing_service: BillingSvc,
) -> Any:
    import app.repositories.organization as org_repo
    org = org_repo.get_by_id(billing_service.db, str(active_org.id))
    if org is None:
        from app.core.exceptions import NotFoundError
        raise NotFoundError(message="Organization not found")

    url = billing_service.create_checkout_session(
        org,
        user=current_user,
        seats=data.seats,
        price_id=str(data.price_id),
        success_url=data.success_url,
        cancel_url=data.cancel_url,
    )
    return CheckoutSessionRead(url=url)
{%- endif %}


@router.post("/portal", response_model=PortalSessionRead)
{%- if cookiecutter.use_postgresql or cookiecutter.use_mongodb %}
async def create_portal_session(
    current_user: CurrentUser,
    active_org: ActiveOrg,
    billing_service: BillingSvc,
) -> Any:
    """Open the Stripe Customer Portal for managing the active org's subscription."""
    import app.repositories.organization as org_repo
    org = await org_repo.get_by_id(billing_service.db, active_org.id)
    if org is None:
        from app.core.exceptions import NotFoundError
        raise NotFoundError(message="Organization not found")

    url = await billing_service.create_portal_session(org)
    return PortalSessionRead(url=url)
{%- else %}
def create_portal_session(
    current_user: CurrentUser,
    active_org: ActiveOrg,
    billing_service: BillingSvc,
) -> Any:
    import app.repositories.organization as org_repo
    org = org_repo.get_by_id(billing_service.db, str(active_org.id))
    if org is None:
        from app.core.exceptions import NotFoundError
        raise NotFoundError(message="Organization not found")

    url = billing_service.create_portal_session(org)
    return PortalSessionRead(url=url)
{%- endif %}


# ---------------------------------------------------------------------------
# Subscription management
# ---------------------------------------------------------------------------

@router.get("/me/subscription", response_model=SubscriptionRead | None)
{%- if cookiecutter.use_postgresql or cookiecutter.use_mongodb %}
async def get_subscription(
    current_user: CurrentUser,
    active_org: ActiveOrg,
    billing_service: BillingSvc,
) -> Any:
    """Get the active subscription for the current organization."""
    return await billing_service.get_subscription(active_org.id)
{%- else %}
def get_subscription(
    current_user: CurrentUser,
    active_org: ActiveOrg,
    billing_service: BillingSvc,
) -> Any:
    return billing_service.get_subscription(str(active_org.id))
{%- endif %}


@router.patch("/me/subscription", response_model=SubscriptionRead)
{%- if cookiecutter.use_postgresql or cookiecutter.use_mongodb %}
async def change_plan(
    data: SubscriptionChangePlan,
    current_user: CurrentUser,
    active_org: ActiveOrg,
    billing_service: BillingSvc,
) -> Any:
    """Upgrade or downgrade the current organization's subscription plan."""
    return await billing_service.change_plan(active_org.id, data.new_price_id)
{%- else %}
def change_plan(
    data: SubscriptionChangePlan,
    current_user: CurrentUser,
    active_org: ActiveOrg,
    billing_service: BillingSvc,
) -> Any:
    return billing_service.change_plan(str(active_org.id), str(data.new_price_id))
{%- endif %}


@router.delete("/me/subscription", response_model=SubscriptionRead)
{%- if cookiecutter.use_postgresql or cookiecutter.use_mongodb %}
async def cancel_subscription(
    current_user: CurrentUser,
    active_org: ActiveOrg,
    billing_service: BillingSvc,
    at_period_end: bool = Query(True, description="Cancel at period end (recommended)"),
) -> Any:
    """Cancel the active subscription. Defaults to end-of-period cancellation."""
    return await billing_service.cancel_subscription(active_org.id, at_period_end=at_period_end)
{%- else %}
def cancel_subscription(
    current_user: CurrentUser,
    active_org: ActiveOrg,
    billing_service: BillingSvc,
    at_period_end: bool = Query(True),
) -> Any:
    return billing_service.cancel_subscription(str(active_org.id), at_period_end=at_period_end)
{%- endif %}


@router.post("/me/subscription/reactivate", response_model=SubscriptionRead)
{%- if cookiecutter.use_postgresql or cookiecutter.use_mongodb %}
async def reactivate_subscription(
    current_user: CurrentUser,
    active_org: ActiveOrg,
    billing_service: BillingSvc,
) -> Any:
    """Undo a scheduled cancellation if the period hasn't ended yet."""
    return await billing_service.reactivate_subscription(active_org.id)
{%- else %}
def reactivate_subscription(
    current_user: CurrentUser,
    active_org: ActiveOrg,
    billing_service: BillingSvc,
) -> Any:
    return billing_service.cancel_subscription(str(active_org.id))  # no-op for SQLite dev
{%- endif %}


# ---------------------------------------------------------------------------
# Credits
# ---------------------------------------------------------------------------

{%- if cookiecutter.enable_credits_system %}

@router.get("/me/credits", response_model=CreditBalanceRead)
{%- if cookiecutter.use_postgresql or cookiecutter.use_mongodb %}
async def get_credits_balance(
    current_user: CurrentUser,
    active_org: ActiveOrg,
    db: DBSession,
) -> Any:
    """Return current credits balance for the active organization."""
    from app.billing.credit_service import CreditService
    from app.core.config import settings
    svc = CreditService(db)
    balance = await svc.get_balance(active_org.id)
    return CreditBalanceRead(balance=balance, low_threshold=settings.CREDITS_LOW_THRESHOLD)
{%- else %}
def get_credits_balance(
    current_user: CurrentUser,
    active_org: ActiveOrg,
    db: DBSession,
) -> Any:
    from app.billing.credit_service import CreditService
    from app.core.config import settings
    svc = CreditService(db)
    balance = svc.get_balance(str(active_org.id))
    return CreditBalanceRead(balance=balance, low_threshold=settings.CREDITS_LOW_THRESHOLD)
{%- endif %}


@router.get("/me/credits/transactions", response_model=CreditTransactionList)
{%- if cookiecutter.use_postgresql or cookiecutter.use_mongodb %}
async def list_credit_transactions(
    current_user: CurrentUser,
    active_org: ActiveOrg,
    db: DBSession,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> Any:
    from app.billing.credit_service import CreditService
    svc = CreditService(db)
    items, total = await svc.get_history(active_org.id, skip=skip, limit=limit)
    return CreditTransactionList(items=items, total=total)
{%- else %}
def list_credit_transactions(
    current_user: CurrentUser,
    active_org: ActiveOrg,
    db: DBSession,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> Any:
    from app.billing.credit_service import CreditService
    svc = CreditService(db)
    items, total = svc.get_history(str(active_org.id), skip=skip, limit=limit)
    return CreditTransactionList(items=items, total=total)
{%- endif %}


@router.get("/me/credits/usage", response_model=UsageAggregateRead)
{%- if cookiecutter.use_postgresql or cookiecutter.use_mongodb %}
async def get_usage_aggregate(
    current_user: CurrentUser,
    active_org: ActiveOrg,
    db: DBSession,
) -> Any:
    import app.repositories.usage_event as usage_repo
    return await usage_repo.aggregate_for_org(db, active_org.id)
{%- else %}
def get_usage_aggregate(
    current_user: CurrentUser,
    active_org: ActiveOrg,
    db: DBSession,
) -> Any:
    import app.repositories.usage_event as usage_repo
    return usage_repo.aggregate_for_org(db, str(active_org.id))
{%- endif %}

{%- endif %}


# ---------------------------------------------------------------------------
# Webhook (unauthenticated, Stripe-signature verified)
# ---------------------------------------------------------------------------

@router.post("/webhook", status_code=status.HTTP_200_OK)
{%- if cookiecutter.use_postgresql or cookiecutter.use_mongodb %}
async def stripe_webhook(
    request: Request,
    billing_service: BillingSvc,
    stripe_signature: str = Header(..., alias="stripe-signature"),
) -> Any:
    """Receive and process Stripe webhook events.

    Stripe sends a ``stripe-signature`` header for HMAC payload verification.
    This endpoint is intentionally unauthenticated.
    """
    payload = await request.body()
    await billing_service.handle_webhook_event(payload, stripe_signature)
    return {"received": True}
{%- else %}
def stripe_webhook(
    request: Request,
    billing_service: BillingSvc,
    stripe_signature: str = Header(..., alias="stripe-signature"),
) -> Any:
    import asyncio
    payload = asyncio.get_event_loop().run_until_complete(request.body())
    billing_service.handle_webhook_event(payload, stripe_signature)
    return {"received": True}
{%- endif %}

{%- else %}
"""Billing routes — not configured (enable_billing or enable_teams is false)."""
{%- endif %}
