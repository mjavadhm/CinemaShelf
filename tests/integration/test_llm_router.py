"""Integration tests for LLM provider management, failover execution, and usage statistics."""

import json
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.database import get_db_session
from app.main import app
from app.modules.llm.models import LLMModel, LLMProvider
from app.modules.llm.service import LLMService


def test_llm_provider_and_model_crud(db_session: Session) -> None:
    app.dependency_overrides[get_db_session] = lambda: db_session
    client = TestClient(app)
    try:
        # 1. Create a Provider
        create_prov_res = client.post(
            "/api/llm/providers",
            json={
                "name": "OpenAI Compatible",
                "base_url": "https://api.openai.com/v1",
                "api_key": "sk-test-secret-key",
                "description": "Primary provider",
            },
        )
        assert create_prov_res.status_code == 201
        prov_data = create_prov_res.json()
        prov_id = prov_data["id"]
        assert prov_data["name"] == "OpenAI Compatible"
        assert prov_data["api_key_masked"] == "••••-key"

        # 2. Get and List Providers
        get_prov_res = client.get(f"/api/llm/providers/{prov_id}")
        assert get_prov_res.status_code == 200
        assert get_prov_res.json()["name"] == "OpenAI Compatible"

        list_prov_res = client.get("/api/llm/providers")
        assert list_prov_res.status_code == 200
        assert len(list_prov_res.json()) >= 1

        # 3. Create Models under the Provider
        create_model1_res = client.post(
            "/api/llm/models",
            json={
                "provider_id": prov_id,
                "model_name": "gpt-4o-mini",
                "display_name": "GPT-4o Mini",
                "input_price_per_1m": 0.15,
                "output_price_per_1m": 0.60,
                "priority": 10,
                "is_enabled": True,
            },
        )
        assert create_model1_res.status_code == 201
        m1_data = create_model1_res.json()
        m1_id = m1_data["id"]
        assert m1_data["model_name"] == "gpt-4o-mini"
        assert m1_data["priority"] == 10

        create_model2_res = client.post(
            "/api/llm/models",
            json={
                "provider_id": prov_id,
                "model_name": "gpt-4o",
                "display_name": "GPT-4o High Tier",
                "input_price_per_1m": 2.50,
                "output_price_per_1m": 10.00,
                "priority": 20,
                "is_enabled": True,
            },
        )
        assert create_model2_res.status_code == 201

        # 4. List Models
        list_models_res = client.get(f"/api/llm/models?provider_id={prov_id}")
        assert list_models_res.status_code == 200
        models_list = list_models_res.json()
        assert len(models_list) == 2
        # Verify priority sorting: priority 10 comes before priority 20
        assert models_list[0]["priority"] == 10
        assert models_list[1]["priority"] == 20

        # 5. Patch Model
        patch_model_res = client.patch(
            f"/api/llm/models/{m1_id}",
            json={"priority": 50, "display_name": "GPT-4o Mini Deprioritized"},
        )
        assert patch_model_res.status_code == 200
        assert patch_model_res.json()["priority"] == 50
        assert patch_model_res.json()["display_name"] == "GPT-4o Mini Deprioritized"

        # 6. Delete Model and Provider
        del_model_res = client.delete(f"/api/llm/models/{m1_id}")
        assert del_model_res.status_code == 204

        # Updating provider
        patch_prov_res = client.patch(
            f"/api/llm/providers/{prov_id}",
            json={"name": "OpenAI Gateway Renamed"},
        )
        assert patch_prov_res.status_code == 200
        assert patch_prov_res.json()["name"] == "OpenAI Gateway Renamed"

    finally:
        app.dependency_overrides.clear()


