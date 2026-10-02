from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Item(Base):
    """A normalized thing that might deserve your attention.

    Everything a source produces — an assignment, an email — becomes one of these,
    so the rules engine and notifier never need to know where it came from.
    """

    __tablename__ = "items"
    __table_args__ = (
        UniqueConstraint("source", "external_id", name="uq_items_source_external_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(32), index=True)      # canvas | gmail | graph
    external_id: Mapped[str] = mapped_column(String(255))
    kind: Mapped[str] = mapped_column(String(32))                    # assignment | mail
    title: Mapped[str] = mapped_column(String(512))
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    sender: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    context: Mapped[str | None] = mapped_column(String(255), nullable=True)  # course name, folder
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    due_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    score: Mapped[int] = mapped_column(Integer, default=0)
    raw: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    notifications: Mapped[list["Notification"]] = relationship(
        back_populates="item", cascade="all, delete-orphan"
    )


class Notification(Base):
    """One row per (item, stage) actually sent.

    The unique constraint is the idempotency guarantee: a retried poll or a second
    replica cannot notify you twice for the same thing.
    """

    __tablename__ = "notifications"
    __table_args__ = (UniqueConstraint("item_id", "stage", name="uq_notifications_item_stage"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id", ondelete="CASCADE"), index=True)
    stage: Mapped[str] = mapped_column(String(32))  # new | due_48h | due_2h
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    item: Mapped[Item] = relationship(back_populates="notifications")


class Rule(Base):
    """A scoring rule. Deterministic and inspectable on purpose — when a
    notification misfires you need to know exactly which rule fired."""

    __tablename__ = "rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    field: Mapped[str] = mapped_column(String(32))       # title | body | sender | context | kind
    match_type: Mapped[str] = mapped_column(String(16))  # contains | equals | domain | prefix
    value: Mapped[str] = mapped_column(String(255))
    weight: Mapped[int] = mapped_column(Integer, default=5)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
