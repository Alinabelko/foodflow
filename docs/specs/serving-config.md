# Спецификация - Serving и Config

## 1. Режимы запуска

| Режим | Entry point | Назначение |
|---|---|---|
| FastAPI backend | `src/server.py` | API для React frontend |
| React frontend | `frontend` Vite app | Основной web UI |
| Streamlit app | `src/web_app.py` | Локальный demo/control center |
| CLI/dev | `src/main.py`, если используется | Локальные эксперименты |

## 2. Конфигурация

Environment variables:

| Переменная | Обязательна | Значение по умолчанию | Назначение |
|---|---|---|---|
| `OPENAI_API_KEY` | Да для реальных LLM-вызовов | none | Аутентификация OpenAI |
| `OPENAI_MAX_RETRIES` | Нет | `3` | Retry для OpenAI client |
| `OPENAI_TIMEOUT_SECONDS` | Нет | `30` | Timeout для OpenAI client |

Локальные файлы:

- `.env` - локальные secrets/config, нельзя коммитить;
- `.env.example` - безопасный шаблон;
- `data/settings.json` - язык и пользовательские настройки;
- `data/*.csv` - состояние приложения.

Default model в текущем коде:

- `gpt-5-mini` в `BaseAgent.model`.

## 3. Запуск API

FastAPI server:

- app instance: `server.app`;
- direct run по умолчанию: `uvicorn.run(app, host="0.0.0.0", port=8000)`;
- CORS сейчас разрешает все origins, это PoC-ограничение.

Долгие операции:

- `/api/chat` использует `run_in_threadpool` для blocking agent call;
- `/api/translate_database` тоже работает в threadpool;
- background queue в PoC отсутствует.

## 4. Файловое хранение

Data directory:

- задается в `DataManager.DATA_DIR`;
- указывает на repository-level `data/`;
- отсутствующие CSV-файлы создаются со schema headers.

Temp upload files:

- создаются через `tempfile.NamedTemporaryFile(delete=False, prefix="foodflow_")`;
- suffix очищается на основе исходного filename;
- удаляются в `finally` внутри `/api/chat`.

## 5. Операционные ограничения

| Ограничение | Текущее состояние PoC |
|---|---|
| Auth | Нет |
| CORS | Wildcard |
| Concurrency | Одно домохозяйство, нет session isolation |
| Persistence | Локальные CSV |
| Background jobs | Нет |
| Deploy target | Локальная/dev машина |
| Backup | Ручной |
| Secrets | `.env` |

## 6. Политика версионирования

Для PoC:

- изменения модели фиксировать в этом spec и/или `system-design.md`;
- prompt files хранить под version control;
- добавлять тесты при изменении tool schemas или CSV schemas;
- не делать тихие изменения CSV schema без migration/default handling.

## 7. Что нужно до production

- Заменить wildcard CORS.
- Добавить authentication и authorization.
- Перенести secrets в secret manager.
- Заменить CSV на SQLite/PostgreSQL.
- Добавить migration strategy.
- Добавить queue/background jobs для долгих задач.
- Добавить health/readiness endpoints.
- Добавить structured logs и traces.
