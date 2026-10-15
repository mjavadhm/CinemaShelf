"""Pydantic schemas and DTOs for the LLM router module."""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, computed_field


class LLMModelBase(BaseModel):
    model_name: str
    display_name: str | None = None
    input_price_per_1m: float = 0.0
    output_price_per_1m: float = 0.0
    is_enabled: bool = True
    priority: int = 1


class LLMModelCreate(LLMModelBase):
    provider_id: int | None = None


class LLMModelUpdate(BaseModel):
    display_name: str | None = None
    input_price_per_1m: float | None = None
    output_price_per_1m: float | None = None
    is_enabled: bool | None = None
    priority: int | None = None


class LLMModelResponse(LLMModelBase):
    id: int
    provider_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LLMProviderBase(BaseModel):
    name: str
    base_url: str
    api_key: str | None = None
    is_enabled: bool = True
    priority: int = 1


class LLMProviderCreate(LLMProviderBase):
    pass


class LLMProviderUpdate(BaseModel):
    name: str | None = None
    base_url: str | None = None
    api_key: str | None = None
    is_enabled: bool | None = None
    priority: int | None = None


class LLMProviderResponse(BaseModel):
    id: int
    name: str
    base_url: str
    api_key: str | None = None
    is_enabled: bool
    priority: int
    models: list[LLMModelResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def api_key_masked(self) -> str | None:
        if not self.api_key:
            return None
        if len(self.api_key) <= 8:
            return "••••"
        return f"••••{self.api_key[-4:]}"

    model_config = ConfigDict(from_attributes=True)


class LLMRemoteDiscoveredModel(BaseModel):
    id: str
    name: str
    in_price_1m: float = 0.0
    out_price_1m: float = 0.0


class LLMUsageLogResponse(BaseModel):
    id: int
    agent_type: str
    provider_name: str
    model_name: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
    success: bool
    error_message: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LLMUsageSummaryResponse(BaseModel):
    total_calls: int
    successful_calls: int
    failed_calls: int
    total_prompt_tokens: int
    total_completion_tokens: int
    total_cost_usd: float
    recent_logs: list[LLMUsageLogResponse] = Field(default_factory=list)


class LLMTestPromptRequest(BaseModel):
    provider_id: int | None = None
    model_id: int | None = None
    system_prompt: str = "You are a helpful movie archivist."
    user_prompt: str = "Briefly recommend 3 classic films."


class LLMTestPromptResponse(BaseModel):
    success: bool
    provider_name: str
    model_name: str
    response_content: str | None = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0
    error_message: str | None = None
