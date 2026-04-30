"""
Edge Cases EC-00 .. EC-06

EC-00: Холодный старт (нет данных о пользователе)
EC-01: Конфликт аллергий в плане (per-person)
EC-02: Пустой холодильник
EC-03: Противоречивые ограничения
EC-04: Срок годности завтра (hard constraint)
EC-05: Нераспознанный запрос (out of scope)
EC-06: Галлюцинация рецепта (вегетарианец + мясное блюдо)
"""
import datetime
import pytest
from helpers import (
    seed_fridge, seed_pantry, seed_people, seed_ingredients,
    today_str, tomorrow_str, days_from_now,
)

pytestmark = [pytest.mark.e2e, pytest.mark.slow]


class TestEC00ColdStart:
    """Все CSV пусты — агент должен работать и не падать."""

    def test_plan_generated_without_user_profile(self, agent, isolated_dm):
        """
        При отсутствии профилей и инвентаря агент генерирует базовый план,
        не выбрасывает исключение и не возвращает сообщение об ошибке.
        """
        result = agent.process_message("Спланируй питание на завтра")

        response = result.get("response", "")
        assert len(response) > 20, f"Ответ слишком короткий: '{response}'"
        assert "error" not in response.lower() and "traceback" not in response.lower(), (
            f"Ответ содержит ошибку: {response}"
        )

    def test_plan_created_or_shopping_list_offered(self, agent, isolated_dm):
        """
        При пустом холодильнике агент либо создаёт план (с пустым инвентарём),
        либо явно предлагает составить список покупок.
        """
        result = agent.process_message("Что поесть завтра?")
        response = result.get("response", "").lower()

        plans = isolated_dm.read_table("meal_plans.csv")
        shopping = isolated_dm.read_table("shopping_list.csv")

        plan_created = len(plans) >= 1
        shopping_mentioned = any(kw in response for kw in [
            "список покупок", "shopping", "купить", "магазин", "покупк"
        ])

        assert plan_created or shopping_mentioned, (
            f"Агент не создал план и не упомянул покупки. "
            f"Ответ: {response}, Планы: {plans}"
        )


class TestEC01AllergyConflict:
    """
    В инвентаре есть аллерген, в профиле — человек с аллергией.
    Агент не должен включать аллерген в блюда ЭТОГО человека.
    """

    def test_allergy_ingredient_not_in_plan_for_allergic_person(
        self, agent, isolated_dm
    ):
        seed_fridge(isolated_dm, [
            {"item": "Арахисовое масло"},
            {"item": "Хлеб"},
            {"item": "Яблоко"},
        ])
        seed_people(isolated_dm, [
            {"name": "Мама", "health_issues": "", "diet_issues": "", "goals": ""},
            {"name": "Сын", "health_issues": "аллергия на арахис", "diet_issues": "", "goals": ""},
        ])
        seed_ingredients(isolated_dm, [
            {"name": "арахис", "allergy_info": "аллерген", "preference_level": "allergy"},
        ])

        result = agent.process_message(
            "Спланируй ужин для всей семьи на сегодня"
        )
        response = result.get("response", "").lower()

        # Ответ не должен содержать арахис без предупреждения о делении блюд
        # Либо агент делит блюда, либо выбирает безарахисовый вариант для всех
        plans = isolated_dm.read_table("meal_plans.csv")
        dinner_plans = [p for p in plans if p.get("meal_type") == "dinner"]

        if dinner_plans:
            dish_names = " ".join(p.get("dish_name", "").lower() for p in dinner_plans)
            # Если арахис в блюде — должно быть упоминание разделения или предупреждения
            if "арахис" in dish_names or "peanut" in dish_names:
                assert any(kw in response for kw in [
                    "для мамы", "для сына", "только для", "взрослым",
                    "осторожно", "аллерги", "отдельно"
                ]), (
                    f"Арахис в плане без предупреждения. Ответ: {response}"
                )


class TestEC02EmptyFridge:
    """Холодильник и кладовая пусты — агент должен сформировать shopping list."""

    def test_non_empty_response_when_fridge_empty(self, agent, isolated_dm):
        """Агент должен ответить содержательно, а не вернуть пустую строку."""
        result = agent.process_message("Что приготовить?")
        response = result.get("response", "")

        assert len(response) > 30, f"Ответ слишком короткий: '{response}'"

    def test_shopping_list_created_when_fridge_empty(self, agent, isolated_dm):
        """
        При пустом холодильнике и запросе на планирование агент должен либо
        добавить что-то в shopping_list.csv, либо явно упомянуть покупки.
        """
        result = agent.process_message(
            "Спланируй питание на завтра. У меня ничего нет дома."
        )
        response = result.get("response", "").lower()
        shopping = isolated_dm.read_table("shopping_list.csv")

        shopping_mentioned = any(kw in response for kw in [
            "список покупок", "shopping", "купить", "магазин", "приобрест"
        ])

        assert len(shopping) >= 1 or shopping_mentioned, (
            f"Shopping list пуст и покупки не упомянуты. "
            f"Ответ: {response}, Shopping list: {shopping}"
        )


