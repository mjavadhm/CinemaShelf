"""Persistence queries for LLM providers, models, and usage logs (no internal commits)."""

from collections.abc import Sequence
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.modules.llm.models import LLMModel, LLMProvider, LLMUsageLog


class LLMRepository:
    """Repository for LLM router persistence operations."""

    def __init__(self, session: Session) -> None:
        self.session = session

    # --- Providers ---

    def create_provider(self, provider: LLMProvider) -> LLMProvider:
        self.session.add(provider)
        self.session.flush()
        return provider

    def get_provider_by_id(self, provider_id: int) -> LLMProvider | None:
        stmt = (
            select(LLMProvider)
            .where(LLMProvider.id == provider_id)
            .options(selectinload(LLMProvider.models))
        )
        return self.session.scalars(stmt).first()

    def get_provider_by_name(self, name: str) -> LLMProvider | None:
        stmt = (
            select(LLMProvider)
            .where(LLMProvider.name == name)
            .options(selectinload(LLMProvider.models))
        )
        return self.session.scalars(stmt).first()

    def list_providers(self) -> Sequence[LLMProvider]:
        stmt = (
            select(LLMProvider)
            .options(selectinload(LLMProvider.models))
            .order_by(LLMProvider.priority.asc(), LLMProvider.name.asc())
        )
        return self.session.scalars(stmt).all()

    def delete_provider(self, provider: LLMProvider) -> None:
        self.session.delete(provider)

    # --- Models ---

    def create_model(self, model: LLMModel) -> LLMModel:
        self.session.add(model)
        self.session.flush()
        return model

    def get_model_by_id(self, model_id: int) -> LLMModel | None:
        stmt = (
            select(LLMModel)
            .where(LLMModel.id == model_id)
            .options(selectinload(LLMModel.provider))
        )
        return self.session.scalars(stmt).first()

    def list_models(
        self,
        provider_id: int | None = None,
        only_enabled: bool = False,
    ) -> Sequence[LLMModel]:
        stmt = select(LLMModel).options(selectinload(LLMModel.provider))
        if provider_id is not None:
            stmt = stmt.where(LLMModel.provider_id == provider_id)
        if only_enabled:
            stmt = stmt.where(LLMModel.is_enabled == True)  # noqa: E712
        stmt = stmt.order_by(LLMModel.priority.asc(), LLMModel.model_name.asc())
        return self.session.scalars(stmt).all()

    def list_models_for_provider(self, provider_id: int) -> Sequence[LLMModel]:
        return self.list_models(provider_id=provider_id)

    def list_all_active_models(self) -> Sequence[LLMModel]:
        stmt = (
            select(LLMModel)
            .join(LLMProvider, LLMProvider.id == LLMModel.provider_id)
            .where(LLMModel.is_enabled == True)  # noqa: E712
            .where(LLMProvider.is_enabled == True)  # noqa: E712
            .options(selectinload(LLMModel.provider))
            .order_by(
                LLMProvider.priority.asc(),
                LLMModel.priority.asc(),
                LLMModel.id.asc(),
            )
        )
        return self.session.scalars(stmt).all()

    def delete_model(self, model: LLMModel) -> None:
        self.session.delete(model)

    # --- Usage Logs ---

    def add_usage_log(self, log: LLMUsageLog) -> LLMUsageLog:
        self.session.add(log)
        self.session.flush()
        return log

    def list_usage_logs(
        self, limit: int = 50, offset: int = 0
    ) -> Sequence[LLMUsageLog]:
        stmt = (
            select(LLMUsageLog)
            .order_by(LLMUsageLog.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return self.session.scalars(stmt).all()

    def get_usage_summary(self) -> dict[str, Any]:
        total_calls = self.session.scalar(select(func.count(LLMUsageLog.id))) or 0
        successful_calls = (
            self.session.scalar(
                select(func.count(LLMUsageLog.id)).where(LLMUsageLog.success == True)  # noqa: E712
            )
            or 0
        )
        failed_calls = total_calls - successful_calls

        total_prompt = (
            self.session.scalar(select(func.sum(LLMUsageLog.prompt_tokens))) or 0
        )
        total_completion = (
            self.session.scalar(select(func.sum(LLMUsageLog.completion_tokens))) or 0
        )
        total_cost = self.session.scalar(select(func.sum(LLMUsageLog.cost_usd))) or 0.0

        return {
            "total_calls": total_calls,
            "successful_calls": successful_calls,
            "failed_calls": failed_calls,
            "total_prompt_tokens": int(total_prompt),
            "total_completion_tokens": int(total_completion),
            "total_cost_usd": round(float(total_cost), 6),
        }
