# System Design - FoodFlow PoC

## 1. Назначение документа

Документ фиксирует архитектуру PoC-системы FoodFlow перед дальнейшей разработкой. Он описывает состав модулей, взаимодействие, execution flow, контракты, state/memory/context handling, retrieval-контур, интеграции, ограничения, failure modes и guardrails.

Цель этапа - иметь достаточную архитектурную базу для реализации и доработки без существенных пробелов в границах модулей и ответственности.

## 2. Ключевые архитектурные решения

| Решение | Обоснование | Последствия |
|---|---|---|
| Agentic backend с RouterAgent как orchestrator | Пользователь общается на естественном языке, система должна выбирать сценарий: меню, покупки, память, история | Центральная точка маршрутизации и хранения chat history |
| Специализированные агенты для разных задач | Планирование меню, покупки и валидация имеют разные правила и tools | Более специализированные промпты, проще тестирование |
| Plan -> Validate -> Refine для meal planning | План питания затрагивает ограничения по здоровью, аллергиям и срокам годности | План сохраняется только после успешной валидации;|
| CSV для хранения данных в PoC | Простые локальные файлы, которые легко смотреть и редактировать | Позволяет поддерживать четкую структуру данных, но плохо масштабируется и не защищает от одновременных записей, предпочтителен переход на БД |
| Structured outputs для планов и validation reports | Типизированные контракты между LLM и кодом | Ошибки парсинга становятся failure mode и обрабатываются явно |

## 3. Границы системы

FoodFlow PoC состоит из web-интерфейса, HTTP backend, agent layer, контекстного retrieval-слоя, tool layer и локального CSV-хранилища.

Внешние сервисы:

- OpenAI API - inference, tool/function calling, structured outputs, vision input.
- Streamlit UI - пользовательский интерфейс.
- Локальная файловая система - persistence в `data/`.

За пределами PoC:

- production auth;
- multi-user tenancy;
- централизованный secrets manager;
- transactional database;
- полноценный vector search;
- платежные/магазинные API;
- медицинская верификация рекомендаций.

## 4. Модули и роли

| Модуль | Файл/слой | Роль |
|---|---|---|
| React frontend | `frontend/src/*` | Chat UI, dashboard/data editor, settings, вызовы FastAPI |
| Streamlit web app | `src/web_app.py` | Альтернативный локальный UI с chat и редактором CSV |
| FastAPI server | `src/server.py` | HTTP API, upload images, clear chat, settings, data CRUD |
| RouterAgent | `src/agents/router_agent.py` | Orchestrator: intent routing, local tools, chat history |
| MenuAgent | `src/agents/menu_agent.py` | Meal planning, multi-day plan generation, save plans, auto-shopping |
| ShoppingAgent | `src/agents/shopping_agent.py` | Inventory CRUD, shopping list, shopping habits |
| ValidatorAgent | `src/agents/validator_agent.py` | LLM validation of proposed meal plans, fail-closed behavior |
| BaseAgent | `src/agents/base.py` | OpenAI client config, prompt loading, shared model defaults |
| ContextAssembler | `src/context.py` | Read-only context snapshot from CSV tables |
| DataManager | `src/data_manager.py` | CSV schemas, read/write/update/remove/save settings |
| Pydantic models | `src/models.py` | Structured contracts for plans and validation reports |
| Prompts | `src/prompts/*.md` | Agent instructions separated from code |
| Tests | `tests/*` | E2E scenarios and infra safety checks |

## 5. Основной workflow выполнения задачи

1. Пользователь отправляет сообщение через React/FastAPI или Streamlit.
2. Backend передает текст в `RouterAgent.process_message`.
3. RouterAgent:
   - загружает language setting;
   - собирает system prompt;
   - добавляет context snapshot от `ContextAssembler`;
   - добавляет user message в chat history;
   - ограничивает историю последними 50 сообщениями;
   - вызывает OpenAI model с tool schema.
4. Модель либо отвечает напрямую, либо вызывает tool:
   - handoff to MenuAgent;
   - handoff to ShoppingAgent;
   - update person info;
   - log history/nutrition;
   - save dish preference;
   - set rotation dish.