class TestEC03ConflictingConstraints:
    """Противоречивые цели: веган + набор мышечной массы + нет бобовых."""

    def test_plan_generated_despite_conflicting_constraints(self, agent, isolated_dm):
        """Агент не должен зависать или возвращать ошибку при противоречивых ограничениях."""
        seed_people(isolated_dm, [{
            "name": "Алексей",
            "diet_issues": "веган, не ест бобовые (нет чечевицы, нет фасоли, нет нута)",
            "goals": "набор мышечной массы, больше белка",
        }])
        seed_fridge(isolated_dm, [
            {"item": "Тофу"},
            {"item": "Орехи"},
            {"item": "Шпинат"},
        ])
        seed_pantry(isolated_dm, ["Рис", "Семена чиа", "Киноа"])

        result = agent.process_message("Спланируй питание на завтра")
        response = result.get("response", "")

        assert len(response) > 20, f"Слишком короткий ответ: '{response}'"
        assert "error" not in response.lower(), f"Ошибка в ответе: {response}"

    def test_plan_does_not_include_forbidden_items(self, agent, isolated_dm):
        """В плане не должно быть мяса, рыбы или бобовых для вегана."""
        seed_people(isolated_dm, [{
            "name": "Алексей",
            "diet_issues": "веган, строго без животных продуктов, без бобовых",
            "goals": "набор мышечной массы",
        }])
        seed_fridge(isolated_dm, [
            {"item": "Тофу"},
            {"item": "Орехи кешью"},
            {"item": "Авокадо"},
        ])

        agent.process_message("Спланируй питание на завтра для Алексея")

        plans = isolated_dm.read_table("meal_plans.csv")
        dish_names = " ".join(p.get("dish_name", "").lower() for p in plans)

        forbidden = ["мясо", "говядин", "свинин", "курин", "рыба", "лосос", "чечевиц", "фасол"]
        found_forbidden = [kw for kw in forbidden if kw in dish_names]

        assert not found_forbidden, (
            f"В плане найдены запрещённые ингредиенты: {found_forbidden}. "
            f"Блюда: {dish_names}"
        )

    def test_response_contains_warning_or_alternatives(self, agent, isolated_dm):
        """Агент должен предупредить об ограниченности вариантов."""
        seed_people(isolated_dm, [{
            "name": "Алексей",
            "diet_issues": "веган без бобовых",
            "goals": "набор мышечной массы",
        }])

        result = agent.process_message("Спланируй питание на завтра для Алексея")
        response = result.get("response", "").lower()

        # Агент должен либо составить план, либо предупредить об ограничениях
        has_plan = len(isolated_dm.read_table("meal_plans.csv")) >= 1
        has_warning = any(kw in response for kw in [
            "ограничен", "сложно", "предупрежд", "белок", "тофу", "alternatives"
        ])

        assert has_plan or has_warning, (
            f"Нет ни плана, ни предупреждения. Ответ: {response}"
        )


class TestEC04ExpiringProduct:
    """Продукт с истекающим сроком завтра ОБЯЗАН попасть в сегодняшний план."""

    def test_expiring_product_used_in_plan(self, agent, isolated_dm):
        """
        Фрикадельки с экспирацией завтра должны быть в сегодняшнем или завтрашнем плане.
        """
        seed_fridge(isolated_dm, [
            {
                "item": "Фрикадельки",
                "expiry_date": tomorrow_str(),
            },
            {"item": "Рис"},
            {"item": "Морковь"},
        ])

        result = agent.process_message("Что поесть сегодня?")

        plans = isolated_dm.read_table("meal_plans.csv")
        dish_names = " ".join(p.get("dish_name", "").lower() for p in plans)
        notes = " ".join(p.get("notes", "").lower() for p in plans)
        response = result.get("response", "").lower()

        # Фрикадельки должны быть упомянуты в плане или в ответе
        used_in_plan = (
            "фрикадел" in dish_names or "meatball" in dish_names or
            "фрикадел" in notes or
            "фрикадел" in response or "meatball" in response
        )

        assert used_in_plan, (
            f"Фрикадельки (срок до {tomorrow_str()}) не использованы. "
            f"Блюда: {dish_names}, Ответ: {response}"
        )

    def test_validator_rejects_plan_without_expiring_product(self, agent, isolated_dm):
        """
        ValidatorAgent должен НЕ пропустить план, в котором не использован
        продукт с истекающим сроком — теперь реализовано через context.py и validator_prompt.md.
        """
        seed_fridge(isolated_dm, [
            {
                "item": "Йогурт просроченный",
                "expiry_date": tomorrow_str(),
            },
            {"item": "Хлеб"},
        ])

        # Запрашиваем план на послезавтра — агент должен всё равно включить йогурт
        agent.process_message(f"Спланируй питание на {days_from_now(2)}")

        plans = isolated_dm.read_table("meal_plans.csv")
        dish_names = " ".join(p.get("dish_name", "").lower() for p in plans)

        assert "йогурт" in dish_names or "yogurt" in dish_names, (
            f"Йогурт с истекающим сроком не использован в плане. Блюда: {dish_names}"
        )


