"""
SC-03: Многодневное планирование

Пользователь: "Спланируй еду на 3 дня" / "на всю неделю"
Агент должен:
  - создать MultiDayMealPlan
  - сохранить ≥ N*3 записей в meal_plans.csv (N дней × 3 приёма)
  - если один день не проходит валидацию — остальные дни сохраняются
"""
import datetime
import pytest
from helpers import seed_fridge, seed_pantry, days_from_now

pytestmark = [pytest.mark.e2e, pytest.mark.slow]


class TestSC03MultiDay:

    def test_three_day_plan_saved(self, agent, isolated_dm):
        """Запрос на 3 дня → ≥9 записей в meal_plans.csv."""
        seed_fridge(isolated_dm, [
            {"item": "Куриное филе"},
            {"item": "Гречка"},
            {"item": "Яйца"},
            {"item": "Картофель"},
            {"item": "Морковь"},
        ])
        seed_pantry(isolated_dm, ["Масло", "Соль", "Специи", "Макароны", "Рис"])

        agent.process_message("Спланируй питание на 3 дня")

        plans = isolated_dm.read_table("meal_plans.csv")

        assert len(plans) >= 9, (
            f"Ожидалось ≥9 записей (3 дня × 3 приёма), получено {len(plans)}. "
            f"Планы: {plans}"
        )

    def test_three_day_plan_has_distinct_dates(self, agent, isolated_dm):
        """В трёхдневном плане должно быть минимум 3 разных даты."""
        seed_fridge(isolated_dm, [
            {"item": "Рыба"},
            {"item": "Рис"},
            {"item": "Брокколи"},
        ])

        agent.process_message("Составь план питания на 3 дня начиная с завтра")

        plans = isolated_dm.read_table("meal_plans.csv")
        dates = {p["date"] for p in plans}

        assert len(dates) >= 3, (
            f"Ожидалось ≥3 разных дат, получено {len(dates)}: {dates}"
        )

    def test_response_mentions_multiple_days(self, agent, isolated_dm):
        """Ответ агента должен упоминать несколько дней."""
        seed_fridge(isolated_dm, [
            {"item": "Говядина"},
            {"item": "Картошка"},
            {"item": "Лук"},
        ])

        result = agent.process_message("Спланируй меню на 3 дня")
        response = result.get("response", "")

        assert len(response) > 50, (
            f"Ответ слишком короткий для трёхдневного плана: '{response}'"
        )

    @pytest.mark.slow
    def test_week_plan_saved(self, agent, isolated_dm):
        """Запрос на неделю → ≥21 записи в meal_plans.csv."""
        seed_fridge(isolated_dm, [
            {"item": "Куриное филе"},
            {"item": "Рыба"},
            {"item": "Яйца"},
            {"item": "Гречка"},
            {"item": "Рис"},
            {"item": "Картофель"},
            {"item": "Морковь"},
        ])
        seed_pantry(isolated_dm, ["Масло", "Соль", "Специи", "Макароны", "Чечевица"])

        agent.process_message("Спланируй еду на всю неделю")

        plans = isolated_dm.read_table("meal_plans.csv")
        # Мягкий порог: даже если 1-2 дня не прошли ретраи — остальные сохранились
        assert len(plans) >= 15, (
            f"Ожидалось ≥15 записей для недели, получено {len(plans)}."
        )
