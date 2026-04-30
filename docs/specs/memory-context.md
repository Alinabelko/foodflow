# Спецификация - Memory и Context

## 1. Типы памяти

| Тип | Где хранится | Назначение |
|---|---|---|
| Session chat history | `RouterAgent.chat_history` | Контекст текущего диалога |
| Persistent household memory | `data/*.csv` | Инвентарь, предпочтения, ограничения, планы |
| Settings memory | `data/settings.json` | Язык и пользовательские настройки |
| Request context snapshot | system message | Актуальные данные для LLM на один запрос |
| Operational logs | API response | Видимость выполнения для пользователя/отладки |

## 2. Session state

RouterAgent владеет chat history:

- user messages добавляются с текстом и опциональным изображением;
- assistant/tool messages добавляются после ответа модели или выполнения tool;
- история обрезается до последних 50 сообщений;
- `clear_history()` очищает только историю чата;
- restart backend очищает chat history, но не CSV-память.

## 3. Политика persistent memory

Persistent memory обновляется только через:

- tool handlers;
- FastAPI data endpoints;
- Streamlit data editor;
- инициализацию отсутствующих файлов в DataManager.

Все CSV-записи должны соответствовать `DataManager.SCHEMAS`. Лишние поля фильтруются при `add_entry` и `save_table`.

## 4. Политика сборки контекста

Каждый agent turn должен включать:

- agent-specific system prompt;
- language setting;
- релевантный context snapshot;
- bounded chat history.

RouterAgent и MenuAgent используют `ContextAssembler`. ShoppingAgent сейчас использует более короткий собственный контекст: количество продуктов в инвентаре и первые позиции shopping list.

## 5. Context budget

Текущие жесткие ограничения:

- chat history: 50 сообщений;
- recent eaten history: 7 записей;
- expiring soon threshold: 2 дня;
- shopping list в ShoppingAgent: первые 10 позиций.

Текущие пробелы:

- нет подсчета токенов;
- нет adaptive compression;
- нет summary старого чата;
- нет приоритетного trimming, кроме ручных лимитов по секциям.

## 6. Privacy policy для контекста

В LLM нужно отправлять только данные, нужные для текущей задачи:

- включать ограничения при планировании еды;
- включать inventory при планировании и покупках;
- не отправлять полные raw CSV dumps, если достаточно summary;
- никогда не отправлять secrets;
- не включать `.env` или API keys в prompts/logs.

## 7. Ошибки и восстановление

| Ошибка | Восстановление |
|---|---|
| Chat history слишком большая | Обрезать до последних 50 сообщений |
| CSV-файл отсутствует | DataManager создает файл со schema header |
| CSV пустой | Читать как пустой список; может включиться cold-start notice |
| Невалидная дата в expiry field | Продукт считается обычной inventory-позицией |
| Backend restart | Agents создаются заново, CSV-память сохраняется |

