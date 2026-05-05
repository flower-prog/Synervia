{%- if cookiecutter.enable_teams and cookiecutter.enable_rag and cookiecutter.use_jwt %}
"""Knowledge Base routes — CRUD + document listing."""

from typing import Any

{%- if cookiecutter.use_postgresql %}
from uuid import UUID
{%- endif %}

from fastapi import APIRouter, Query, status

from app.api.deps import ActiveOrg, CurrentUser, KnowledgeBaseSvc
{%- if cookiecutter.use_postgresql or cookiecutter.use_sqlite %}
from app.api.deps import RAGDocumentSvc
{%- endif %}
from app.schemas.knowledge_base import (
    KnowledgeBaseCreate,
    KnowledgeBaseList,
    KnowledgeBaseRead,
    KnowledgeBaseUpdate,
)
{%- if cookiecutter.use_postgresql or cookiecutter.use_sqlite %}
from app.schemas.rag import RAGTrackedDocumentList
{%- endif %}

router = APIRouter()


{%- if cookiecutter.use_postgresql %}


@router.get("", response_model=KnowledgeBaseList)
async def list_knowledge_bases(
    service: KnowledgeBaseSvc,
    current_user: CurrentUser,
    active_org: ActiveOrg,
) -> Any:
    """List all Knowledge Bases accessible to the current user in this org context."""
    items = await service.list_accessible(
        user_id=current_user.id,
        organization_id=active_org.id,
    )
    return KnowledgeBaseList(items=items, total=len(items))


@router.post("", response_model=KnowledgeBaseRead, status_code=status.HTTP_201_CREATED)
async def create_knowledge_base(
    data: KnowledgeBaseCreate,
    service: KnowledgeBaseSvc,
    current_user: CurrentUser,
    active_org: ActiveOrg,
) -> Any:
    """Create a new Knowledge Base.

    - ``personal`` scope: visible only to you
    - ``org`` scope: visible to all members of the active org (admin/owner only)
    - ``app`` scope: visible to all users (app admin only)
    """
    return await service.create(
        data,
        user_id=current_user.id,
        organization_id=active_org.id,
        is_app_admin=getattr(current_user, "is_app_admin", False),
    )


@router.get("/{kb_id}", response_model=KnowledgeBaseRead)
async def get_knowledge_base(
    kb_id: UUID,
    service: KnowledgeBaseSvc,
    current_user: CurrentUser,
    active_org: ActiveOrg,
) -> Any:
    """Get a Knowledge Base by ID."""
    return await service.get(
        kb_id,
        user_id=current_user.id,
        organization_id=active_org.id,
    )


@router.patch("/{kb_id}", response_model=KnowledgeBaseRead)
async def update_knowledge_base(
    kb_id: UUID,
    data: KnowledgeBaseUpdate,
    service: KnowledgeBaseSvc,
    current_user: CurrentUser,
    active_org: ActiveOrg,
) -> Any:
    """Update name or description of a Knowledge Base."""
    return await service.update(
        kb_id,
        data,
        user_id=current_user.id,
        organization_id=active_org.id,
        is_app_admin=getattr(current_user, "is_app_admin", False),
    )


@router.delete("/{kb_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_knowledge_base(
    kb_id: UUID,
    service: KnowledgeBaseSvc,
    current_user: CurrentUser,
    active_org: ActiveOrg,
) -> None:
    """Delete a Knowledge Base. Default KBs cannot be deleted."""
    await service.delete(
        kb_id,
        user_id=current_user.id,
        organization_id=active_org.id,
        is_app_admin=getattr(current_user, "is_app_admin", False),
    )


