# Repository Guidelines

## Project Structure & Module Organization
- `backend/` holds Django (`config/settings/*` for env configs, `apps/` per domain, `core/` for shared pipeline and AI clients); supporting notes live in `backend/docs/`.
- `frontend/` is a Vue 2 SPA under `frontend/src/` (components, views, Vuex store) with static assets in `frontend/src/assets/`. Infra artifacts live in `docker/` and `docker-compose.yml`, while generated media belongs in `storage/` outside Git.

## Build, Test, and Development Commands
- Launch everything with `docker-compose up -d`, then run `docker-compose exec backend python manage.py migrate` or `createsuperuser` whenever schema or creds change.
- Backend dev: `cd backend && python manage.py runserver`, plus `celery -A config worker -l info` and `celery -A config beat -l info`; install deps inside a venv from `requirements/development.txt`. Frontend dev: `cd frontend && npm install && npm run dev`, `npm run build` for production, `npm run lint` before commits, and `bash test_sse.sh` for SSE regressions.

## Coding Style & Naming Conventions
Stick to PEP8 with four space indents, auto format via `black .`, and lint with `flake8 .`; keep modules SOLID aligned and name stages after their domain action (`rewrite`, `image_generation`). Vue code follows ESLint defaults, camelCase scripts, kebab case component tags, and the existing atoms or molecules or organisms folder split.

## Testing Guidelines
Use `cd backend && pytest --cov apps --cov core` as the primary suite, storing new `test_*.py` files next to the feature or alongside existing probes such as `backend/test_celery_redis.py`. Reserve `python manage.py test` for smoke checks and rerun `test_sse.sh` after touching Channels or SSE code; include repro notes or screenshots for UI work until automated component tests are added.

## Commit & Pull Request Guidelines
Write short imperative commit subjects under roughly 60 characters (module prefix optional) and reference any related ticket or doc. PRs must explain intent, list commands executed, surface schema or env var changes, attach UI screenshots when applicable, and tag a reviewer from the affected layer.

## Security & Configuration Tips
Copy `.env.example` to `.env`, inject keys locally, and avoid committing them; Django reads env vars from that file. Keep generated media in `storage/` or external buckets, prune stale files, rotate provider credentials through the admin UI, and keep logs free of raw secrets.
