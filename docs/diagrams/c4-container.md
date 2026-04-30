# C4 Container - FoodFlow PoC

## Purpose

Диаграмма показывает основные deployable/runtime containers и их взаимодействие: frontend, backend, agent core, retrieval/context, tool layer, storage и observability.

```mermaid
flowchart TB
    subgraph Client["Client Layer"]
        React["React/Vite SPA<br/>chat, dashboard, data editor"]
        Streamlit["Streamlit UI<br/>local control center"]
    end

    subgraph Backend["Backend Container"]
        FastAPI["FastAPI server<br/>/api/chat, /api/data, /api/settings"]
        Router["RouterAgent<br/>orchestrator"]
        Menu["MenuAgent<br/>meal planning"]
        Shopping["ShoppingAgent<br/>inventory and shopping"]
        Validator["ValidatorAgent<br/>plan validation"]
        Context["ContextAssembler<br/>structured retrieval snapshot"]
        Tools["Tool Layer<br/>allowed state-changing functions"]
        DataManager["DataManager<br/>schema-aware CSV CRUD"]
        Obs["Observability Hooks<br/>logs, test assertions, future traces"]
    end

    subgraph Storage["Storage"]
        CSV["data/*.csv<br/>persistent household state"]
        Settings["settings.json<br/>language/config state"]
    end

    OpenAI["OpenAI API"]

    React --> FastAPI
    Streamlit --> Router
    FastAPI --> Router
    Router --> Menu
    Router --> Shopping
    Menu --> Validator
    Router --> Context
    Menu --> Context
    Context --> DataManager
    Tools --> DataManager
    Router --> Tools
    Menu --> Tools
    Shopping --> Tools
    DataManager --> CSV
    DataManager --> Settings
    Router --> OpenAI
    Menu --> OpenAI
    Shopping --> OpenAI
    Validator --> OpenAI
    Router --> Obs
    Menu --> Obs
    Shopping --> Obs
```

## Text Description

React/Vite и Streamlit - два UI-контейнера для PoC. React работает через FastAPI, Streamlit может обращаться к RouterAgent напрямую в одном Python process.

FastAPI отвечает за HTTP-контракты, загрузку изображений, settings, data endpoints и threadpool-вызов agent logic. Agent core состоит из RouterAgent, MenuAgent, ShoppingAgent и ValidatorAgent. ContextAssembler является retrieval-контейнером: он читает structured state и собирает prompt snapshot. Tool Layer ограничивает допустимые side effects, а DataManager выполняет реальные операции над CSV.

Observability в PoC минимальная: agents возвращают `logs`, тесты проверяют safety-свойства, а production tracing еще не реализован.

## Container Responsibilities

| Container | Responsibility |
|---|---|
| React/Vite SPA | User-facing chat, dashboard, table editing |
| Streamlit UI | Local all-in-one UI for debugging/demo |
| FastAPI | Public HTTP API for frontend |
| Agent core | Reasoning, routing, planning, validation |
| ContextAssembler | Deterministic retrieval/context snapshot |
| Tool Layer | Safe allowlist of state mutations |
| DataManager | Schema-aware persistence |
| CSV storage | Local durable state |
| Observability hooks | Logs now, metrics/traces later |

