# Спецификация - Observability и Evals

## 1. Ответственность

Observability должна показывать, правильно ли система маршрутизирует запросы, соблюдает ли safety constraints, корректно ли меняет состояние и укладывается ли в ограничения по latency/cost.

Evals должны покрывать и deterministic behavior, и agentic behavior.

## 2. Текущее состояние observability

В текущем PoC observability легковесная:

- agents возвращают `logs` в API response;
- тесты проверяют отдельные safety-свойства;
- console output может показывать ошибки загрузки prompt или validator;
- CSV state можно проверить напрямую.

Пока нет централизованного log store, metrics backend, trace IDs и cost telemetry.

## 3. Обязательные logs

В будущем каждый request должен порождать structured events:

| Event | Fields |
|---|---|
| `request_received` | request id, interface, has_image, language |
| `router_decision` | direct/tool/handoff, tool name |
| `context_assembled` | sections, approximate size, warnings |
| `tool_executed` | tool name, success, affected table, row count |
| `planning_attempt` | dates count, attempt number |
| `validation_result` | valid count, invalid count, issue categories |
| `response_returned` | latency, success, logs count |
| `error` | component, error type, safe message |

Не логировать:

- API keys;
- raw images;
- полные health profiles;
- полные hidden prompts;
- чувствительные пользовательские данные без явной необходимости даже в local debug mode.

## 4. Метрики

| Metric | Для чего нужна |
|---|---|
| p50/p95 chat latency | Контроль скорости простых запросов |
| p50/p95 planning latency | Контроль долгих циклов planning/validation |
| router handoff accuracy | Цель > 85% |
| tool call success rate | Цель > 90% |
| validation first-pass rate | Цель > 60% |
| validation fail-closed count | Детект проблем OpenAI/parse |
| average planning retries | Цель < 1.5 |
| plans violating allergy constraints | Цель 0 |
| OpenAI request count per task | Контроль стоимости |
| estimated token/cost per task | Бюджетирование |
| CSV write failures | Надежность хранения |

## 5. Evals

### Deterministic tests

Должны покрывать:

- schema filtering в DataManager;
- отклонение неизвестного CSV filename;
- уникальность и cleanup temp upload filenames;
- fail-closed поведение validator;
- chat history truncation;
- сохранение meal plan только после validation;
- запись nutrition log для eaten meals;
- удаление продукта из inventory после eaten log.

### Agent scenario evals

Должны покрывать продуктовые сценарии:

- SC-01 inventory update;
- SC-02 single-day meal plan;
- SC-03 multi-day plan;
- SC-04 meal logging;
- SC-05 rotation dishes;
- EC cold start;
- EC allergy conflict;
- EC empty inventory;
- EC out-of-domain request.

### Manual review checklist

Для каждого agent run:

- Правильно ли выбран route?
- Соблюдены ли restrictions?
- Приоритизированы ли expiring items?
- Добавлены ли missing ingredients в shopping list?
- Объяснил ли ответ важную неопределенность?
- Совпали ли state changes с намерением пользователя?

## 6. Trace design

Будущая структура trace:

```text
request
  router_call
    context_assembly
    openai_router_completion
    tool_execution or handoff
  specialist_call
    specialist_context
    openai_specialist_completion
    validation_loop
      plan_generation
      validation_call
      retry_feedback
  persistence
  response
```

Каждый trace должен иметь request id, который передается через logs.

## 7. Alert conditions

Для production-like demo:

- OpenAI failure rate > 5%;
- p95 chat latency > 12 sec;
- p95 planning latency > 60 sec;
- обнаружено allergy violation;
- CSV write failure;
- повторяющиеся validator fail-closed results;
- daily cost budget exceeded.

