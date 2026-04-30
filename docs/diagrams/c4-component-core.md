# C4 Component - Agent Core

## Purpose

Диаграмма раскрывает внутреннее устройство ядра системы: как RouterAgent, специализированные агенты, context, tools, модели и DataManager связаны между собой.

```mermaid
flowchart TB
    UserMsg["User message<br/>text + optional image"]

    subgraph RouterAgent["RouterAgent"]
        RH["chat_history<br/>max 50 messages"]
        RPrompt["router_prompt.md"]
        RTools["Router tool schema"]
        RExec["local tool executor"]
        Handoff["handoff dispatcher"]
    end

    subgraph SpecialistAgents["Specialist Agents"]
        Menu["MenuAgent"]
        Shopping["ShoppingAgent"]
        Validator["ValidatorAgent"]
    end

    subgraph SharedCore["Shared Core"]
        Base["BaseAgent<br/>OpenAI client + prompt loader"]
        Context["ContextAssembler"]
        Models["Pydantic models<br/>MultiDayMealPlan, ValidationReport"]
        DM["DataManager"]
    end

    subgraph Storage["CSV State"]
        People["people.csv"]
        Inventory["fridge/pantry/freezer.csv"]
        History["history.csv / nutrition_log.csv"]
        Plans["meal_plans.csv"]
        ShoppingList["shopping_list.csv"]
        Dishes["dishes.csv"]
    end

    OpenAI["OpenAI API"]

    UserMsg --> RH
    RH --> RPrompt
    Context --> RPrompt
    RPrompt --> OpenAI
    RTools --> OpenAI
    OpenAI -->|"assistant response or tool calls"| RExec
    RExec -->|"local state mutations"| DM
    RExec -->|"handoff"| Handoff
    Handoff --> Menu
    Handoff --> Shopping
    Menu --> Validator
    Menu --> Models
    Validator --> Models
    Menu --> Context
    RouterAgent --> Context
    Shopping --> DM
    Context --> DM
    Base --> OpenAI
    DM --> People
    DM --> Inventory
    DM --> History
    DM --> Plans
    DM --> ShoppingList
    DM --> Dishes
```

## Component Contracts

| Component | Input | Output | Side Effects |
|---|---|---|---|
| RouterAgent | user text, optional image | `{response, logs}` | chat history, CSV via local tools |
| MenuAgent | chat history | `{content, logs}` | meal_plans.csv, shopping_list.csv |
| ShoppingAgent | chat history | `{content, logs}` | inventory CSV, shopping_list.csv, shopping_habits.csv |
| ValidatorAgent | `DailyMealPlan`, context string | `ValidationReport` | None |
| ContextAssembler | current CSV state | context string | None |
| DataManager | filename + operation | records/status | CSV read/write |

