{%- if cookiecutter.use_jwt and cookiecutter.use_postgresql and cookiecutter.use_sqlmodel %}
"""User database model using SQLModel."""

import uuid
from enum import StrEnum
{%- if cookiecutter.enable_session_management %}
from typing import TYPE_CHECKING
{%- endif %}

from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import Field, Relationship, SQLModel

from app.db.base import TimestampMixin

{%- if cookiecutter.enable_session_management %}
if TYPE_CHECKING:
    from app.db.models.session import Session
{%- endif %}


class UserRole(StrEnum):
    """User role enumeration.

    Roles hierarchy (higher includes lower permissions):
    - ADMIN: Full system access, can manage users and settings
    - USER: Standard user access
    """

    ADMIN = "admin"
    USER = "user"


class User(TimestampMixin, SQLModel, table=True):
    """User model."""

    __tablename__ = "users"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(PG_UUID(as_uuid=True), primary_key=True),
    )
    email: str = Field(
        sa_column=Column(String(255), unique=True, index=True, nullable=False),
    )
    hashed_password: str | None = Field(default=None, max_length=255)
    full_name: str | None = Field(default=None, max_length=255)
    is_active: bool = Field(default=True)
    role: str = Field(default=UserRole.USER.value, max_length=50)
{%- if cookiecutter.enable_teams %}
    is_app_admin: bool = Field(default=False)
{%- endif %}
{%- if cookiecutter.enable_oauth %}
    oauth_provider: str | None = Field(default=None, sa_column=Column(String(50), nullable=True, index=True))
    oauth_id: str | None = Field(default=None, sa_column=Column(String(255), nullable=True, index=True))
{%- endif %}
    avatar_url: str | None = Field(default=None, sa_column=Column(String(500), nullable=True))

{%- if cookiecutter.enable_session_management %}

    # Relationship to sessions
    sessions: list["Session"] = Relationship(back_populates="user")
{%- endif %}

    @property
    def user_role(self) -> UserRole:
        """Get role as enum."""
        return UserRole(self.role)

    def has_role(self, required_role: UserRole) -> bool:
        """Check if user has the required role or higher.

        Admin role has access to everything.
        """
        if self.role == UserRole.ADMIN.value:
            return True
        return self.role == required_role.value

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"


{%- elif cookiecutter.use_jwt and cookiecutter.use_postgresql %}
"""User database model."""

import uuid
from enum import StrEnum
{%- if cookiecutter.enable_session_management %}
from typing import TYPE_CHECKING
{%- endif %}

from sqlalchemy import Boolean, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column{% if cookiecutter.enable_session_management %}, relationship{% endif %}

from app.db.base import Base, TimestampMixin

{%- if cookiecutter.enable_session_management %}
if TYPE_CHECKING:
    from app.db.models.session import Session
{%- endif %}


class UserRole(StrEnum):
    """User role enumeration.

    Roles hierarchy (higher includes lower permissions):
    - ADMIN: Full system access, can manage users and settings
    - USER: Standard user access
    """

    ADMIN = "admin"
    USER = "user"


