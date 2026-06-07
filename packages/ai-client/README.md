# ai-client

Shared AI client library for **MindJira**. Асинхронний Python-клієнт для роботи з LLM-провайдерами (Anthropic Claude та NVIDIA NIM) із вбудованим rate limiting, retry, розрахунком вартості та логуванням витрат у БД.

---

## Стек

- Python 3.12+
- Pydantic 2
- SQLAlchemy 2 (async)
- Anthropic SDK / OpenAI SDK
- tenacity (retry)
- uv

---

## Встановлення

```bash
cd packages/ai-client
uv pip install -e .
```

Або як залежність у сервісі:

```toml
# pyproject.toml сервісу
dependencies = [
    "ai-client",
]
```

---

## Поетапне налаштування

### Крок 1. Налаштуй `.env`

У корені проєкту (або у `.env` сервісу) додай змінні з префіксом `AI_`:

#### Варіант A — Anthropic Claude (оригінальний API)

```env
AI_ANTHROPIC_API_KEY=sk-ant-api03-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
AI_ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
# AI_BASE_URL=              <-- залиш порожнім або прибери
```

#### Варіант B — NVIDIA NIM (OpenAI-compatible)

```env
AI_ANTHROPIC_API_KEY=nvapi-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
AI_ANTHROPIC_MODEL=meta/llama-3.1-8b-instruct
AI_BASE_URL=https://integrate.api.nvidia.com/v1
```

> **Примітка:** для NVIDIA NIM модель береться з каталогу [build.nvidia.com](https://build.nvidia.com) (наприклад `meta/llama-3.1-8b-instruct`, `nvidia/llama-3.3-70b-instruct`, `z-ai/glm4.7`).

### Крок 2. Імпортуй у коді

```python
from ai_client import AIClient, AIClientSettings

settings = AIClientSettings()  # авто-зчитування з .env

client = AIClient(
    api_key=settings.ANTHROPIC_API_KEY,
    model=settings.ANTHROPIC_MODEL,
    base_url=settings.BASE_URL,      # None для Anthropic, URL для NIM
    max_concurrent=5,
)
```

---

## Умовності та обмеження

| Умова | Значення |
|-------|----------|
| `max_concurrent` | Семафор на 5 одночасних запитів (налаштовується) |
| Retry | 3 спроби, exponential backoff 2–10 секунд |
| Retry тільки на | `429 Rate Limit`, `5xx Server Error` |
| `401 Unauthorized` | Одразу `AIAuthError`, без retry |
| Температура | `0.1` (жорстко в коді) |
| Max tokens | `4096` за замовчуванням (перевизначається в методі) |
| Розрахунок ціни | $3 / 1M input tokens, $15 / 1M output tokens |

---

## Приклади використання

### Простий запит

```python
response = await client.complete(
    system_prompt="You are a helpful assistant.",
    user_prompt="Explain Docker in one sentence.",
)

print(response.content)
print(f"Input: {response.input_tokens}, Output: {response.output_tokens}")
print(f"Cost: ${response.cost_usd:.6f}")
```

### З логуванням у БД

```python
from sqlalchemy.ext.asyncio import AsyncSession

response = await client.complete(
    system_prompt="You are a Jira expert.",
    user_prompt="Summarize this ticket.",
    session=db_session,           # AsyncSession
    service_name="sprint-summary",
    issue_key="PROJ-123",
)
```

> Якщо передано `session` — витрати автоматично запишуться в таблицю `ai_logs`.

### JSON mode (structured output)

```python
schema = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "priority": {"type": "string", "enum": ["Low", "Medium", "High"]},
    },
    "required": ["summary", "priority"],
}

data = await client.complete_with_schema(
    system_prompt="Analyze the Jira ticket.",
    user_prompt="Ticket: User cannot login via SSO.",
    schema=schema,
)

# data -> {"summary": "SSO login failure", "priority": "High"}
```

---

## Обробка помилок

```python
from ai_client.exceptions import AIAuthError, AIRateLimitError, AIResponseError

try:
    response = await client.complete(...)
except AIAuthError:
    # 401 — перевір API key
    ...
except AIRateLimitError:
    # 429 — занадто багато запитів (вичерпано retry)
    ...
except AIResponseError:
    # 5xx або інші API-помилки
    ...
```

---

## SQLAlchemy модель для логів

```python
from ai_client.db import AILog
```

| Поле | Тип | Опис |
|------|-----|------|
| `id` | UUID PK | Авто-генерація |
| `service_name` | str | Назва сервісу (напр. `gateway`) |
| `issue_key` | str \| None | Jira issue key (опціонально) |
| `input_tokens` | int | Токени на вході |
| `output_tokens` | int | Токени на виході |
| `cost_usd` | float | Вартість у доларах |
| `model` | str | Назва моделі |
| `created_at` | datetime | Час запису (server_default) |

Міграції створюй у сервісі через Alembic — `AILog` успадковує `DeclarativeBase`.

---

## Перемикання між провайдерами

| Провайдер | `AI_BASE_URL` | SDK |
|-----------|---------------|-----|
| **Anthropic Claude** | відсутній / `None` | `anthropic.AsyncAnthropic` |
| **NVIDIA NIM** | `https://integrate.api.nvidia.com/v1` | `openai.AsyncOpenAI` |
| **Ollama (локально)** | `http://localhost:11434/v1` | `openai.AsyncOpenAI` |
| **vLLM / інший proxy** | твій URL | `openai.AsyncOpenAI` |

---

## Тестування

```bash
cd packages/ai-client
uv run python test_ai_client.py
```

Скрипт авто-зчитує `.env` із кореня проєкту і виводить результат запиту.
