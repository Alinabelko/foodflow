"""
SC-05: Управление блюдами ротации

Пользователь: "Добавь овсянку как регулярный завтрак"
Агент должен:
  - записать блюдо в dishes.csv
  - установить флаг is_rotation=True

NOTE: Поле is_rotation ОТСУТСТВУЕТ в текущей схеме dishes.csv.
Все тесты в этом файле помечены xfail — они документируют
требование SC-05 и будут зелёными после реализации gap #2
из gap_analysis.md.

Тесты на базовое добавление блюда (без ротации) не помечены xfail
и должны проходить уже сейчас.
"""
import pytest
from helpers import seed_fridge

pytestmark = pytest.mark.e2e


class TestSC05RotationDishes:

    def test_dish_added_to_dishes_csv(self, agent, isolated_dm):
        """
        Базовый кейс: добавление блюда в dishes.csv без требований к флагу ротации.
        Этот тест должен проходить уже сейчас.
        """
        agent.process_message("Запомни, что мне нравится овсянка на завтрак, оцени на 8/10")

        dishes = isolated_dm.read_table("dishes.csv")
        dish_names = [d.get("name", "").lower() for d in dishes]

        assert any("овсян" in name or "oatmeal" in name for name in dish_names), (
            f"Овсянка не найдена в dishes.csv. Содержимое: {dishes}"
        )

    @pytest.mark.xfail(
        reason="Gap SC-05: поле is_rotation отсутствует в схеме dishes.csv (DataManager). "
               "Требует добавления поля и логики в router_agent.py и menu_prompt.md."
    )
    def test_rotation_flag_set(self, agent, isolated_dm):
        """
        Агент должен установить is_rotation=True при явном запросе.
        XFAIL: поле is_rotation не реализовано.
        """
        agent.process_message("Добавь овсянку как регулярный завтрак каждый день")

        dishes = isolated_dm.read_table("dishes.csv")
        oatmeal = [
            d for d in dishes
            if "овсян" in d.get("name", "").lower() or "oatmeal" in d.get("name", "").lower()
        ]

        assert oatmeal, f"Овсянка не найдена в dishes.csv вообще. Содержимое: {dishes}"
        assert any(
            str(d.get("is_rotation", "")).lower() in ("true", "1", "yes")
            for d in oatmeal
        ), f"Флаг is_rotation не установлен: {oatmeal}"

    @pytest.mark.xfail(
        reason="Gap SC-05: поле rotation_frequency отсутствует в схеме dishes.csv."
    )
    def test_rotation_frequency_saved(self, agent, isolated_dm):
        """
        Частота ротации должна сохраняться.
        XFAIL: поле rotation_frequency не реализовано.
        """
        agent.process_message("Куриный суп — наше воскресное блюдо")

        dishes = isolated_dm.read_table("dishes.csv")
        chicken_soup = [
            d for d in dishes
            if "курин" in d.get("name", "").lower() or "chicken" in d.get("name", "").lower()
        ]

        assert chicken_soup, f"Куриный суп не найден. Содержимое: {dishes}"
        assert any(
            "воскрес" in str(d.get("rotation_day", "")).lower() or
            "sunday" in str(d.get("rotation_day", "")).lower()
            for d in chicken_soup
        ), f"День ротации не сохранён: {chicken_soup}"

    @pytest.mark.xfail(
        reason="Gap SC-05: MenuAgent не использует ротационные блюда при планировании."
    )
    def test_rotation_dish_preferred_in_plan(self, agent, isolated_dm):
        """
        MenuAgent должен предпочитать ротационные блюда при планировании.
        XFAIL: MenuAgent не имеет логики предпочтения ротационных блюд.
        """
        from conftest import seed_pantry, tomorrow_str

        # Сначала добавляем ротационное блюдо
        agent.process_message("Добавь овсянку как регулярный завтрак")

        seed_fridge(isolated_dm, [
            {"item": "Овсянка"},
            {"item": "Молоко"},
        ])
        seed_pantry(isolated_dm, ["Сахар", "Соль"])

        agent.process_message(f"Спланируй завтраки на 3 дня начиная с {tomorrow_str()}")

        plans = isolated_dm.read_table("meal_plans.csv")
        breakfasts = [p for p in plans if p.get("meal_type") == "breakfast"]

        assert any(
            "овсян" in p.get("dish_name", "").lower() or "oatmeal" in p.get("dish_name", "").lower()
            for p in breakfasts
        ), f"Ротационная овсянка не попала ни в один завтрак. Завтраки: {breakfasts}"
