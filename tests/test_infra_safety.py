import asyncio
import os
from io import BytesIO

from fastapi import UploadFile

os.environ.setdefault("OPENAI_API_KEY", "test")


def test_translate_database_calls_agent_once(monkeypatch):
    import server

    calls = []

    class FakeAgent:
        def translate_database(self, language):
            calls.append(language)

    monkeypatch.setattr(server, "agent", FakeAgent())

    result = asyncio.run(server.translate_database(server.SettingsRequest(language="ru")))

    assert result == {"status": "success"}
    assert calls == ["ru"]


def test_upload_temp_paths_are_unique_for_same_filename():
    import server

    first = UploadFile(file=BytesIO(b"first"), filename="meal.jpg")
    second = UploadFile(file=BytesIO(b"second"), filename="meal.jpg")

    first_path = server._save_upload_to_temp(first)
    second_path = server._save_upload_to_temp(second)

    try:
        assert first_path != second_path
        assert os.path.basename(first_path).startswith("foodflow_")
        assert os.path.basename(second_path).startswith("foodflow_")
        with open(first_path, "rb") as f:
            assert f.read() == b"first"
        with open(second_path, "rb") as f:
            assert f.read() == b"second"
    finally:
        for path in (first_path, second_path):
            if os.path.exists(path):
                os.remove(path)


def test_validator_fails_closed_when_api_call_fails():
    from agents.validator_agent import ValidatorAgent
    from models import DailyMealPlan, MealCandidate

    class DummyDataManager:
        def get_settings(self):
            return {"language": "en"}

    class FailingCompletions:
        def parse(self, **kwargs):
            raise RuntimeError("api unavailable")

    class FailingClient:
        class beta:
            class chat:
                completions = FailingCompletions()

    plan = DailyMealPlan(
        date="2026-05-01",
        breakfast=MealCandidate(
            dish_name="Toast",
            reasoning="Simple",
            ingredients_needed=["bread"],
        ),
        lunch=MealCandidate(
            dish_name="Soup",
            reasoning="Warm",
            ingredients_needed=["vegetables"],
        ),
        dinner=MealCandidate(
            dish_name="Rice",
            reasoning="Uses pantry",
            ingredients_needed=["rice"],
        ),
    )

    validator = ValidatorAgent(DummyDataManager())
    validator.client = FailingClient()

    report = validator.validate_plan(plan, "context")

    assert len(report.results) == 3
    assert all(not result.is_valid for result in report.results)
    assert all(result.score == 0 for result in report.results)
    assert all(result.issues for result in report.results)


def test_telegram_agent_response_accepts_router_dict():
    import main

    assert main._agent_response_text({"response": "ok", "logs": ["trace"]}) == "ok"


def test_telegram_photo_temp_paths_are_unique():
    import main

    first_path = main._new_photo_temp_path("photo.jpg")
    second_path = main._new_photo_temp_path("photo.jpg")

    try:
        assert first_path != second_path
        assert os.path.basename(first_path).startswith("foodflow_telegram_")
        assert os.path.basename(second_path).startswith("foodflow_telegram_")
        assert first_path.endswith(".jpg")
        assert second_path.endswith(".jpg")
    finally:
        for path in (first_path, second_path):
            if os.path.exists(path):
                os.remove(path)
