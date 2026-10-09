# Food-Web — ALL FIXED / START HERE

## What was fixed

- AI external/OpenRouter free-model path: explicit free-model validation, local SQLite notice mode, consent/budget gates, and safer fallback handling.
- Single-word catalog search/typo handling: searches such as `garrden` stay in marketplace fuzzy search instead of being redirected to AI.
- Removed secrets, cookies, `.git` history, caches, and local artifacts from the repaired distribution archive.
- Added regression coverage for the AI free-model path and search routing.
- Python and JavaScript syntax validation passed.

## Windows + VS Code

1. Extract this project.
2. Copy your private `.env` into the project root. Never upload or commit it.
3. Open PowerShell in the project root.
4. Use your existing virtual environment if you have one, then install dependencies:

   `python -m pip install -r requirements.txt`

5. For local OpenRouter free-model development only:

   `$env:APP_ENV="development"`

   `python scripts/enable_openrouter_free_local.py`

6. Apply migrations:

   `flask --app run.py db upgrade`

7. Start the app:

   `python run.py`

8. In Customer AI, explicitly enable external AI assistance, then test with `hello`.

## Important

The repair does not contain your API key. Keep your existing key private. If the original ZIP was public/shared, rotate exposed credentials.

A live provider request was not executed in this environment because the uploaded API credentials must not be used by the repair process.
