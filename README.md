# Dash support monorepo

A Flutter chat app and a FastAPI backend that runs Claude with custom tools.
The app never holds the API key. The backend owns the tool loop and the hooks.

## Layout

```code
dash/
  pubspec.yaml                Dart pub workspace root; melos: key holds the dev scripts
  .vscode/launch.json        run the app in Chrome
  apps/
    mobile/                  the Flutter app
      lib/
        main_development.dart
        bootstrap.dart
        app/
        chat/
          bloc/
          view/
    packages/
      chat_repository/        http client and models, talks to the backend
  backend/
    requirements.txt
    contracts/
      chat.openapi.yaml      the /chat request and response shape
    evals/
      run_evals.py             behavioral evals against the live agent
    agent/
      core.py                 the Claude tool-use loop
      hooks.py                pre_hook, post_hook
      tools.py                get_customer, lookup_order, process_refund, escalate_to_human
    api/
      main.py                 FastAPI app
      routes/
        health.py              GET /health
        chat.py                 POST /chat
```

## Backend, local

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env        # then put your real key in this file
uvicorn api.main:app --reload --port 8000
```

Check it: `curl http://localhost:8000/health`

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

`melos run evals` also calls the live Anthropic API, so it needs
`ANTHROPIC_API_KEY` set the same way.

## Flutter app

```bash
dart pub global activate melos
melos bootstrap
melos run app
```

The base URL comes from a dart-define named BASE_URL and defaults to
`http://10.0.2.2:8000`, which the Android emulator uses to reach the host.

## Run in Chrome

Open the repo in VS Code and pick the "mobile (chrome)" run config, which
passes `BASE_URL=http://localhost:8000`. From the command line:

```bash
cd apps/dash
flutter run -d chrome --dart-define=BASE_URL=http://localhost:8000
```

## Melos scripts

- `melos run backend` starts FastAPI, needs the venv active
- `melos run app` runs the Flutter app
- `melos run analyze` and `melos run analyze:backend`
- `melos run test` and `melos run test:backend`
- `melos run check` runs all four
- `melos run evals` runs behavioral evals against the live agent (real
  Anthropic API calls, not part of `check`)
