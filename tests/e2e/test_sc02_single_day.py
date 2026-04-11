"""
SC-02: Планирование меню на один день

Пользователь: "Что поесть завтра?"
Агент должен:
  - передать запрос в MenuAgent
  - запустить цикл Plan→Validate→Refine
  - сохранить 3 приёма пищи в meal_plans.csv
  - автоматически добавить недостающее в shopping_list.csv
"""
import datetime
import pytest
from helpers import seed_fridge, seed_people, seed_pantry, tomorrow_str

pytestmark = [pytest.mark.e2e, pytest.mark.slow]


TOMORROW = tomorrow_str()


class TestSC02SingleDayPlan:

    def test_plan_saved_to_csv(self, agent, isolated_dm):
        """После запроса в meal_plans.csv должны быть записи завтрашнего дня."""
        seed_fridge(isolated_dm, [
            {"item": "Куриное филе", "expiry_date": (
                datetime.date.today() + datetime.timedelta(days=5)).isoformat()},
            {"item": "Гречка"},
            {"item": "Яйца"},
        ])
        seed_pantry(isolated_dm, ["Масло растительное", "Соль", "Специи"])

        result = agent.process_message("Что поесть завтра?")

        plans = isolated_dm.read_table("meal_plans.csv")
        tomorrow_plans = [p for p in plans if p.get("date") == TOMORROW]

        assert len(tomorrow_plans) >= 3, (
            f"Ожидалось ≥3 записей в meal_plans.csv для {TOMORROW}, "
            f"получено {len(tomorrow_plans)}.\nВсе планы: {plans}\n"
            f"Ответ: {result.get('response', '')}"
        )

    def test_all_meal_types_present(self, agent, isolated_dm):
        """Должны быть breakfast, lunch и dinner."""
        seed_fridge(isolated_dm, [
            {"item": "Овсянка"},
            {"item": "Куриный суп"},
            {"item": "Рис"},
            {"item": "Морковь"},
        ])

        agent.process_message(f"Спланируй питание на {TOMORROW}")

        plans = isolated_dm.read_table("meal_plans.csv")
        meal_types = {p["meal_type"].lower() for p in plans if p.get("date") == TOMORROW}

        assert "breakfast" in meal_types, f"Завтрак не найден. meal_types={meal_types}"
        assert "lunch" in meal_types, f"Обед не найден. meal_types={meal_types}"
        assert "dinner" in meal_types, f"Ужин не найден. meal_types={meal_types}"

    def test_missing_ingredients_go_to_shopping_list(self, agent, isolated_dm):
        """Если для плана не хватает продуктов — они должны попасть в shopping_list.csv."""
        # Намеренно пустой холодильник → всё будет missing
        result = agent.process_message(f"Спланируй питание на {TOMORROW}")

        plans = isolated_dm.read_table("meal_plans.csv")
        shopping = isolated_dm.read_table("shopping_list.csv")

        # Если план создан — проверяем что shopping list не пустой
        if plans:
            assert len(shopping) >= 1, (
                f"Shopping list пуст, хотя продукты должны были добавиться. "
                f"Ответ: {result.get('response', '')}"
            )

    def test_response_contains_dish_names(self, agent, isolated_dm):
        """Ответ агента должен содержать названия блюд."""
        seed_fridge(isolated_dm, [
            {"item": "Яйца"},
            {"item": "Хлеб"},
            {"item": "Картофель"},
        ])

        result = agent.process_message("Что поесть завтра?")
        response = result.get("response", "")

        # Ответ должен быть содержательным (не пустым и не ошибкой)
        assert len(response) > 30, f"Ответ слишком короткий: '{response}'"
        assert "error" not in response.lower(), f"Ответ содержит ошибку: {response}"

    def test_plan_respects_dietary_restriction(self, agent, isolated_dm):
        """Агент не должен планировать мясо для вегетарианца."""
        seed_people(isolated_dm, [{
            "name": "Анна",
            "diet_issues": "вегетарианец, не ест мясо и рыбу",
            "goals": ""
        }])
        seed_fridge(isolated_dm, [
            {"item": "Тофу"},
            {"item": "Овощи"},
            {"item": "Гречка"},
        ])

        agent.process_message(f"Спланируй питание на {TOMORROW}")

        plans = isolated_dm.read_table("meal_plans.csv")
        dish_names = " ".join(p.get("dish_name", "").lower() for p in plans)

        # Грубая проверка: явные мясные блюда не должны фигурировать
        meat_keywords = ["стейк", "мясо", "свинин", "говядин", "пельмен"]
        found_meat = [kw for kw in meat_keywords if kw in dish_names]
        assert not found_meat, (
            f"В плане найдены мясные блюда для вегетарианца: {found_meat}. "
            f"Блюда: {dish_names}"
        )