5. Если произошел handoff:
   - специализированный агент получает текущую chat history;
   - собирает свой context;
   - вызывает свою модель и tools;
   - возвращает content и logs в RouterAgent.
6. Если выполняется local tool:
   - RouterAgent вызывает deterministic code;
   - DataManager меняет CSV;
   - tool outputs возвращаются модели для финального ответа.
7. Backend возвращает `{response, logs}` во frontend.
8. UI показывает ответ; таблицы доступны через data endpoints/editor.

## 6. Workflow планирования меню

Meal planning - наиболее рискованный workflow, поэтому он построен как цикл:

1. MenuAgent получает запрос на одну или несколько дат.
2. ContextAssembler формирует snapshot:
   - expiring soon;
   - inventory;
   - household goals/restrictions;
   - allergies/dislikes;
   - rotation dishes;
   - recent history.
3. MenuAgent генерирует `MultiDayMealPlan` через structured output.
4. Для каждого `DailyMealPlan` вызывается ValidatorAgent.
5. ValidatorAgent возвращает `ValidationReport`.
6. Если все дни валидны:
   - MenuAgent сохраняет meal plans в `meal_plans.csv`;
   - missing ingredients добавляются в `shopping_list.csv`;
   - пользователь получает итоговый план.
7. Если есть ошибки:
   - issues агрегируются в feedback;
   - MenuAgent повторяет генерацию до `max_retries=3`.
8. Если после 3 попыток план невалиден:
   - план не сохраняется;
   - пользователь получает ошибку с последними issues.

## 7. State, memory и context handling

### Persistent state

Persistent state хранится локально в `data/`:

| Таблица | Назначение |
|---|---|
| `people.csv` | Профили членов семьи, ограничения, цели |
| `ingredients.csv` | Аллергии, dislikes, preferences |
| `dishes.csv` | Предпочтения, рейтинг, rotation dishes |
| `fridge.csv`, `pantry.csv`, `freezer.csv` | Инвентарь |
| `recipes.csv` | Локальные рецепты |
| `history.csv` | Что было съедено/куплено |
| `nutrition_log.csv` | Оценки calories/protein/fats/carbs |
| `meal_plans.csv` | Сохраненные планы питания |
| `shopping_list.csv` | Список покупок |
| `shopping_habits.csv` | Покупательские привычки |
| `settings.json` | Язык интерфейса/ответов |

### Session state

- RouterAgent хранит `chat_history` in-memory.
- Максимум истории: 50 сообщений.
- `clear_chat` очищает in-memory историю, но не CSV-память.
- При restart backend история чата теряется, persistent CSV остается.

### Context budget policy

Контекст собирается не как полный dump всех таблиц, а как сжатый snapshot:

- fridge сортируется по expiry date;
- продукты с истечением <= 2 дней выделяются как hard constraint;
- pantry/freezer показываются компактным списком;
- recent history ограничена последними 7 eaten entries;
- shopping list в ShoppingAgent ограничивается первыми 10 items в системном контексте.

Ограничение PoC: нет token accounting и adaptive summarization. При росте CSV таблиц понадобится лимитирование, ranking и/или vector index.

## 8. Retrieval-контур

Текущий retrieval - deterministic structured retrieval из локальных CSV, без embeddings.

Контур:

1. `DataManager.read_table` читает нужные CSV.
2. `ContextAssembler.get_context_snapshot` выбирает релевантные части состояния.
3. Snapshot добавляется как system message.
4. LLM использует snapshot для reasoning и tool calls.

Источники retrieval:

- inventory;
- household profiles;
- allergies/dislikes;
- rotation dishes;
- recent meal history;
- shopping list;
- settings.

Чего нет в PoC:

- vector index;
- reranking model;
- semantic document retrieval;
- external recipe search;
- freshness cache;
- per-source access policy.

Планируемое расширение: добавить интеграции с магазинами и источниками пищевой ценности. Магазинные API будут использоваться для проверки наличия, цен и формирования покупок, а база калорий/БЖУ - для более надежных расчетов nutrition log и планов питания.

## 9. Tool/API-интеграции

### Internal tool layer

Основные tools:

