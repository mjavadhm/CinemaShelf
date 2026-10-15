"""SQLAlchemy ORM models for LLM multi-model router and cost tracking."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin


class LLMProvider(Base, TimestampMixin):
    """An OpenAI-compatible API provider (e.g. OpenAI, OpenRouter, Groq, Ollama, 9Router)."""

    __tablename__ = "llm_providers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    base_url: Mapped[str] = mapped_column(String(500), nullable=False)
    api_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    models: Mapped[list["LLMModel"]] = relationship(
        "LLMModel",
        back_populates="provider",
        cascade="all, delete-orphan",
    )


class LLMModel(Base, TimestampMixin):
    """Specific model available under a provider with input/output pricing per 1M tokens."""

    __tablename__ = "llm_models"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    provider_id: Mapped[int] = mapped_column(
        ForeignKey("llm_providers.id", ondelete="CASCADE"), index=True, nullable=False
    )
    model_name: Mapped[str] = mapped_column(String(200), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    input_price_per_1m: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    output_price_per_1m: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    provider: Mapped["LLMProvider"] = relationship("LLMProvider", back_populates="models")


class LLMUsageLog(Base, TimestampMixin):
    """Granular record of an LLM invocation for cost and audit tracking."""

    __tablename__ = "llm_usage_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    agent_type: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    provider_name: Mapped[str] = mapped_column(String(100), nullable=False)
    model_name: Mapped[str] = mapped_column(String(200), nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
