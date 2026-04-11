"""
SC-04: Учёт приёма пищи

Пользователь: "Пообедал гречкой с куриным филе"
Агент должен:
  - вызвать log_history (action='eaten', дата=сегодня)
  - записать приблизительное КБЖУ через LLM
  - результат — запись в history.csv

NOTE (Gap из анализа): Текущая реализация НЕ убирает ингредиенты из
fridge.csv после еды. Тест test_inventory_decremented помечен xfail
до исправления этого gap'а (SC-04 в gap_analysis.md).
"""
import datetime
import pytest
from helpers import seed_fridge, today_str

pytestmark = pytest.mark.e2e

TODAY = today_str()


class TestSC04MealLogging:

    def test_eaten_logged_to_history(self, agent, isolated_dm):
        """История должна содержать запись о съеденном с action='eaten'."""
        seed_fridge(isolated_dm, [
            {"item": "Гречка"},
            {"item": "Куриное филе"},
        ])

        agent.process_message("Пообедал гречкой с куриным филе")

        history = isolated_dm.read_table("history.csv")
        eaten = [h for h in history if h.get("action") == "eaten"]

        assert len(eaten) >= 1, (
            f"Ожидалась хотя бы одна запись action='eaten' в history.csv. "
            f"Вся история: {history}"
        )

    def test_eaten_record_has_today_date(self, agent, isolated_dm):
        """Дата записи должна быть сегодняшней."""
        agent.process_message("Съел яичницу на завтрак")

        history = isolated_dm.read_table("history.csv")
        today_eaten = [
            h for h in history
            if h.get("action") == "eaten" and h.get("date", "").startswith(TODAY)
        ]

        assert len(today_eaten) >= 1, (
            f"Запись за сегодня ({TODAY}) не найдена. История: {history}"
        )

    def test_nutrition_fields_populated(self, agent, isolated_dm):
        """Поля КБЖУ (calories, protein) должны быть заполнены (LLM оценка)."""
        agent.process_message("Поужинал тарелкой борща со сметаной")

        history = isolated_dm.read_table("history.csv")
        eaten = [h for h in history if h.get("action") == "eaten"]

        if eaten:
            # Хотя бы у одной записи должны быть числовые КБЖУ
            has_nutrition = any(
                str(h.get("calories", "")).strip() not in ("", "0", "nan")
                for h in eaten
            )
            assert has_nutrition, (
                f"КБЖУ не заполнены ни в одной записи. Записи: {eaten}"
            )

    def test_bought_action_also_works(self, agent, isolated_dm):
        """log_history поддерживает action='bought' — покупка тоже логируется."""
        agent.process_message("Сегодня купил хлеб и молоко")

        history = isolated_dm.read_table("history.csv")
        bought = [h for h in history if h.get("action") == "bought"]
        # Покупка может также попасть через update_inventory (не history) —
        # принимаем оба варианта
        fridge = isolated_dm.read_table("fridge.csv")
        pantry = isolated_dm.read_table("pantry.csv")

        all_items = (
            [h["item"].lower() for h in bought] +
            [r["item"].lower() for r in fridge] +
            [r["item"].lower() for r in pantry]
        )

        found_bread = any("хлеб" in i or "bread" in i for i in all_items)
        found_milk = any("молок" in i or "milk" in i for i in all_items)

        assert found_bread or found_milk, (
            f"Ни хлеб, ни молоко не зафиксированы. "
            f"History bought: {bought}, Fridge: {fridge}, Pantry: {pantry}"
        )

    @pytest.mark.xfail(
        reason="Gap SC-04: текущая реализация не убирает ингредиенты из "
               "fridge.csv при log_history. Требует доработки router_agent.py."
    )
    def test_inventory_decremented_after_eating(self, agent, isolated_dm):
        """
        После того как съел гречку, её не должно быть в fridge.csv.
        XFAIL — этот gap зафиксирован в gap_analysis.md (пункт #1).
        """
        seed_fridge(isolated_dm, [{"item": "Гречка"}])

        agent.process_message("Только что съел тарелку гречки")

        fridge = isolated_dm.read_table("fridge.csv")
        items = [r["item"].lower() for r in fridge]

        assert not any("греч" in i or "buckwheat" in i for i in items), (
            f"Гречка всё ещё в fridge.csv после употребления: {items}"
        )