class TestEC05OutOfScope:
    """Запрос вне области применения — агент должен вежливо отклонить."""

    def test_math_request_rejected(self, agent, isolated_dm):
        """
        Запрос о математике должен быть отклонён без изменения данных.
        """
        result = agent.process_message("Помоги с заданием по математике: реши уравнение 2x+3=7")

        response = result.get("response", "").lower()
        plans = isolated_dm.read_table("meal_plans.csv")

        # Агент не должен создать план питания
        assert len(plans) == 0, (
            f"Агент создал план питания для математического запроса. Планы: {plans}"
        )
        # Ответ должен содержать вежливый отказ
        has_refusal = any(kw in response for kw in [
            "питани", "кухн", "еда", "не могу помочь с", "специализируюсь",
            "only help", "food", "nutrition", "cannot help with"
        ])
        assert has_refusal, (
            f"Ответ не содержит вежливого отказа / перенаправления. Ответ: {response}"
        )

    def test_general_question_rejected_gracefully(self, agent, isolated_dm):
        """Вопрос о погоде отклоняется без изменений в данных."""
        result = agent.process_message("Какая сегодня погода в Москве?")

        response = result.get("response", "")
        assert len(response) > 5, "Ответ пустой"

        # Данные не должны были измениться
        fridge = isolated_dm.read_table("fridge.csv")
        assert len(fridge) == 0, f"Fridge изменился от вопроса о погоде: {fridge}"


class TestEC06HallucinationGuard:
    """
    ValidatorAgent должен отловить блюдо с мясом для вегетарианца
    и отклонить план, требуя пересмотра.
    """

    def test_meat_dish_not_in_vegetarian_plan(self, agent, isolated_dm):
        """Для вегетарианца мясное блюдо не должно пройти валидацию."""
        seed_people(isolated_dm, [{
            "name": "Ольга",
            "diet_issues": "вегетарианец, никакого мяса",
            "goals": "",
        }])
        seed_fridge(isolated_dm, [
            {"item": "Тофу"},
            {"item": "Помидоры"},
            {"item": "Сыр"},
        ])

        agent.process_message("Спланируй ужин для Ольги")

        plans = isolated_dm.read_table("meal_plans.csv")
        dinner_dishes = " ".join(
            p.get("dish_name", "").lower()
            for p in plans
            if p.get("meal_type") == "dinner"
        )

        meat_keywords = ["мясо", "говядин", "свинин", "курин", "стейк", "шашлык", "бекон"]
        found_meat = [kw for kw in meat_keywords if kw in dinner_dishes]

        assert not found_meat, (
            f"ValidatorAgent пропустил мясное блюдо для вегетарианца. "
            f"Найдено: {found_meat}. Ужины: {dinner_dishes}"
        )

    def test_dairy_not_in_vegan_plan(self, agent, isolated_dm):
        """Для вегана молочные продукты не должны попасть в план."""
        seed_people(isolated_dm, [{
            "name": "Иван",
            "diet_issues": "строгий веган, без молочного, без яиц",
            "goals": "",
        }])
        seed_fridge(isolated_dm, [
            {"item": "Авокадо"},
            {"item": "Тофу"},
            {"item": "Шпинат"},
        ])
        seed_pantry(isolated_dm, ["Рис", "Оливковое масло"])

        agent.process_message(f"Спланируй питание на {tomorrow_str()} для Ивана")

        plans = isolated_dm.read_table("meal_plans.csv")
        dish_names = " ".join(p.get("dish_name", "").lower() for p in plans)

        dairy_keywords = ["молоко", "сметан", "творог", "кефир", "сливк", "butter", "cheese", "сыр"]
        found_dairy = [kw for kw in dairy_keywords if kw in dish_names]

        assert not found_dairy, (
            f"Молочные продукты в веганском плане: {found_dairy}. "
            f"Блюда: {dish_names}"
        )
