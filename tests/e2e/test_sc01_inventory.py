"""
SC-01: Пополнение инвентаря голосом

Пользователь сообщает о купленных продуктах в свободной форме.
Агент должен:
  - распознать продукты, количество, срок годности
  - вызвать update_inventory (через ShoppingAgent)
  - результат — записи в fridge.csv
"""
import pytest
from helpers import seed_fridge, tomorrow_str

pytestmark = pytest.mark.e2e


class TestSC01Inventory:

    def test_single_item_added_to_fridge(self, agent, isolated_dm):
        """Пользователь говорит, что купил молоко — оно должно появиться в fridge."""
        result = agent.process_message("Купил молоко 1 литр")

        fridge = isolated_dm.read_table("fridge.csv")
        items = [row["item"].lower() for row in fridge]

        assert any("молок" in item or "milk" in item for item in items), (
            f"Молоко не найдено в fridge.csv после покупки. Содержимое: {items}\n"
            f"Ответ агента: {result.get('response', '')}"
        )

    def test_multiple_items_added(self, agent, isolated_dm):
        """Несколько продуктов в одном сообщении — все должны попасть в инвентарь."""
        result = agent.process_message(
            "Сегодня купил: курицу 1 кг, 10 яиц и хлеб"
        )

        fridge_items = [r["item"].lower() for r in isolated_dm.read_table("fridge.csv")]
        pantry_items = [r["item"].lower() for r in isolated_dm.read_table("pantry.csv")]
        all_items = fridge_items + pantry_items

        found_chicken = any("кури" in i or "chicken" in i for i in all_items)
        found_eggs = any("яйц" in i or "egg" in i for i in all_items)
        # хлеб может попасть в pantry или fridge — оба варианта верны
        found_bread = any("хлеб" in i or "bread" in i for i in all_items)

        assert found_chicken, f"Курица не найдена. Инвентарь: {all_items}"
        assert found_eggs, f"Яйца не найдены. Инвентарь: {all_items}"
        assert found_bread, f"Хлеб не найден. Инвентарь: {all_items}"

    def test_expiry_date_parsed(self, agent, isolated_dm):
        """Агент должен сохранить срок годности из текста."""
        expiry = "2026-04-20"
        result = agent.process_message(
            f"Купил куриное филе 500г, срок годности до {expiry}"
        )

        fridge = isolated_dm.read_table("fridge.csv")
        chicken_rows = [
            r for r in fridge
            if "кури" in r["item"].lower() or "chicken" in r["item"].lower() or "филе" in r["item"].lower()
        ]

        assert chicken_rows, (
            f"Куриное филе не найдено в fridge.csv. Содержимое: {fridge}\n"
            f"Ответ: {result.get('response', '')}"
        )
        assert any(r.get("expiry_date") == expiry for r in chicken_rows), (
            f"Срок годности {expiry} не записан. Строки: {chicken_rows}"
        )

    def test_response_confirms_action(self, agent, isolated_dm):
        """Агент должен подтвердить добавление в ответном сообщении."""
        result = agent.process_message("Купил апельсины 1 кг")
        response = result.get("response", "").lower()

        # Агент должен что-то ответить
        assert len(response) > 10, "Ответ агента слишком короткий или пустой"
        # Ответ не должен быть ошибкой
        assert "error" not in response and "ошибк" not in response, (
            f"Ответ содержит ошибку: {response}"
        )
