# Спецификация - Tools и API

## 1. Ответственность

Tools переводят намерение пользователя, распознанное LLM, в контролируемые изменения состояния. Модель может выбрать tool и передать аргументы, но реальные изменения CSV выполняет только Python-код.

HTTP API открывает frontend доступ к чату, редактированию данных и настройкам.

## 2. Контракты tools

### Tools RouterAgent

| Tool | Обязательные аргументы | Side effects |
|---|---|---|
| `handoff_to_menu_agent` | `reason` | Нет прямых изменений; передает задачу MenuAgent |
| `handoff_to_shopping_agent` | `reason` | Нет прямых изменений; передает задачу ShoppingAgent |
| `update_person_info` | `name` | Upsert в `people.csv` |
| `log_history` | `item`, `action`, `date`, `calories`, `protein`, `fats`, `carbs` | Добавляет запись в `history.csv`; если `action=eaten`, пишет `nutrition_log.csv` и удаляет найденный продукт из инвентаря |
| `save_dish_preference` | `name` | Upsert в `dishes.csv` |
| `set_rotation_dish` | `name` | Upsert в `dishes.csv` с флагами ротационного блюда |

### Tools MenuAgent

| Tool | Обязательные аргументы | Side effects |
|---|---|---|
| `start_planning_cycle` | `dates` | После успешной валидации пишет `meal_plans.csv` и missing ingredients в `shopping_list.csv` |
| `add_dish_review` | `name` | Добавляет строку в `dishes.csv` |

### Tools ShoppingAgent

| Tool | Обязательные аргументы | Side effects |
|---|---|---|
| `update_inventory` | `updates[]` | Добавляет или удаляет строки в `fridge.csv`, `pantry.csv`, `freezer.csv` |
| `update_shopping_habit` | `habit_text` | Добавляет строку в `shopping_habits.csv` |
| `manage_shopping_list` | `action`, `items[]` | Добавляет или удаляет позиции в `shopping_list.csv` |

## 3. Контракты API

| Endpoint | Method | Input | Output |
|---|---|---|---|
| `/api/chat` | POST | multipart `message`, опционально `image` | `{response: str, logs: list[str]}` |
| `/api/data/{filename}` | GET | имя файла из schema whitelist | список записей |
| `/api/data/{filename}` | POST | список dict-записей | `{status: "success"}` |
| `/api/settings` | GET | нет | settings dict |
| `/api/settings` | POST | `{language}` | `{status: "success"}` |
| `/api/clear_chat` | POST | нет | `{status: "success"}` |
| `/api/meal_plans/approve` | POST | form `date` | `{status: "success"}` |
| `/api/translate_database` | POST | `{language}` | `{status: "success"}` |

## 4. Таймауты и retry

OpenAI client:

- timeout: `OPENAI_TIMEOUT_SECONDS`, default `30`;
- max retries: `OPENAI_MAX_RETRIES`, default `3`.

Цикл планирования меню:

- максимум попыток планирования: `3`;
- ошибка validator считается невалидным результатом, а не успешной проверкой.

HTTP endpoints сейчас выполняют синхронную agent-логику в threadpool. Долгие операции, например перевод базы или планирование, держат request открытым до завершения.

## 5. Ошибки

| Ошибка | Ожидаемое поведение |
|---|---|
| Неизвестный filename в data API | HTTP 404 |
| Ошибка OpenAI request | Вернуть ошибку пользователю, не выполнять новые tool side effects |
| Невалидный structured output | Вернуть ошибку генерации, не сохранять план |
| Ошибка ValidatorAgent | Вернуть невалидный `ValidationReport`, fail closed |
| Неизвестный tool name | Вернуть `Unknown tool`, не выполнять неподдержанное действие |
| Ошибка обработки temp image | Запрос должен завершиться ошибкой до мутации состояния |

## 6. Политика side effects

Разрешенные side effects:

- CSV CRUD через DataManager;
- создание и удаление временного файла загрузки;
- обновление in-memory chat history.

Запрещено в PoC:

- произвольная запись файлов вне `data/` и temp upload handling;
- произвольные shell/network calls из tools;
- file paths, напрямую управляемые LLM;
- оформление внешних заказов или покупок.

## 7. Production-ограничители

Перед production нужно добавить:

- auth;
- ограниченный CORS;
- rate limiting;
- подтверждение разрушительных действий;
- audit log для всех изменений состояния;
- idempotency keys для повторных tool calls;
- transactional DB или file locks/backups вместо простых CSV.
