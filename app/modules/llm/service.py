"""Application service coordinating LLM multi-model failover routing, token cost tracking, and specialized agents."""

import json
import logging
import re
from collections.abc import Sequence
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.errors import ApplicationError
from app.modules.llm.models import LLMModel, LLMProvider, LLMUsageLog
from app.modules.llm.repository import LLMRepository
from app.modules.llm.schemas import (
    LLMModelCreate,
    LLMModelUpdate,
    LLMProviderCreate,
    LLMProviderUpdate,
    LLMRemoteDiscoveredModel,
    LLMTestPromptRequest,
)

logger = logging.getLogger(__name__)


def _extract_json_payload(text: str | None) -> dict[str, Any] | None:
    """Extract JSON object from markdown code blocks or plain text."""
    if not text:
        return None
    cleaned = text.strip()
    match = re.search(r"\{[\s\S]*\}", cleaned)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            pass
    try:
        return json.loads(cleaned)
    except Exception:
        return None


class LLMService:
    """Coordinates LLM API provider integrations, failover execution, and usage audit."""

    def __init__(
        self,
        session: Session,
        settings: Settings | None = None,
        http_client: httpx.Client | None = None,
    ) -> None:
        self.session = session
        self.repository = LLMRepository(session)
        self.settings = settings or get_settings()
        self._http_client = http_client

    def _get_client(self) -> httpx.Client:
        if self._http_client is not None:
            return self._http_client
        return httpx.Client(timeout=30.0, trust_env=False)

    # --- Provider CRUD ---

    def create_provider(self, request: LLMProviderCreate) -> LLMProvider:
        existing = self.repository.get_provider_by_name(request.name)
        if existing:
            raise ApplicationError(
                code="provider_exists",
                message=f"LLM Provider '{request.name}' already exists",
                status_code=409,
            )

        provider = LLMProvider(
            name=request.name,
            base_url=request.base_url.rstrip("/"),
            api_key=request.api_key,
            is_enabled=request.is_enabled,
            priority=request.priority,
        )
        self.repository.create_provider(provider)
        self.session.commit()
        return provider

    def list_providers(self) -> Sequence[LLMProvider]:
        return self.repository.list_providers()

    def get_provider(self, provider_id: int) -> LLMProvider:
        provider = self.repository.get_provider_by_id(provider_id)
        if not provider:
            raise ApplicationError(
                code="provider_not_found",
                message=f"LLM Provider {provider_id} not found",
                status_code=404,
            )
        return provider

    def update_provider(
        self, provider_id: int, request: LLMProviderUpdate
    ) -> LLMProvider:
        provider = self.get_provider(provider_id)
        if request.name is not None:
            provider.name = request.name
        if request.base_url is not None:
            provider.base_url = request.base_url.rstrip("/")
        if request.api_key is not None:
            provider.api_key = request.api_key
        if request.is_enabled is not None:
            provider.is_enabled = request.is_enabled
        if request.priority is not None:
            provider.priority = request.priority

        self.session.commit()
        return provider

    def delete_provider(self, provider_id: int) -> None:
        provider = self.get_provider(provider_id)
        self.repository.delete_provider(provider)
        self.session.commit()

    # --- Model CRUD ---

    def create_model(self, provider_id: int, request: LLMModelCreate) -> LLMModel:
        provider = self.get_provider(provider_id)
        model = LLMModel(
            provider_id=provider.id,
            model_name=request.model_name,
            display_name=request.display_name or request.model_name,
            input_price_per_1m=request.input_price_per_1m,
            output_price_per_1m=request.output_price_per_1m,
            is_enabled=request.is_enabled,
            priority=request.priority,
        )
        self.repository.create_model(model)
        self.session.commit()
        return model

    def update_model(self, model_id: int, request: LLMModelUpdate) -> LLMModel:
        model = self.repository.get_model_by_id(model_id)
        if not model:
            raise ApplicationError(
                code="model_not_found",
                message=f"LLM Model {model_id} not found",
                status_code=404,
            )
        if request.display_name is not None:
            model.display_name = request.display_name
        if request.input_price_per_1m is not None:
            model.input_price_per_1m = request.input_price_per_1m
        if request.output_price_per_1m is not None:
            model.output_price_per_1m = request.output_price_per_1m
        if request.is_enabled is not None:
            model.is_enabled = request.is_enabled
        if request.priority is not None:
            model.priority = request.priority

        self.session.commit()
        return model

    def delete_model(self, model_id: int) -> None:
        model = self.repository.get_model_by_id(model_id)
        if not model:
            raise ApplicationError(
                code="model_not_found",
                message=f"LLM Model {model_id} not found",
                status_code=404,
            )
        self.repository.delete_model(model)
        self.session.commit()

    def list_models(
        self,
        provider_id: int | None = None,
        only_enabled: bool = False,
    ) -> Sequence[LLMModel]:
        return self.repository.list_models(provider_id=provider_id, only_enabled=only_enabled)

    # --- Remote Model Discovery ---

    def fetch_remote_models(
        self, provider_id: int
    ) -> list[LLMRemoteDiscoveredModel]:
        """Fetch model list from {base_url}/models endpoint."""
        provider = self.get_provider(provider_id)
        endpoint = f"{provider.base_url}/models"
        headers = {"Accept": "application/json"}
        if provider.api_key:
            headers["Authorization"] = f"Bearer {provider.api_key}"

        client = self._get_client()
        should_close = self._http_client is None
        try:
            resp = client.get(endpoint, headers=headers, timeout=15.0)
            if resp.status_code != 200:
                raise ApplicationError(
                    code="remote_models_failed",
                    message=f"Provider endpoint {endpoint} returned status {resp.status_code}: {resp.text[:200]}",
                    status_code=502,
                )
            payload = resp.json()
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to fetch models from %s: %s", endpoint, exc)
            raise ApplicationError(
                code="remote_models_failed",
                message=f"Could not connect to provider models endpoint: {exc}",
                status_code=502,
            ) from exc
        finally:
            if should_close:
                client.close()

        raw_list: list[Any] = []
        if isinstance(payload, dict):
            raw_list = payload.get("data") or payload.get("models") or []
        elif isinstance(payload, list):
            raw_list = payload

        discovered: list[LLMRemoteDiscoveredModel] = []
        for item in raw_list:
            if isinstance(item, str):
                discovered.append(
                    LLMRemoteDiscoveredModel(id=item, name=item, in_price_1m=0.0, out_price_1m=0.0)
                )
                continue
            if not isinstance(item, dict):
                continue

            m_id = item.get("id") or item.get("name") or item.get("model")
            if not m_id:
                continue

            in_p = 0.0
            out_p = 0.0
            pricing = item.get("pricing")
            if isinstance(pricing, dict):
                try:
                    p_in = float(pricing.get("prompt") or pricing.get("input") or 0.0)
                    p_out = float(pricing.get("completion") or pricing.get("output") or 0.0)
                    in_p = round(p_in * 1_000_000, 4) if 0 < p_in < 0.01 else round(p_in, 4)
                    out_p = round(p_out * 1_000_000, 4) if 0 < p_out < 0.01 else round(p_out, 4)
                except Exception:
                    pass

            discovered.append(
                LLMRemoteDiscoveredModel(
                    id=str(m_id),
                    name=str(item.get("name") or m_id),
                    in_price_1m=in_p,
                    out_price_1m=out_p,
                )
            )

        discovered.sort(key=lambda x: x.id)
        return discovered

    # --- Multi-Model Failover Execution ---

    def call_with_failover(
        self,
        agent_type: str,
        system_prompt: str,
        user_prompt: str,
        preferred_model_id: int | None = None,
    ) -> tuple[dict[str, Any] | None, str | None]:
        """Iterate through active models in priority order until one succeeds with JSON output."""
        active_models = list(self.repository.list_all_active_models())
        if not active_models:
            logger.info("No active LLM models configured; fallback to deterministic logic.")
            return None, "No active models available"

        # If a preferred model is requested, prioritize it
        if preferred_model_id:
            primary = [m for m in active_models if m.id == preferred_model_id]
            others = [m for m in active_models if m.id != preferred_model_id]
            active_models = primary + others

        client = self._get_client()
        should_close = self._http_client is None

        try:
            for model in active_models:
                provider = model.provider
                endpoint = f"{provider.base_url}/chat/completions"
                headers = {"Content-Type": "application/json"}
                if provider.api_key:
                    headers["Authorization"] = f"Bearer {provider.api_key}"

                payload = {
                    "model": model.model_name,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0.1,
                }

                try:
                    logger.info(
                        "Dispatching [%s] to %s (%s)...",
                        agent_type,
                        provider.name,
                        model.model_name,
                    )
                    resp = client.post(endpoint, headers=headers, json=payload, timeout=25.0)
                    if resp.status_code != 200:
                        err_text = resp.text[:200]
                        logger.warning(
                            "Provider %s (%s) returned %d: %s. Trying next model...",
                            provider.name,
                            model.model_name,
                            resp.status_code,
                            err_text,
                        )
                        self._log_usage(
                            agent_type=agent_type,
                            provider_name=provider.name,
                            model_name=model.model_name,
                            prompt_tokens=0,
                            completion_tokens=0,
                            cost_usd=0.0,
                            success=False,
                            error_message=f"HTTP {resp.status_code}: {err_text}",
                        )
                        continue

                    data = resp.json()
                    choices = data.get("choices", [])
                    if not choices:
                        continue

                    content = choices[0].get("message", {}).get("content", "")
                    usage = data.get("usage", {})
                    p_tokens = int(usage.get("prompt_tokens") or 0)
                    c_tokens = int(usage.get("completion_tokens") or 0)

                    if p_tokens == 0 and c_tokens == 0:
                        p_tokens = max(1, (len(system_prompt) + len(user_prompt)) // 4)
                        c_tokens = max(1, len(content) // 4)

                    cost_usd = (p_tokens / 1_000_000.0) * model.input_price_per_1m + (
                        c_tokens / 1_000_000.0
                    ) * model.output_price_per_1m

                    parsed = _extract_json_payload(content)
                    if parsed is not None:
                        parsed["_meta_model"] = f"{provider.name}/{model.model_name}"
                        parsed["_meta_cost"] = round(cost_usd, 6)
                        parsed["_meta_tokens"] = p_tokens + c_tokens
                        parsed["_meta_prompt_tokens"] = p_tokens
                        parsed["_meta_completion_tokens"] = c_tokens
                        self._log_usage(
                            agent_type=agent_type,
                            provider_name=provider.name,
                            model_name=model.model_name,
                            prompt_tokens=p_tokens,
                            completion_tokens=c_tokens,
                            cost_usd=cost_usd,
                            success=True,
                        )
                        return parsed, None
                    else:
                        logger.warning(
                            "Model %s output did not contain valid JSON. Trying next model...",
                            model.model_name,
                        )
                        self._log_usage(
                            agent_type=agent_type,
                            provider_name=provider.name,
                            model_name=model.model_name,
                            prompt_tokens=p_tokens,
                            completion_tokens=c_tokens,
                            cost_usd=cost_usd,
                            success=False,
                            error_message="Invalid JSON response",
                        )
                except Exception as exc:  # noqa: BLE001
                    logger.warning(
                        "Error contacting %s (%s): %s. Switching to fallback...",
                        provider.name,
                        model.model_name,
                        exc,
                    )
                    self._log_usage(
                        agent_type=agent_type,
                        provider_name=provider.name,
                        model_name=model.model_name,
                        prompt_tokens=0,
                        completion_tokens=0,
                        cost_usd=0.0,
                        success=False,
                        error_message=str(exc),
                    )
        finally:
            if should_close:
                client.close()

        return None, "All candidate LLM models failed"

    def _log_usage(
        self,
        agent_type: str,
        provider_name: str,
        model_name: str,
        prompt_tokens: int,
        completion_tokens: int,
        cost_usd: float,
        success: bool,
        error_message: str | None = None,
    ) -> None:
        try:
            log = LLMUsageLog(
                agent_type=agent_type,
                provider_name=provider_name,
                model_name=model_name,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                cost_usd=cost_usd,
                success=success,
                error_message=error_message,
            )
            self.repository.add_usage_log(log)
            self.session.commit()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not persist LLM usage log: %s", exc)

    # --- Specialized Agents ---

    def verify_or_select_movie(
        self,
        target_title: str,
        target_year: str | int | None,
        search_cards: list[dict[str, Any]],
    ) -> tuple[int | None, str | None]:
        """Agent 1: Matches Zarfilm search cards against target movie title and year."""
        if not search_cards:
            return None, None

        system_prompt = (
            "You are an expert film archivist and entity-resolution agent. "
            "The user wants to find a specific movie on a Persian movie streaming site (Zarfilm). "
            "You will be given the target movie Title and Release Year, along with a JSON list of search result cards found on Zarfilm "
            "(including title, year, IMDb score, genres, and Persian plot summary). "
            "Note that release years sometimes differ by ±1 year (festival vs wide release) or titles may be alternate English/original titles. "
            "Carefully verify the plot, year, and title. "
            "Return ONLY a valid JSON object with keys: "
            '{"selected_index": <int or null if none match>, "confidence": <0-100>, "reason_fa": "<brief Persian explanation>"}'
        )

        user_prompt = json.dumps(
            {
                "target_movie": {"title": target_title, "year": str(target_year or "")},
                "zarfilm_search_results": search_cards,
            },
            ensure_ascii=False,
            indent=2,
        )

        res, err = self.call_with_failover("SEARCH_MATCH", system_prompt, user_prompt)
        if not res:
            return None, err

        idx = res.get("selected_index")
        reason = res.get("reason_fa") or ""
        model_used = res.get("_meta_model", "LLM")

        if idx is None or not isinstance(idx, int) or idx < 0 or idx >= len(search_cards):
            return -1, f"[{model_used}] {reason}"

        return idx, f"[{model_used}] {reason}"

    def select_best_quality(
        self,
        target_title: str,
        target_year: str | int | None,
        dl_options: list[dict[str, Any]],
        user_preference_prompt: str = "",
    ) -> tuple[int | None, str | None]:
        """Agent 2: Evaluates download links against user's natural language criteria."""
        if not dl_options:
            return None, None

        pref = user_preference_prompt.strip() or "1080p SoftSub x265 or high quality"
        system_prompt = (
            "You are an intelligent video release selector agent. "
            "You will receive a list of available download links for a movie from Zarfilm (including section type like SoftSub vs Dubbed, quality label, file size, encoder, and extra notes), "
            "along with the user's natural language quality preference. "
            "Select the single best download option index that satisfies the user's criteria. "
            "Return ONLY a valid JSON object with keys: "
            '{"selected_index": <int or null>, "reason_fa": "<brief Persian explanation of why this release was chosen>"}'
        )

        clean_options = [
            {
                "index": i,
                "type": opt.get("section_type", ""),
                "quality": opt.get("q_text") or opt.get("quality_label", ""),
                "size": opt.get("size_text", ""),
                "encoder": opt.get("encoder_text") or opt.get("encoder", ""),
                "note": opt.get("desc_text", ""),
                "filename": str(opt.get("href", "")).split("/")[-1].split("?")[0],
            }
            for i, opt in enumerate(dl_options)
        ]

        user_prompt = json.dumps(
            {
                "movie": f"{target_title} ({target_year or ''})",
                "user_quality_preference": pref,
                "available_releases": clean_options,
            },
            ensure_ascii=False,
            indent=2,
        )

        res, err = self.call_with_failover("QUALITY_SELECT", system_prompt, user_prompt)
        if not res:
            return None, err

        idx = res.get("selected_index")
        reason = res.get("reason_fa") or ""
        model_used = res.get("_meta_model", "LLM")

        if isinstance(idx, int) and 0 <= idx < len(dl_options):
            return idx, f"[{model_used}] {reason}"

        return None, None

    # --- Stats & Test ---

    def get_usage_summary(self, recent_limit: int = 20) -> dict[str, Any]:
        summary = self.repository.get_usage_summary()
        recent_logs = self.repository.list_usage_logs(limit=recent_limit)
        summary["recent_logs"] = recent_logs
        return summary

    def test_prompt(self, request: LLMTestPromptRequest) -> dict[str, Any]:
        """Test prompt on a configured model or through failover."""
        res, err = self.call_with_failover(
            agent_type="TEST",
            system_prompt=request.system_prompt,
            user_prompt=request.user_prompt,
            preferred_model_id=request.model_id,
        )
        if res:
            meta = res.get("_meta_model", "")
            prov_name = meta.split("/")[0] if "/" in meta else "Provider"
            mod_name = meta.split("/", 1)[1] if "/" in meta else meta
            return {
                "success": True,
                "provider_name": prov_name,
                "model_name": mod_name,
                "response_content": json.dumps(res, ensure_ascii=False),
                "prompt_tokens": res.get("_meta_prompt_tokens", res.get("_meta_tokens", 0)),
                "completion_tokens": res.get("_meta_completion_tokens", 0),
                "cost_usd": res.get("_meta_cost", 0.0),
                "error_message": None,
            }
        return {
            "success": False,
            "provider_name": "N/A",
            "model_name": "N/A",
            "response_content": None,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "cost_usd": 0.0,
            "error_message": err or "Failed to get response from any candidate model",
        }