def test_llm_remote_discovery_and_failover_execution(db_session: Session) -> None:
    app.dependency_overrides[get_db_session] = lambda: db_session
    client = TestClient(app)
    try:
        # Create Provider and Models in DB
        prov = LLMProvider(
            name="OpenRouter Mock",
            base_url="https://openrouter.ai/api/v1",
            api_key="mock-key-1234",
        )
        db_session.add(prov)
        db_session.flush()

        m1 = LLMModel(
            provider_id=prov.id,
            model_name="failing-model-1",
            display_name="Fail Model",
            input_price_per_1m=1.0,
            output_price_per_1m=2.0,
            priority=1,
            is_enabled=True,
        )
        m2 = LLMModel(
            provider_id=prov.id,
            model_name="working-model-2",
            display_name="Success Model",
            input_price_per_1m=0.5,
            output_price_per_1m=1.5,
            priority=2,
            is_enabled=True,
        )
        db_session.add_all([m1, m2])
        db_session.commit()

        # 1. Test Remote Models Discovery with mocked response
        mock_discovery_response = MagicMock()
        mock_discovery_response.status_code = 200
        mock_discovery_response.json.return_value = {
            "data": [
                {"id": "meta-llama/llama-3-8b", "name": "Llama 3 8B"},
                {
                    "id": "anthropic/claude-3.5-sonnet",
                    "name": "Sonnet 3.5",
                    "pricing": {"prompt": "0.000003", "completion": "0.000015"},
                },
            ]
        }

        mock_http_client = MagicMock()
        mock_http_client.get.return_value = mock_discovery_response

        with patch("app.modules.llm.service.httpx.Client", return_value=mock_http_client):
            disc_res = client.get(f"/api/llm/providers/{prov.id}/remote-models")
            assert disc_res.status_code == 200
            disc_data = disc_res.json()
            assert len(disc_data) == 2
            assert any(item["id"] == "meta-llama/llama-3-8b" for item in disc_data)

        # 2. Test Failover Execution via Test Prompt
        # First call fails (500), second call succeeds (200) with JSON response
        mock_fail_resp = MagicMock()
        mock_fail_resp.status_code = 500
        mock_fail_resp.text = "Internal Server Error"

        mock_succ_resp = MagicMock()
        mock_succ_resp.status_code = 200
        mock_succ_resp.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {"greeting": "Salam CinemaShelf", "confidence": 99}
                        )
                    }
                }
            ],
            "usage": {
                "prompt_tokens": 1000,
                "completion_tokens": 500,
            },
        }

        mock_http_client2 = MagicMock()
        mock_http_client2.post.side_effect = [mock_fail_resp, mock_succ_resp]

        with patch("app.modules.llm.service.httpx.Client", return_value=mock_http_client2):
            test_prompt_res = client.post(
                "/api/llm/test-prompt",
                json={
                    "agent_type": "TEST_AGENT",
                    "system_prompt": "You are a test assistant.",
                    "user_prompt": "Test greeting.",
                },
            )
            assert test_prompt_res.status_code == 200
            test_data = test_prompt_res.json()
            assert test_data["success"] is True
            assert test_data["model_name"] == "working-model-2"
            assert test_data["provider_name"] == "OpenRouter Mock"
            assert test_data["prompt_tokens"] == 1000
            assert test_data["completion_tokens"] == 500
            # Cost: (1000/1M * 0.5) + (500/1M * 1.5) = 0.0005 + 0.00075 = 0.00125
            assert test_data["cost_usd"] == 0.00125
            parsed = json.loads(test_data["response_content"])
            assert parsed["greeting"] == "Salam CinemaShelf"

        # 3. Test Usage Summary Endpoint
        summary_res = client.get("/api/llm/usage/summary")
        assert summary_res.status_code == 200
        summary_data = summary_res.json()
        assert summary_data["total_calls"] >= 2  # 1 failure + 1 success
        assert summary_data["successful_calls"] >= 1
        assert (summary_data["total_prompt_tokens"] + summary_data["total_completion_tokens"]) >= 1500
        assert summary_data["total_cost_usd"] >= 0.00125
        assert len(summary_data["recent_logs"]) >= 1

    finally:
        app.dependency_overrides.clear()


def test_specialized_llm_agents(db_session: Session) -> None:
    """Verify movie verifier and quality selector logic with mock responses."""
    prov = LLMProvider(
        name="Mock Provider",
        base_url="https://api.mock.com/v1",
        api_key="mock-key",
    )
    db_session.add(prov)
    db_session.flush()

    model = LLMModel(
        provider_id=prov.id,
        model_name="smart-model",
        display_name="Smart Model",
        is_enabled=True,
    )
    db_session.add(model)
    db_session.commit()

    # Agent 1: verify_or_select_movie
    mock_resp_agent1 = MagicMock()
    mock_resp_agent1.status_code = 200
    mock_resp_agent1.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "selected_index": 1,
                            "confidence": 95,
                            "reason_fa": "تطابق کامل سال و عنوان با نسخه اصلی",
                        }
                    )
                }
            }
        ],
        "usage": {"prompt_tokens": 100, "completion_tokens": 50},
    }

    mock_client1 = MagicMock()
    mock_client1.post.return_value = mock_resp_agent1
    service = LLMService(db_session, http_client=mock_client1)

    idx, reason = service.verify_or_select_movie(
        target_title="Inception",
        target_year=2010,
        search_cards=[
            {"title": "Inception 2", "year": "2020"},
            {"title": "Inception", "year": "2010"},
        ],
    )
    assert idx == 1
    assert "تطابق کامل" in (reason or "")

    # Agent 2: select_best_quality
    mock_resp_agent2 = MagicMock()
    mock_resp_agent2.status_code = 200
    mock_resp_agent2.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "selected_index": 0,
                            "reason_fa": "کیفیت ۱۰۸۰ سافت‌ساب مطابق با درخواست کاربر",
                        }
                    )
                }
            }
        ],
        "usage": {"prompt_tokens": 120, "completion_tokens": 60},
    }

    mock_client2 = MagicMock()
    mock_client2.post.return_value = mock_resp_agent2
    service2 = LLMService(db_session, http_client=mock_client2)

    idx2, reason2 = service2.select_best_quality(
        target_title="Inception",
        target_year=2010,
        dl_options=[
            {
                "section_type": "SoftSub",
                "quality_label": "1080p x265",
                "size_text": "2.1 GB",
            },
            {
                "section_type": "Dubbed",
                "quality_label": "720p",
                "size_text": "900 MB",
            },
        ],
        user_preference_prompt="1080p softsub",
    )
    assert idx2 == 0
    assert "۱۰۸۰ سافت‌ساب" in (reason2 or "")
