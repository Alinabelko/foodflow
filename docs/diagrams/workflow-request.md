# Workflow / Graph Diagram - Request Execution

## Purpose

Диаграмма показывает пошаговое выполнение пользовательского запроса, включая основные ветки ошибок.

```mermaid
flowchart TD
    Start["User sends message"] --> API["FastAPI / Streamlit receives input"]
    API --> Upload{"Image attached?"}
    Upload -->|yes| Temp["Save unique temp image"]
    Upload -->|no| Router
    Temp --> Router["RouterAgent.process_message"]

    Router --> Ctx["Assemble context snapshot"]
    Ctx --> LLM["OpenAI call with router tools"]
    LLM --> ApiErr{"API error?"}
    ApiErr -->|yes| ErrResp["Return error, no mutation"]
    ApiErr -->|no| ToolChoice{"Tool calls?"}

    ToolChoice -->|no| Direct["Append assistant message and return response"]
    ToolChoice -->|yes| Handoff{"Handoff tool?"}

    Handoff -->|MenuAgent| Menu["MenuAgent.run"]
    Handoff -->|ShoppingAgent| Shopping["ShoppingAgent.run"]
    Handoff -->|no| LocalTools["Execute Router local tools"]

    LocalTools --> SaveState["DataManager writes CSV"]
    SaveState --> FinalLLM["Final OpenAI response using tool outputs"]
    FinalLLM --> Return["Return response + logs"]

    Shopping --> ShoppingErr{"Shopping API/tool error?"}
    ShoppingErr -->|yes| ReturnShoppingErr["Return ShoppingAgent error"]
    ShoppingErr -->|no| Return

    Menu --> Plan["Generate MultiDayMealPlan"]
    Plan --> PlanErr{"Generation/parse error?"}
    PlanErr -->|yes| PlanFail["Return generation error; no save"]
    PlanErr -->|no| Validate["Validate each DailyMealPlan"]
    Validate --> Valid{"All valid?"}
    Valid -->|yes| PersistPlan["Save meal_plans and missing shopping items"]
    PersistPlan --> Return
    Valid -->|no| Retries{"Attempts < 3?"}
    Retries -->|yes| Feedback["Add validation issues as feedback"]
    Feedback --> Plan
    Retries -->|no| MaxFail["Return failure with last issues; no save"]

    Return --> Cleanup{"Temp image exists?"}
    ErrResp --> Cleanup
    Direct --> Cleanup
    PlanFail --> Cleanup
    MaxFail --> Cleanup
    ReturnShoppingErr --> Cleanup
    Cleanup -->|yes| DeleteTemp["Delete temp file"]
    Cleanup -->|no| End["End"]
    DeleteTemp --> End
```

## Text Description

Основной путь: UI отправляет запрос, backend вызывает RouterAgent, RouterAgent собирает context snapshot и обращается к OpenAI. Модель либо отвечает напрямую, либо выбирает tool. Handoff tools переключают выполнение в MenuAgent или ShoppingAgent. Local tools выполняют ограниченные изменения состояния через DataManager.

Для meal planning есть отдельный критический цикл: generation -> validation -> retry. Если validation не проходит, issues возвращаются в prompt как feedback. После трех неудачных попыток план не сохраняется.

Ветки ошибок спроектированы так, чтобы по возможности не мутировать состояние: ошибка API до tool execution не меняет CSV; ошибка generation не сохраняет план; ошибка Validator приводит к invalid report и fail-closed отказу.

## Error Branches

| Branch | User-visible result | State mutation |
|---|---|---|
| Router OpenAI error | Error response | No mutation |
| Shopping OpenAI error | Error response | No mutation before tool execution |
| Plan parse/generation error | Error response | No plan saved |
| Validation failure after retries | Failure with issues | No plan saved |
| Validator API failure | Invalid report | No plan saved |
| Unknown tool | Tool output says unknown | No unsupported mutation |

