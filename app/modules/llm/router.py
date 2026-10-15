"""FastAPI HTTP endpoints for LLM multi-model router, providers, and cost tracking."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db_session
from app.modules.llm.schemas import (
    LLMModelCreate,
    LLMModelResponse,
    LLMModelUpdate,
    LLMProviderCreate,
    LLMProviderResponse,
    LLMProviderUpdate,
    LLMRemoteDiscoveredModel,
    LLMTestPromptRequest,
    LLMTestPromptResponse,
    LLMUsageSummaryResponse,
)
from app.modules.llm.service import LLMService

router = APIRouter(prefix="/llm", tags=["llm"])


def get_llm_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> LLMService:
    """Dependency injector for LLMService."""
    return LLMService(session=session)


# --- Providers ---


@router.post(
    "/providers",
    response_model=LLMProviderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new LLM provider",
)
def create_llm_provider(
    request: LLMProviderCreate,
    service: Annotated[LLMService, Depends(get_llm_service)],
) -> LLMProviderResponse:
    provider = service.create_provider(request)
    return LLMProviderResponse.model_validate(provider)


@router.get(
    "/providers",
    response_model=list[LLMProviderResponse],
    summary="List all configured LLM providers",
)
def list_llm_providers(
    service: Annotated[LLMService, Depends(get_llm_service)],
) -> list[LLMProviderResponse]:
    providers = service.list_providers()
    return [LLMProviderResponse.model_validate(p) for p in providers]


@router.get(
    "/providers/{id}",
    response_model=LLMProviderResponse,
    summary="Get details of an LLM provider",
)
def get_llm_provider(
    id: int,
    service: Annotated[LLMService, Depends(get_llm_service)],
) -> LLMProviderResponse:
    provider = service.get_provider(id)
    return LLMProviderResponse.model_validate(provider)


@router.patch(
    "/providers/{id}",
    response_model=LLMProviderResponse,
    summary="Update LLM provider settings",
)
def update_llm_provider(
    id: int,
    request: LLMProviderUpdate,
    service: Annotated[LLMService, Depends(get_llm_service)],
) -> LLMProviderResponse:
    provider = service.update_provider(id, request)
    return LLMProviderResponse.model_validate(provider)


@router.delete(
    "/providers/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an LLM provider",
)
def delete_llm_provider(
    id: int,
    service: Annotated[LLMService, Depends(get_llm_service)],
) -> Response:
    service.delete_provider(id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/providers/{id}/remote-models",
    response_model=list[LLMRemoteDiscoveredModel],
    summary="Discover available models from provider API",
)
def discover_provider_models(
    id: int,
    service: Annotated[LLMService, Depends(get_llm_service)],
) -> list[LLMRemoteDiscoveredModel]:
    return service.fetch_remote_models(id)


# --- Models ---


@router.get(
    "/models",
    response_model=list[LLMModelResponse],
    summary="List configured LLM models",
)
def list_llm_models(
    service: Annotated[LLMService, Depends(get_llm_service)],
    provider_id: int | None = None,
    only_enabled: bool = False,
) -> list[LLMModelResponse]:
    models = service.list_models(provider_id=provider_id, only_enabled=only_enabled)
    return [LLMModelResponse.model_validate(m) for m in models]


@router.post(
    "/models",
    response_model=LLMModelResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new LLM model directly with provider_id in body",
)
def create_llm_model_direct(
    request: LLMModelCreate,
    service: Annotated[LLMService, Depends(get_llm_service)],
) -> LLMModelResponse:
    from app.core.errors import ApplicationError

    if request.provider_id is None:
        raise ApplicationError(
            code="missing_provider_id",
            message="provider_id is required when creating a model directly",
            status_code=400,
        )
    model = service.create_model(request.provider_id, request)
    return LLMModelResponse.model_validate(model)


@router.post(
    "/providers/{provider_id}/models",
    response_model=LLMModelResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a model under an LLM provider",
)
def create_llm_model(
    provider_id: int,
    request: LLMModelCreate,
    service: Annotated[LLMService, Depends(get_llm_service)],
) -> LLMModelResponse:
    model = service.create_model(provider_id, request)
    return LLMModelResponse.model_validate(model)


@router.patch(
    "/models/{model_id}",
    response_model=LLMModelResponse,
    summary="Update an LLM model",
)
def update_llm_model(
    model_id: int,
    request: LLMModelUpdate,
    service: Annotated[LLMService, Depends(get_llm_service)],
) -> LLMModelResponse:
    model = service.update_model(model_id, request)
    return LLMModelResponse.model_validate(model)


@router.delete(
    "/models/{model_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an LLM model",
)
def delete_llm_model(
    model_id: int,
    service: Annotated[LLMService, Depends(get_llm_service)],
) -> Response:
    service.delete_model(model_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- Usage Stats & Test ---


@router.get(
    "/usage",
    response_model=LLMUsageSummaryResponse,
    summary="Get LLM usage and token cost tracking summary",
)
def get_llm_usage(
    service: Annotated[LLMService, Depends(get_llm_service)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> LLMUsageSummaryResponse:
    summary = service.get_usage_summary(recent_limit=limit)
    return LLMUsageSummaryResponse.model_validate(summary)


@router.get(
    "/usage/summary",
    response_model=LLMUsageSummaryResponse,
    summary="Alias for /usage",
)
def get_llm_usage_summary_alias(
    service: Annotated[LLMService, Depends(get_llm_service)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> LLMUsageSummaryResponse:
    summary = service.get_usage_summary(recent_limit=limit)
    return LLMUsageSummaryResponse.model_validate(summary)


@router.post(
    "/test",
    response_model=LLMTestPromptResponse,
    summary="Test LLM execution with failover",
)
def test_llm_prompt(
    request: LLMTestPromptRequest,
    service: Annotated[LLMService, Depends(get_llm_service)],
) -> LLMTestPromptResponse:
    result = service.test_prompt(request)
    return LLMTestPromptResponse.model_validate(result)


@router.post(
    "/test-prompt",
    response_model=LLMTestPromptResponse,
    summary="Alias for /test",
)
def test_llm_prompt_alias(
    request: LLMTestPromptRequest,
    service: Annotated[LLMService, Depends(get_llm_service)],
) -> LLMTestPromptResponse:
    result = service.test_prompt(request)
    return LLMTestPromptResponse.model_validate(result)