class User(Base, TimestampMixin):
    """User model."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    role: Mapped[str] = mapped_column(String(50), default=UserRole.USER.value, nullable=False)
{%- if cookiecutter.enable_teams %}
    is_app_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
{%- endif %}
{%- if cookiecutter.enable_oauth %}
    oauth_provider: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    oauth_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
{%- endif %}
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

{%- if cookiecutter.enable_session_management %}

    # Relationship to sessions
    sessions: Mapped[list["Session"]] = relationship(
        "Session", back_populates="user", cascade="all, delete-orphan"
    )
{%- endif %}

    @property
    def user_role(self) -> UserRole:
        """Get role as enum."""
        return UserRole(self.role)

    def has_role(self, required_role: UserRole) -> bool:
        """Check if user has the required role or higher.

        Admin role has access to everything.
        """
        if self.role == UserRole.ADMIN.value:
            return True
        return self.role == required_role.value

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"


{%- elif cookiecutter.use_jwt and cookiecutter.use_sqlite and cookiecutter.use_sqlmodel %}
"""User database model using SQLModel."""

import uuid
from enum import StrEnum
{%- if cookiecutter.enable_session_management %}
from typing import TYPE_CHECKING
{%- endif %}

from sqlalchemy import Column, String
from sqlmodel import Field, Relationship, SQLModel

from app.db.base import TimestampMixin

{%- if cookiecutter.enable_session_management %}
if TYPE_CHECKING:
    from app.db.models.session import Session
{%- endif %}


class UserRole(StrEnum):
    """User role enumeration.

    Roles hierarchy (higher includes lower permissions):
    - ADMIN: Full system access, can manage users and settings
    - USER: Standard user access
    """

    ADMIN = "admin"
    USER = "user"


class User(TimestampMixin, SQLModel, table=True):
    """User model."""

    __tablename__ = "users"

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        sa_column=Column(String(36), primary_key=True),
    )
    email: str = Field(
        sa_column=Column(String(255), unique=True, index=True, nullable=False),
    )
    hashed_password: str | None = Field(default=None, max_length=255)
    full_name: str | None = Field(default=None, max_length=255)
    is_active: bool = Field(default=True)
    role: str = Field(default=UserRole.USER.value, max_length=50)
{%- if cookiecutter.enable_teams %}
    is_app_admin: bool = Field(default=False)
{%- endif %}
{%- if cookiecutter.enable_oauth %}
    oauth_provider: str | None = Field(default=None, sa_column=Column(String(50), nullable=True, index=True))
    oauth_id: str | None = Field(default=None, sa_column=Column(String(255), nullable=True, index=True))
{%- endif %}
    avatar_url: str | None = Field(default=None, sa_column=Column(String(500), nullable=True))

{%- if cookiecutter.enable_session_management %}

    # Relationship to sessions
    sessions: list["Session"] = Relationship(back_populates="user")
{%- endif %}

    @property
    def user_role(self) -> UserRole:
        """Get role as enum."""
        return UserRole(self.role)

    def has_role(self, required_role: UserRole) -> bool:
        """Check if user has the required role or higher.

        Admin role has access to everything.
        """
        if self.role == UserRole.ADMIN.value:
            return True
        return self.role == required_role.value

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"


{%- elif cookiecutter.use_jwt and cookiecutter.use_sqlite %}
"""User database model."""

import uuid
from enum import StrEnum
{%- if cookiecutter.enable_session_management %}
from typing import TYPE_CHECKING
{%- endif %}

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column{% if cookiecutter.enable_session_management %}, relationship{% endif %}

from app.db.base import Base, TimestampMixin

{%- if cookiecutter.enable_session_management %}
if TYPE_CHECKING:
    from app.db.models.session import Session
{%- endif %}


class UserRole(StrEnum):
    """User role enumeration.

    Roles hierarchy (higher includes lower permissions):
    - ADMIN: Full system access, can manage users and settings
    - USER: Standard user access
    """

    ADMIN = "admin"
    USER = "user"


class User(Base, TimestampMixin):
    """User model."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    role: Mapped[str] = mapped_column(String(50), default=UserRole.USER.value, nullable=False)
{%- if cookiecutter.enable_teams %}
    is_app_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
{%- endif %}
{%- if cookiecutter.enable_oauth %}
    oauth_provider: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    oauth_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
{%- endif %}
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

{%- if cookiecutter.enable_session_management %}

    # Relationship to sessions
    sessions: Mapped[list["Session"]] = relationship(
        "Session", back_populates="user", cascade="all, delete-orphan"
    )
{%- endif %}

    @property
    def user_role(self) -> UserRole:
        """Get role as enum."""
        return UserRole(self.role)

    def has_role(self, required_role: UserRole) -> bool:
        """Check if user has the required role or higher.

        Admin role has access to everything.
        """
        if self.role == UserRole.ADMIN.value:
            return True
        return self.role == required_role.value

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"


{%- elif cookiecutter.use_jwt and cookiecutter.use_mongodb %}
"""User document model for MongoDB."""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Optional

from beanie import Document
from pydantic import EmailStr, Field


class UserRole(StrEnum):
    """User role enumeration.

    Roles hierarchy (higher includes lower permissions):
    - ADMIN: Full system access, can manage users and settings
    - USER: Standard user access
    """

    ADMIN = "admin"
    USER = "user"


class User(Document):
    """User document model."""

    email: EmailStr
    hashed_password: Optional[str] = None
    full_name: Optional[str] = None
    is_active: bool = True
    role: str = UserRole.USER.value
{%- if cookiecutter.enable_teams %}
    is_app_admin: bool = False
{%- endif %}
{%- if cookiecutter.enable_oauth %}
    oauth_provider: Optional[str] = None
    oauth_id: Optional[str] = None
{%- endif %}
    avatar_url: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: Optional[datetime] = None

    @property
    def user_role(self) -> UserRole:
        """Get role as enum."""
        return UserRole(self.role)

    def has_role(self, required_role: UserRole) -> bool:
        """Check if user has the required role or higher.

        Admin role has access to everything.
        """
        if self.role == UserRole.ADMIN.value:
            return True
        return self.role == required_role.value

    class Settings:
        name = "users"
        indexes = [
            "email",
        ]


{%- else %}
"""User model - not configured."""
{%- endif %}
