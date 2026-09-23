# Dash support monorepo

A Flutter chat app backed by a FastAPI service that runs Claude in a tool-use
loop. The app never holds the Anthropic API key — it only ever talks to the
backend over HTTP. The backend owns the key, the tool loop, and the
validation and audit hooks around every tool call.

## How a message flows

1. The Flutter app posts `{ user_id, messages }` to `POST /chat`.
2. [`agent/core.py`](backend/agent/core.py) runs `run_conversation()`: it
   calls the Anthropic API with the conversation, the system prompt, and the
   five tool schemas, up to 10 iterations.
3. When Claude asks for a tool, the input is validated against a Pydantic
   model, passed through `pre_hook` (auth check, refund policy, identity
   verification), run, then passed through `post_hook` (marks the customer
   verified, writes refund audit records).
4. Tool errors are classified `retryable` or not. Two non-retryable errors in
   a row (validation failures, blocked calls) end the conversation early with
   a message telling the user to escalate, instead of burning iterations.
5. The loop ends when Claude replies with text instead of a tool call, and
   the reply plus full message history go back to the app.

## Layout

```code
dash_support/
  pubspec.yaml               Dart workspace root; the `melos:` key holds the dev scripts
  .vscode/launch.json        Chrome and mobile run configs
  apps/
    dash/                    the Flutter app
      lib/
        main.dart
        bootstrap.dart
        app/
        chat/
          bloc/              ChatBloc: events in, states out
          view/
    packages/
      chat_repository/       HTTP client + models, talks to the backend
  backend/
    requirements.txt
    contracts/
      chat.openapi.yaml      the /chat request and response shape
    agent/
      core.py                 the Claude tool-use loop, retry/escalation logic
      hooks.py                pre_hook (auth, policy), post_hook (audit, state)
      tools.py                get_customer, lookup_order, get_orders,
                               process_refund, escalate_to_human
    api/
      main.py                 FastAPI app, CORS
      routes/
        health.py              GET /health
        chat.py                 POST /chat
    evals/
      run_evals.py             behavioral evals against the live agent
      compare_models.py        same evals, run across multiple models
      report.py                PDF report generation
```

## Quickstart

### Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env        # then put your real key in this file
uvicorn api.main:app --reload --port 8000
```

Check it: `curl http://localhost:8000/health`

### Flutter app

```bash
dart pub global activate melos
melos bootstrap
cd apps/dash
flutter run -d chrome --dart-define=BASE_URL=http://localhost:8000
```

Or open the repo in VS Code and pick the "chrome" run config from
[`.vscode/launch.json`](.vscode/launch.json).

The base URL comes from a dart-define named `BASE_URL`. It defaults to
`http://10.0.2.2:8000` in [`main.dart`](apps/dash/lib/main.dart), which is
how the Android emulator reaches the host machine. Chrome, desktop, and the
iOS simulator should pass `http://localhost:8000` explicitly, as above.

## Environment variables

The backend reads its config from a `.env` file in `backend/`, loaded by
`python-dotenv` in [`agent/core.py`](backend/agent/core.py). Shell exports
take priority over `.env`, so setting the variable in your shell overrides
the file.

Copy the template and fill in your real key:

```bash
cp .env.example backend/.env
```

- `ANTHROPIC_API_KEY` — required, no default. From the
  [Anthropic console](https://console.anthropic.com/settings/keys). Without
  it, every request to `/chat` fails.
- `CLAUDE_MODEL` — optional, defaults to `claude-sonnet-4-6`. Overrides which
  model the agent calls.

`backend/.env` is gitignored — never commit it. `.env.example` (at the repo
root) is the checked-in template and should only ever hold placeholder
values.

`melos run evals` and `melos run evals:compare` also call the live Anthropic
API, so they need `ANTHROPIC_API_KEY` set the same way.

## The agent

### Tools

All five tools live in [`agent/tools.py`](backend/agent/tools.py), each
backed by a Pydantic input model and an in-memory mock store (swap the
marked spots for a real database, payment provider, and help desk).

| Tool | Purpose |
| --- | --- |
| `get_customer` | Look up a customer by id or email. Verifying identity here unlocks refunds. |
| `lookup_order` | Fetch one order, optionally confirming it belongs to a given customer. |
| `get_orders` | List a customer's recent orders, newest first, up to `max_items`. |
| `process_refund` | Refund an order. Rejects orders that don't exist, aren't refundable, or where the amount exceeds the order total. |
| `escalate_to_human` | Create a help desk ticket and hand off the conversation. |

### Hooks

[`agent/hooks.py`](backend/agent/hooks.py) wraps every tool call:

- `pre_hook` blocks unauthenticated requests, requires `get_customer` +
  `lookup_order` before any `process_refund`, and caps refunds at
  `REFUND_LIMIT` (200.0), directing anything larger to `escalate_to_human`.
- `post_hook` marks the conversation's customer as verified once
  `get_customer` succeeds, and appends successful refunds to an in-memory
  audit trail.

### System prompt

The system prompt in `core.py` scopes the agent to Dash order/refund/account
topics, tells it to verify identity before refunding, and to escalate
immediately when a customer expresses frustration or asks for a human —
regardless of phrasing.

## Melos scripts

Defined under the `melos:` key in [`pubspec.yaml`](pubspec.yaml).

| Script | What it does |
| --- | --- |
| `melos run app` | Runs the Flutter app against the local backend |
| `melos run backend` | Starts FastAPI on port 8000 (needs the venv active) |
| `melos run analyze` | `dart analyze` across the workspace |
| `melos run analyze:backend` | Lints the Python backend with ruff |
| `melos run test` | Runs Dart and Flutter tests |
| `melos run test:backend` | Runs the Python tests with pytest |
| `melos run check` | Runs all four analyze/test scripts above |
| `melos run evals` | Behavioral evals against the live agent, builds a PDF report (real API calls, not part of `check`) |
| `melos run evals:compare` | Evals across multiple models with a comparison report (real API calls, not part of `check`) |
