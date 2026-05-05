{%- if cookiecutter.enable_teams and cookiecutter.enable_rag and cookiecutter.use_jwt %}
{%- if cookiecutter.use_postgresql %}
"""Knowledge Base service (PostgreSQL async)."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthorizationError, NotFoundError
from app.db.models.knowledge_base import KBScope, KnowledgeBase
from app.repositories import knowledge_base_repo
from app.schemas.knowledge_base import KnowledgeBaseCreate, KnowledgeBaseUpdate


class KnowledgeBaseService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_accessible(
        self,
        user_id: UUID,
        organization_id: UUID | None = None,
    ) -> list[KnowledgeBase]:
        return await knowledge_base_repo.get_accessible(
            self.db, user_id=user_id, organization_id=organization_id
        )

    async def get(
        self,
        kb_id: UUID,
        *,
        user_id: UUID,
        organization_id: UUID | None = None,
    ) -> KnowledgeBase:
        kb = await knowledge_base_repo.get_by_id(self.db, kb_id)
        if not kb:
            raise NotFoundError(message="Knowledge base not found", details={"kb_id": str(kb_id)})
        self._check_read_access(kb, user_id=user_id, organization_id=organization_id)
        return kb

    async def create(
        self,
        data: KnowledgeBaseCreate,
        *,
        user_id: UUID,
        organization_id: UUID | None = None,
        is_app_admin: bool = False,
    ) -> KnowledgeBase:
        self._check_create_permission(
            scope=data.scope,
            user_id=user_id,
            organization_id=organization_id,
            is_app_admin=is_app_admin,
        )
        owner_user_id = user_id if data.scope == KBScope.PERSONAL.value else None
        org_id = organization_id if data.scope in (KBScope.ORG.value, KBScope.PERSONAL.value) else None
        return await knowledge_base_repo.create(
            self.db,
            name=data.name,
            collection_name=data.collection_name,
            scope=data.scope,
            description=data.description,
            owner_user_id=owner_user_id,
            organization_id=org_id,
        )

    async def create_default_for_org(
        self,
        organization_id: UUID,
        collection_name: str,
    ) -> KnowledgeBase:
        existing = await knowledge_base_repo.get_default_for_org(self.db, organization_id)
        if existing:
            return existing
        return await knowledge_base_repo.create(
            self.db,
            name="Default",
            collection_name=collection_name,
            scope=KBScope.ORG.value,
            description="Default knowledge base",
            organization_id=organization_id,
            is_default=True,
        )

    async def update(
        self,
        kb_id: UUID,
        data: KnowledgeBaseUpdate,
        *,
        user_id: UUID,
        organization_id: UUID | None = None,
        is_app_admin: bool = False,
    ) -> KnowledgeBase:
        kb = await knowledge_base_repo.get_by_id(self.db, kb_id)
        if not kb:
            raise NotFoundError(message="Knowledge base not found", details={"kb_id": str(kb_id)})
        self._check_write_access(kb, user_id=user_id, organization_id=organization_id, is_app_admin=is_app_admin)
        return await knowledge_base_repo.update(
            self.db,
            db_kb=kb,
            name=data.name,
            description=data.description,
        )

    async def delete(
        self,
        kb_id: UUID,
        *,
        user_id: UUID,
        organization_id: UUID | None = None,
        is_app_admin: bool = False,
    ) -> None:
        kb = await knowledge_base_repo.get_by_id(self.db, kb_id)
        if not kb:
            raise NotFoundError(message="Knowledge base not found", details={"kb_id": str(kb_id)})
        if kb.is_default:
            from app.core.exceptions import BadRequestError
            raise BadRequestError(message="Cannot delete the default knowledge base")
        self._check_write_access(kb, user_id=user_id, organization_id=organization_id, is_app_admin=is_app_admin)
        await knowledge_base_repo.delete(self.db, kb_id)

    def _check_read_access(
        self,
        kb: KnowledgeBase,
        *,
        user_id: UUID,
        organization_id: UUID | None,
    ) -> None:
        if kb.scope == KBScope.APP.value:
            return
        if kb.scope == KBScope.PERSONAL.value and str(kb.owner_user_id) == str(user_id):
            return
        if kb.scope == KBScope.ORG.value and organization_id and str(kb.organization_id) == str(organization_id):
            return
        raise NotFoundError(message="Knowledge base not found", details={"kb_id": str(kb.id)})

    def _check_write_access(
        self,
        kb: KnowledgeBase,
        *,
        user_id: UUID,
        organization_id: UUID | None,
        is_app_admin: bool,
    ) -> None:
        if kb.scope == KBScope.APP.value and not is_app_admin:
            raise AuthorizationError(message="App admin required to modify app-scoped knowledge base")
        if kb.scope == KBScope.PERSONAL.value and str(kb.owner_user_id) != str(user_id):
            raise AuthorizationError(message="Only the owner can modify this knowledge base")
        if kb.scope == KBScope.ORG.value:
            if not organization_id or str(kb.organization_id) != str(organization_id):
                raise AuthorizationError(message="Not a member of this knowledge base's organization")

    def _check_create_permission(
        self,
        *,
        scope: str,
        user_id: UUID,
        organization_id: UUID | None,
        is_app_admin: bool,
    ) -> None:
        if scope == KBScope.APP.value and not is_app_admin:
            raise AuthorizationError(message="App admin required to create app-scoped knowledge base")
        if scope == KBScope.ORG.value and not organization_id:
            raise AuthorizationError(message="Organization context required to create org-scoped knowledge base")

{%- elif cookiecutter.use_sqlite %}
"""Knowledge Base service (SQLite sync)."""

from sqlalchemy.orm import Session

from app.core.exceptions import AuthorizationError, NotFoundError
from app.db.models.knowledge_base import KBScope, KnowledgeBase
from app.repositories import knowledge_base_repo
from app.schemas.knowledge_base import KnowledgeBaseCreate, KnowledgeBaseUpdate


class KnowledgeBaseService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_accessible(
        self,
        user_id: str,
        organization_id: str | None = None,
    ) -> list[KnowledgeBase]:
        return knowledge_base_repo.get_accessible(
            self.db, user_id=user_id, organization_id=organization_id
        )

    def get(
        self,
        kb_id: str,
        *,
        user_id: str,
        organization_id: str | None = None,
    ) -> KnowledgeBase:
        kb = knowledge_base_repo.get_by_id(self.db, kb_id)
        if not kb:
            raise NotFoundError(message="Knowledge base not found", details={"kb_id": kb_id})
        self._check_read_access(kb, user_id=user_id, organization_id=organization_id)
        return kb

    def create(
        self,
        data: KnowledgeBaseCreate,
        *,
        user_id: str,
        organization_id: str | None = None,
        is_app_admin: bool = False,
    ) -> KnowledgeBase:
        self._check_create_permission(
            scope=data.scope,
            user_id=user_id,
            organization_id=organization_id,
            is_app_admin=is_app_admin,
        )
        owner_user_id = user_id if data.scope == KBScope.PERSONAL.value else None
        org_id = organization_id if data.scope in (KBScope.ORG.value, KBScope.PERSONAL.value) else None
        return knowledge_base_repo.create(
            self.db,
            name=data.name,
            collection_name=data.collection_name,
            scope=data.scope,
            description=data.description,
            owner_user_id=owner_user_id,
            organization_id=org_id,
        )

    def create_default_for_org(
        self,
        organization_id: str,
        collection_name: str,
    ) -> KnowledgeBase:
        existing = knowledge_base_repo.get_default_for_org(self.db, organization_id)
        if existing:
            return existing
        return knowledge_base_repo.create(
            self.db,
            name="Default",
            collection_name=collection_name,
            scope=KBScope.ORG.value,
            description="Default knowledge base",
            organization_id=organization_id,
            is_default=True,
        )

    def update(
        self,
        kb_id: str,
        data: KnowledgeBaseUpdate,
        *,
        user_id: str,
        organization_id: str | None = None,
        is_app_admin: bool = False,
    ) -> KnowledgeBase:
        kb = knowledge_base_repo.get_by_id(self.db, kb_id)
        if not kb:
            raise NotFoundError(message="Knowledge base not found", details={"kb_id": kb_id})
        self._check_write_access(kb, user_id=user_id, organization_id=organization_id, is_app_admin=is_app_admin)
        return knowledge_base_repo.update(self.db, db_kb=kb, name=data.name, description=data.description)

    def delete(
        self,
        kb_id: str,
        *,
        user_id: str,
        organization_id: str | None = None,
        is_app_admin: bool = False,
    ) -> None:
        kb = knowledge_base_repo.get_by_id(self.db, kb_id)
        if not kb:
            raise NotFoundError(message="Knowledge base not found", details={"kb_id": kb_id})
        if kb.is_default:
            from app.core.exceptions import BadRequestError
            raise BadRequestError(message="Cannot delete the default knowledge base")
        self._check_write_access(kb, user_id=user_id, organization_id=organization_id, is_app_admin=is_app_admin)
        knowledge_base_repo.delete(self.db, kb_id)

    def _check_read_access(
        self,
        kb: KnowledgeBase,
        *,
        user_id: str,
        organization_id: str | None,
    ) -> None:
        if kb.scope == KBScope.APP.value:
            return
        if kb.scope == KBScope.PERSONAL.value and str(kb.owner_user_id) == str(user_id):
            return
        if kb.scope == KBScope.ORG.value and organization_id and str(kb.organization_id) == str(organization_id):
            return
        raise NotFoundError(message="Knowledge base not found", details={"kb_id": str(kb.id)})

    def _check_write_access(
        self,
        kb: KnowledgeBase,
        *,
        user_id: str,
        organization_id: str | None,
        is_app_admin: bool,
    ) -> None:
        if kb.scope == KBScope.APP.value and not is_app_admin:
            raise AuthorizationError(message="App admin required to modify app-scoped knowledge base")
        if kb.scope == KBScope.PERSONAL.value and str(kb.owner_user_id) != str(user_id):
            raise AuthorizationError(message="Only the owner can modify this knowledge base")
        if kb.scope == KBScope.ORG.value:
            if not organization_id or str(kb.organization_id) != str(organization_id):
                raise AuthorizationError(message="Not a member of this knowledge base's organization")

    def _check_create_permission(
        self,
        *,
        scope: str,
        user_id: str,
        organization_id: str | None,
        is_app_admin: bool,
    ) -> None:
        if scope == KBScope.APP.value and not is_app_admin:
            raise AuthorizationError(message="App admin required to create app-scoped knowledge base")
        if scope == KBScope.ORG.value and not organization_id:
            raise AuthorizationError(message="Organization context required to create org-scoped knowledge base")

{%- elif cookiecutter.use_mongodb %}
"""Knowledge Base service (MongoDB async)."""

from app.core.exceptions import AuthorizationError, NotFoundError
from app.db.models.knowledge_base import KBScope, KnowledgeBase
from app.repositories import knowledge_base_repo
from app.schemas.knowledge_base import KnowledgeBaseCreate, KnowledgeBaseUpdate


class KnowledgeBaseService:
    async def list_accessible(
        self,
        user_id: str,
        organization_id: str | None = None,
    ) -> list[KnowledgeBase]:
        return await knowledge_base_repo.get_accessible(
            user_id=user_id, organization_id=organization_id
        )

    async def get(
        self,
        kb_id: str,
        *,
        user_id: str,
        organization_id: str | None = None,
    ) -> KnowledgeBase:
        kb = await knowledge_base_repo.get_by_id(kb_id)
        if not kb:
            raise NotFoundError(message="Knowledge base not found", details={"kb_id": kb_id})
        self._check_read_access(kb, user_id=user_id, organization_id=organization_id)
        return kb

    async def create(
        self,
        data: KnowledgeBaseCreate,
        *,
        user_id: str,
        organization_id: str | None = None,
        is_app_admin: bool = False,
    ) -> KnowledgeBase:
        self._check_create_permission(
            scope=data.scope,
            user_id=user_id,
            organization_id=organization_id,
            is_app_admin=is_app_admin,
        )
        owner_user_id = user_id if data.scope == KBScope.PERSONAL.value else None
        org_id = organization_id if data.scope in (KBScope.ORG.value, KBScope.PERSONAL.value) else None
        return await knowledge_base_repo.create(
            name=data.name,
            collection_name=data.collection_name,
            scope=data.scope,
            description=data.description,
            owner_user_id=owner_user_id,
            organization_id=org_id,
        )

    async def create_default_for_org(
        self,
        organization_id: str,
        collection_name: str,
    ) -> KnowledgeBase:
        existing = await knowledge_base_repo.get_default_for_org(organization_id)
        if existing:
            return existing
        return await knowledge_base_repo.create(
            name="Default",
            collection_name=collection_name,
            scope=KBScope.ORG.value,
            description="Default knowledge base",
            organization_id=organization_id,
            is_default=True,
        )

    async def update(
        self,
        kb_id: str,
        data: KnowledgeBaseUpdate,
        *,
        user_id: str,
        organization_id: str | None = None,
        is_app_admin: bool = False,
    ) -> KnowledgeBase:
        kb = await knowledge_base_repo.get_by_id(kb_id)
        if not kb:
            raise NotFoundError(message="Knowledge base not found", details={"kb_id": kb_id})
        self._check_write_access(kb, user_id=user_id, organization_id=organization_id, is_app_admin=is_app_admin)
        return await knowledge_base_repo.update(db_kb=kb, name=data.name, description=data.description)

    async def delete(
        self,
        kb_id: str,
        *,
        user_id: str,
        organization_id: str | None = None,
        is_app_admin: bool = False,
    ) -> None:
        kb = await knowledge_base_repo.get_by_id(kb_id)
        if not kb:
            raise NotFoundError(message="Knowledge base not found", details={"kb_id": kb_id})
        if kb.is_default:
            from app.core.exceptions import BadRequestError
            raise BadRequestError(message="Cannot delete the default knowledge base")
        self._check_write_access(kb, user_id=user_id, organization_id=organization_id, is_app_admin=is_app_admin)
        await knowledge_base_repo.delete(kb_id)

    def _check_read_access(self, kb: KnowledgeBase, *, user_id: str, organization_id: str | None) -> None:
        if kb.scope == KBScope.APP.value:
            return
        if kb.scope == KBScope.PERSONAL.value and str(kb.owner_user_id) == str(user_id):
            return
        if kb.scope == KBScope.ORG.value and organization_id and str(kb.organization_id) == str(organization_id):
            return
        raise NotFoundError(message="Knowledge base not found", details={"kb_id": str(kb.id)})

    def _check_write_access(self, kb: KnowledgeBase, *, user_id: str, organization_id: str | None, is_app_admin: bool) -> None:
        if kb.scope == KBScope.APP.value and not is_app_admin:
            raise AuthorizationError(message="App admin required to modify app-scoped knowledge base")
        if kb.scope == KBScope.PERSONAL.value and str(kb.owner_user_id) != str(user_id):
            raise AuthorizationError(message="Only the owner can modify this knowledge base")
        if kb.scope == KBScope.ORG.value:
            if not organization_id or str(kb.organization_id) != str(organization_id):
                raise AuthorizationError(message="Not a member of this knowledge base's organization")

    def _check_create_permission(self, *, scope: str, user_id: str, organization_id: str | None, is_app_admin: bool) -> None:
        if scope == KBScope.APP.value and not is_app_admin:
            raise AuthorizationError(message="App admin required to create app-scoped knowledge base")
        if scope == KBScope.ORG.value and not organization_id:
            raise AuthorizationError(message="Organization context required to create org-scoped knowledge base")

{%- endif %}
{%- else %}
"""Knowledge Base service — not configured."""
{%- endif %}