@router.get("/{kb_id}/documents", response_model=RAGTrackedDocumentList)
async def list_kb_documents(
    kb_id: UUID,
    service: KnowledgeBaseSvc,
    rag_doc_service: RAGDocumentSvc,
    current_user: CurrentUser,
    active_org: ActiveOrg,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> Any:
    """List documents ingested into a Knowledge Base."""
    await service.get(kb_id, user_id=current_user.id, organization_id=active_org.id)
    return await rag_doc_service.list_for_kb(kb_id=kb_id, skip=skip, limit=limit)


{%- elif cookiecutter.use_sqlite %}


@router.get("", response_model=KnowledgeBaseList)
def list_knowledge_bases(
    service: KnowledgeBaseSvc,
    current_user: CurrentUser,
    active_org: ActiveOrg,
) -> Any:
    """List all Knowledge Bases accessible to the current user in this org context."""
    items = service.list_accessible(
        user_id=str(current_user.id),
        organization_id=str(active_org.id),
    )
    return KnowledgeBaseList(items=items, total=len(items))


@router.post("", response_model=KnowledgeBaseRead, status_code=status.HTTP_201_CREATED)
def create_knowledge_base(
    data: KnowledgeBaseCreate,
    service: KnowledgeBaseSvc,
    current_user: CurrentUser,
    active_org: ActiveOrg,
) -> Any:
    """Create a new Knowledge Base."""
    return service.create(
        data,
        user_id=str(current_user.id),
        organization_id=str(active_org.id),
        is_app_admin=getattr(current_user, "is_app_admin", False),
    )


@router.get("/{kb_id}", response_model=KnowledgeBaseRead)
def get_knowledge_base(
    kb_id: str,
    service: KnowledgeBaseSvc,
    current_user: CurrentUser,
    active_org: ActiveOrg,
) -> Any:
    """Get a Knowledge Base by ID."""
    return service.get(
        kb_id,
        user_id=str(current_user.id),
        organization_id=str(active_org.id),
    )


@router.patch("/{kb_id}", response_model=KnowledgeBaseRead)
def update_knowledge_base(
    kb_id: str,
    data: KnowledgeBaseUpdate,
    service: KnowledgeBaseSvc,
    current_user: CurrentUser,
    active_org: ActiveOrg,
) -> Any:
    """Update name or description of a Knowledge Base."""
    return service.update(
        kb_id,
        data,
        user_id=str(current_user.id),
        organization_id=str(active_org.id),
        is_app_admin=getattr(current_user, "is_app_admin", False),
    )


@router.delete("/{kb_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def delete_knowledge_base(
    kb_id: str,
    service: KnowledgeBaseSvc,
    current_user: CurrentUser,
    active_org: ActiveOrg,
) -> None:
    """Delete a Knowledge Base. Default KBs cannot be deleted."""
    service.delete(
        kb_id,
        user_id=str(current_user.id),
        organization_id=str(active_org.id),
        is_app_admin=getattr(current_user, "is_app_admin", False),
    )


@router.get("/{kb_id}/documents", response_model=RAGTrackedDocumentList)
def list_kb_documents(
    kb_id: str,
    service: KnowledgeBaseSvc,
    rag_doc_service: RAGDocumentSvc,
    current_user: CurrentUser,
    active_org: ActiveOrg,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> Any:
    """List documents ingested into a Knowledge Base."""
    service.get(kb_id, user_id=str(current_user.id), organization_id=str(active_org.id))
    return rag_doc_service.list_for_kb(kb_id=kb_id, skip=skip, limit=limit)


{%- elif cookiecutter.use_mongodb %}


@router.get("", response_model=KnowledgeBaseList)
async def list_knowledge_bases(
    service: KnowledgeBaseSvc,
    current_user: CurrentUser,
    active_org: ActiveOrg,
) -> Any:
    """List all Knowledge Bases accessible to the current user in this org context."""
    items = await service.list_accessible(
        user_id=str(current_user.id),
        organization_id=str(active_org.id),
    )
    return KnowledgeBaseList(items=items, total=len(items))


@router.post("", response_model=KnowledgeBaseRead, status_code=status.HTTP_201_CREATED)
async def create_knowledge_base(
    data: KnowledgeBaseCreate,
    service: KnowledgeBaseSvc,
    current_user: CurrentUser,
    active_org: ActiveOrg,
) -> Any:
    """Create a new Knowledge Base."""
    return await service.create(
        data,
        user_id=str(current_user.id),
        organization_id=str(active_org.id),
        is_app_admin=getattr(current_user, "is_app_admin", False),
    )


@router.get("/{kb_id}", response_model=KnowledgeBaseRead)
async def get_knowledge_base(
    kb_id: str,
    service: KnowledgeBaseSvc,
    current_user: CurrentUser,
    active_org: ActiveOrg,
) -> Any:
    """Get a Knowledge Base by ID."""
    return await service.get(kb_id, user_id=str(current_user.id), organization_id=str(active_org.id))


@router.patch("/{kb_id}", response_model=KnowledgeBaseRead)
async def update_knowledge_base(
    kb_id: str,
    data: KnowledgeBaseUpdate,
    service: KnowledgeBaseSvc,
    current_user: CurrentUser,
    active_org: ActiveOrg,
) -> Any:
    """Update name or description of a Knowledge Base."""
    return await service.update(
        kb_id, data,
        user_id=str(current_user.id),
        organization_id=str(active_org.id),
        is_app_admin=getattr(current_user, "is_app_admin", False),
    )


@router.delete("/{kb_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_knowledge_base(
    kb_id: str,
    service: KnowledgeBaseSvc,
    current_user: CurrentUser,
    active_org: ActiveOrg,
) -> None:
    """Delete a Knowledge Base. Default KBs cannot be deleted."""
    await service.delete(
        kb_id,
        user_id=str(current_user.id),
        organization_id=str(active_org.id),
        is_app_admin=getattr(current_user, "is_app_admin", False),
    )


{%- endif %}
{%- else %}
"""Knowledge Base routes — not configured."""
{%- endif %}
