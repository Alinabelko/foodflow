# C4 Context - FoodFlow PoC

## Purpose

Эта диаграмма показывает систему как черный ящик: кто с ней взаимодействует, какие внешние сервисы используются и где проходит граница PoC.

```mermaid
flowchart LR
    User["Пользователь / семья"]
    Browser["Browser UI<br/>React или Streamlit"]
    FoodFlow["FoodFlow PoC<br/>AI meal planning and kitchen memory"]
    OpenAI["OpenAI API<br/>LLM, tools, structured output, vision"]
    LocalFS["Локальная файловая система<br/>data/*.csv, settings.json"]

    User -->|"сообщения, правки таблиц, изображения"| Browser
    Browser -->|"HTTP / local session"| FoodFlow
    FoodFlow -->|"LLM requests"| OpenAI
    OpenAI -->|"responses, tool calls, parsed objects"| FoodFlow
    FoodFlow <-->|"read/write CSV"| LocalFS
    FoodFlow -->|"ответы, logs"| Browser
    Browser -->|"план, список покупок, состояние"| User
```

## Text Description

FoodFlow PoC работает как локальная система для одной семьи. Пользователь взаимодействует с ней через web-интерфейс: React frontend через FastAPI или Streamlit app. Внутри границы FoodFlow находятся backend, agent orchestration, retrieval/context assembly, tool layer и CSV-хранилище.

OpenAI API находится вне границы системы и используется только для reasoning, tool/function calling, structured output и анализа изображения. Локальные CSV-файлы считаются persistence boundary: это долговременная память PoC.

## Boundaries

Inside FoodFlow:

- HTTP API;
- agent orchestration;
- context assembly;
- tool handlers;
- CSV schemas and CRUD;
- local logs returned to UI.

Outside FoodFlow:

- OpenAI model execution;
- browser runtime;
- operating system and filesystem;
- any future delivery/nutrition/recipe APIs.

