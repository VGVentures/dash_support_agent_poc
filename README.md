# Dash support monorepo

A Flutter chat app and a FastAPI backend that runs Claude with custom tools.
The app never holds the API key. The backend owns the tool loop and the hooks.

## Layout

```
dash/
  melos.yaml                 manages the Dart workspace and dev scripts
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
    app/
      main.py                 FastAPI app and the /chat loop
      hooks.py                pre_hook, post_hook
      tools.py                get_customer, lookup_order, process_refund, escalate_to_human
```

## Backend, local

```
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env        # then put your real key in this file
uvicorn app.main:app --reload --port 8000
```

Check it: `curl http://localhost:8000/health`

## Flutter app

```
dart pub global activate melos
melos bootstrap
melos run app
```

The base URL comes from a dart-define named BASE_URL and defaults to
`http://10.0.2.2:8000`, which the Android emulator uses to reach the host.

## Run in Chrome

Open the repo in VS Code and pick the "mobile (chrome)" run config, which
passes `BASE_URL=http://localhost:8000`. From the command line:

```
cd apps/dash
flutter run -d chrome --dart-define=BASE_URL=http://localhost:8000
```

## Melos scripts

- `melos run backend` starts FastAPI, needs the venv active
- `melos run app` runs the Flutter app
- `melos run analyze` and `melos run analyze:backend`
- `melos run test` and `melos run test:backend`
- `melos run check` runs all four
