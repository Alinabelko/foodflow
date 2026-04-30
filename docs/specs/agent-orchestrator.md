# Спецификация - Agent и Orchestrator

## 1. Ответственность

RouterAgent - главный orchestrator. Он решает, как обработать пользовательский запрос: ответить напрямую, выполнить локальный Router tool или передать задачу специализированному агенту.

Специализированные агенты:

- MenuAgent - планирование питания и отзывы о блюдах;
- ShoppingAgent - инвентарь и список покупок;
- ValidatorAgent - только валидация планов.

## 2. State machine RouterAgent

```text
получить user message
-> собрать router system messages
-> добавить bounded chat history
-> вызвать OpenAI с router tools
-> если прямой ответ: сохранить в историю и вернуть
-> если handoff tool: вызвать specialist agent и вернуть его результат
-> если local tool: выполнить tool, отправить tool outputs модели, вернуть финальный ответ
-> если OpenAI error: вернуть ошибку без выполнения tool
```

## 3. Правила переходов

| Intent | Переход |
|---|---|
| Планирование меню, рецепты, review блюд | `handoff_to_menu_agent` |
| Shopping list, купленные продукты, обновление инвентаря | `handoff_to_shopping_agent` |
| Обновление профиля пользователя | local `update_person_info` |
| Логирование еды или покупки | local `log_history` |
| Предпочтение или оценка блюда | local `save_dish_preference` |
| Регулярное/ротационное блюдо | local `set_rotation_dish` |
| Запрос вне домена | Прямой ответ или мягкий отказ в рамках домена |

## 4. State machine MenuAgent

```text
получить chat history
-> вызвать OpenAI с menu tools
-> если tool не выбран: вернуть ответ модели
-> если add_dish_review: записать dishes.csv и вернуть результат
-> если start_planning_cycle:
   -> собрать контекст
   -> сгенерировать MultiDayMealPlan
   -> провалидировать каждый DailyMealPlan
   -> если все валидно: сохранить планы и shopping list
   -> если есть ошибки и попытки остались: перегенерировать с feedback
   -> если попытки закончились: вернуть ошибку, ничего не сохранять
```

## 5. Правила ValidatorAgent

ValidatorAgent:

- принимает `DailyMealPlan` и context string;
- вызывает OpenAI structured parse с `ValidationReport`;
- не меняет состояние;
- работает fail closed: если API/parse падает, возвращает invalid results со score `0`.

## 6. Stop conditions

| Процесс | Условие остановки |
|---|---|
| Router direct answer | Первый assistant response без tool calls |
| Router local tool flow | Финальный ответ после tool outputs |
| Handoff flow | Specialist возвращает `{content, logs}` |
| Planning cycle | Все планы валидны или попыток больше 3 |
| Validation | Один report на каждый daily plan |

## 7. Retry/fallback

- OpenAI client retry управляется env-переменными.
- Planning retry ограничен `max_retries=3`.
- Validation failure перезапускает генерацию плана, а не только validation.
- Validator API failure превращается в invalid report.
- Unknown tool возвращает no-op output.

## 8. Ограничения реализации

- Specialist agents не должны напрямую менять `RouterAgent.chat_history`.
- Имена tools должны оставаться стабильными: frontend/tests могут зависеть от поведения.
- Pydantic structured models желательно менять backward-compatible способом.
- Нельзя сохранять partial meal plans, если это отдельно не спроектировано и не задокументировано.
- Logs должны оставаться коротким execution trace.

