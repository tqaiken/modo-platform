import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class UserRole(str, enum.Enum):
    SUPER_ADMIN = "SUPER_ADMIN"
    CURATOR = "CURATOR"
    VERIFIER = "VERIFIER"
    DEVELOPER = "DEVELOPER"


class User(Base):
    __tablename__ = "users"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    email = Column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    full_name = Column(
        String(255),
        nullable=False,
    )

    hashed_password = Column(
        String(255),
        nullable=False,
    )

    role = Column(
        Enum(UserRole),
        nullable=False,
        default=UserRole.DEVELOPER,
    )

    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
    )

    # SUPER_ADMIN назначает предмет разработчику и верификатору.
    # Для CURATOR и SUPER_ADMIN поле может быть пустым.
    subject_id = Column(
        Integer,
        ForeignKey("subjects.id"),
        nullable=True,
        index=True,
    )

    subject = relationship(
        "Subject",
        lazy="joined",
    )

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self):
        return (
            f"<User {self.email} "
            f"({self.role.value}) "
            f"subject_id={self.subject_id}>"
        )