- `handoff_to_menu_agent(reason)`;
- `handoff_to_shopping_agent(reason)`;
- `update_person_info(name, health_issues, diet_issues, goals)`;
- `log_history(item, action, date, quantity, calories, protein, fats, carbs)`;
- `save_dish_preference(name, rating, comments)`;
- `set_rotation_dish(name, rotation_frequency, rotation_day)`;
- `start_planning_cycle(dates, focus)`;
- `add_dish_review(name, rating, comments)`;
- `update_inventory(updates[])`;
- `update_shopping_habit(habit_text)`;
- `manage_shopping_list(action, items[])`.

### HTTP API

FastAPI endpoints:

- `GET /api/data/{filename}`;
- `POST /api/data/{filename}`;
- `GET /api/settings`;
- `POST /api/settings`;
- `POST /api/chat`;
- `POST /api/clear_chat`;
- `POST /api/meal_plans/approve`;
- `POST /api/translate_database`.

### OpenAI API

BaseAgent создает client с:

- `OPENAI_API_KEY`;
- `OPENAI_MAX_RETRIES`, default `3`;
- `OPENAI_TIMEOUT_SECONDS`, default `30`;
- model default in code: `gpt-5-mini`.

Используются:

- chat completions;
- tool/function calling;
- structured parse for Pydantic response formats;
- image input via base64 data URL.

## 10. Failure modes, fallback и guardrails

| Failure mode | Обработка сейчас | Guardrail/fallback |
|---|---|---|
| OpenAI API недоступен в RouterAgent | Возврат `Error connecting to Router AI` | User-visible error, no state mutation |
| OpenAI API недоступен в ShoppingAgent | Возврат `Error in ShoppingAgent` | No tool side effect if response not received |
| Structured plan generation failed | Возврат ошибки генерации | No plan saved |
| Validator API failed | Validator returns invalid report for all meals | Fail closed; plan rejected |
| Plan violates restrictions | Retry with validation issues as feedback | Max 3 attempts |
| Tool call has unsupported function | Output `Unknown tool` | Side effect blocked |
| Unknown CSV filename via API | HTTP 404 | Schema whitelist in DataManager |
| Image upload filename unsafe/odd suffix | Temp file with sanitized suffix | Unique temp file, cleanup in `finally` |
| Chat history grows too large | Truncate to last 50 messages | Prevent unbounded prompt growth |
| Empty/cold-start data | ContextAssembler emits cold-start notice | Basic plan + ask user to enrich data |
| Destructive inventory removal | Direct remove in PoC | Production needs confirmation/undo |
| CSV corruption/concurrent write | Not fully handled | Production needs DB or file locks/backups |

## 11. Technical and operational constraints

| Constraint | PoC target/current value | Notes |
|---|---|---|
| p95 text chat latency | Target < 12 sec | Simple requests should be faster; plan generation can exceed |
| p95 meal planning latency | Target < 45 sec for 1-3 days | Multi-day + validation can be longer |
| OpenAI timeout | 30 sec default | `OPENAI_TIMEOUT_SECONDS` |
| OpenAI retries | 3 default | `OPENAI_MAX_RETRIES` |
| Plan validation retries | 3 attempts | `MenuAgent._generate_valid_plan` |
| Max chat history | 50 messages | In-memory only |
| Concurrent users | 1 household/session | No auth/session isolation |
| Reliability | Best-effort local PoC | No HA, no queue, no retry jobs |
| Cost budget | Low PoC budget, manual monitoring | Production needs usage telemetry and budget alarms |
| Storage | Local CSV | No transactions, no migrations |
| Security | Local trusted environment | CORS wildcard and no auth are not production-ready |

## 12. Control points

Control points that must be preserved during implementation:

- all state mutation goes through tool handlers or HTTP data endpoints;
- meal plans are saved only after successful validation;
- ValidatorAgent must fail closed;
- DataManager must keep schema whitelist;
- chat history must remain bounded;
- temp uploads must be unique and removed after request;
- sensitive settings/secrets must stay outside git;
- logs must not expose more personal data than needed for debugging;
- destructive operations need confirmation before production.

## 13. Linked docs

- Diagrams: `docs/diagrams/`
- Module specs: `docs/specs/`
- Governance and risks: `docs/governance.md`
- Product proposal and scenarios: `docs/product-proposal.md`
