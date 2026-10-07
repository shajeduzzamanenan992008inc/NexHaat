# Stage 13: private local AI and operator setup

Stage 13 uses three separate private services: the Flask marketplace, a local
Qwen inference endpoint, and a local embedding endpoint. Optional Whisper,
CosyVoice, and SearXNG services can be deployed beside the inference service.
Do not put model or provider credentials in source control.

## Private model hosts

Provision a private GPU host with enough memory for the selected Qwen 3.5 9B
quantization and the chosen inference runtime. Serve Qwen3.5-9B behind an
OpenAI-compatible `/v1/chat/completions` API with image input enabled. Serve
Qwen3-Embedding-0.6B through `/v1/embeddings` and return 1,024-dimensional
vectors. Use an internal HTTPS endpoint, authenticated service access, network
allowlisting from the web app, and request/response body retention disabled.
The app must not expose the GPU endpoint directly to browsers or Telegram.
The application validates 1,024 embedding dimensions; the Qwen model card lists
that output dimension as its maximum. PostgreSQL pgvector supports that size and
the migration creates the cosine HNSW index. See the [Qwen local model card](https://huggingface.co/Qwen/Qwen3.5-9B),
[Qwen embedding model card](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B), and
[pgvector index guide](https://github.com/pgvector/pgvector#hnsw).

Configure private application settings:

- `AI_LOCAL_BASE_URL`, `AI_LOCAL_MODEL`, optional `AI_LOCAL_API_KEY`
- `AI_EMBEDDING_BASE_URL`, `AI_EMBEDDING_MODEL`, optional `AI_EMBEDDING_API_KEY`
- `AI_ASR_BASE_URL`, `AI_ASR_MODEL` for local Whisper transcription
- `AI_TTS_BASE_URL`, `AI_TTS_MODEL`, and optionally `AI_TTS_VOICE` for the
  configured Bengali CosyVoice voice
- `AI_SEARCH_BASE_URL` for a private SearXNG-compatible `/search?format=json`
  endpoint

All provider identifiers must match the deployed provider's current model
catalog. The app does not assume names such as “GPT-6 Astra” are real IDs.

## Optional external specialists

External requests are off until `AI_EXTERNAL_ENABLED=true`, the account or
Telegram user opts in, at least two provider credentials and model IDs are
configured, per-model input/output rates are entered, and
`AI_EXTERNAL_MONTHLY_BUDGET_USD` is greater than zero. Rates must match the
configured model and current provider price list. The app reserves the worst
case cost for up to three bounded calls before sending any request. Reservations
are not refunded after partial failures. Configure a matching provider-side
spending cap as an additional safeguard.

Settings are grouped by provider. Configure the selected provider's `AI_OPENAI_API_KEY`,
`AI_OPENAI_MODEL`, `AI_OPENAI_BASE_URL`, `AI_OPENAI_INPUT_USD_PER_MILLION`, and
`AI_OPENAI_OUTPUT_USD_PER_MILLION`, or the matching `AI_ANTHROPIC_*`, `AI_GEMINI_*`,
or `AI_DEEPSEEK_*` settings. Use the provider's current model catalog; Gemini's
OpenAI-compatible endpoint is documented as a compatibility path with feature
limitations. Model identifiers are never guessed by the application. See
[Gemini compatibility](https://ai.google.dev/gemini-api/docs/openai),
[Anthropic model status](https://platform.claude.com/docs/en/about-claude/model-deprecations),
and [DeepSeek Chat Completions](https://api-docs.deepseek.com/api/create-chat-completion/).

Security Bot remains local-only. External specialist prompts never contain
security records, tool results, seller/admin database results, chat history,
images, voice, or retrieved knowledge. Shopping and private delivery facts are
served by role-scoped local tools.

## Curated retrieval and migration

Apply the additive Alembic migration before indexing. PostgreSQL deployments
need permission to enable the `vector` extension. SQLite stores vectors as JSON
for development and uses bounded cosine similarity in Python.

Add reviewed Markdown only beneath `docs/ai-knowledge/`. Assign an intended
visibility scope when indexing; do not put customer records, provider secrets,
raw conversations, or uploaded media there. Run:

```sh
flask --app run.py db upgrade
flask --app run.py index-ai-knowledge --scope public
```

The index command calls only the configured local embedding service.
It scans only top-level Markdown files in `docs/ai-knowledge/`, reuses hashes
to avoid duplicate chunks, deletes stale chunks when a source changes, validates
all 1,024 finite numeric embedding values, and rolls back the index transaction
if indexing fails. Retrieval returns public guidance plus only the caller's
role scope. Keep current prices, stock, orders, return eligibility, private
records, conversations, uploads, and unverified model output out of this corpus;
the live marketplace tools remain authoritative for changing or account-scoped
facts.

## Quality benchmark and controlled improvement

After configuring the private local inference endpoint, run
`flask --app run.py benchmark-ai`. It checks arithmetic, Bengali and Banglish
understanding, a reasoning trap, Python syntax/function presence, a common
debugging concept, and uncertainty around private marketplace facts. It also
checks English, Bangla, and Banglish shopping/support questions that require
verified public guidance or an available live source for changing product and
account facts. It sends only fixed prompts to the configured local endpoint,
explicitly disables external specialists, and prints case IDs/status only. It
does not persist or print model answers. A passing automated marker is not
proof of code correctness or general model quality; Admin review and proper
isolated code-execution tests are still required for those claims.

This is a measurement tool, not model training. Improve answers by reviewing
failures and adding concise, verified guidance under `docs/ai-knowledge/`,
re-indexing with `index-ai-knowledge`, and re-running the benchmark. Do not
automatically ingest conversations, user feedback, uploads, generated code, or
unverified model output. Any later lesson-learning or code change must be
sanitized, Admin-approved, tested, and reversible. Model-weight fine-tuning
requires a separately approved dataset, private training infrastructure, and
its own evaluation/rollback gate; it is not performed by this application.
The current indexer is not a lesson approval workflow: Guardian or coding
results cannot be automatically proposed, approved, or written to persistent
knowledge. Only operator-reviewed Markdown is indexed. Stage 14 still needs a
separately designed Admin proposal/review workflow for reusable lessons.

## Acceptance evidence and remaining operator checks

Mocked code tests verify routing, role boundaries, privacy, consent, provider
limits, and fallback. Before Stage 13 is operationally accepted, deploy the
private model services, verify local vision/Whisper/TTS endpoints, confirm the
PostgreSQL `vector` extension and HNSW index, run the curated knowledge index,
run `benchmark-ai`, and send staging messages through both Telegram bots.
Record only status and redacted metadata; never copy tokens or prompt bodies
into the roadmap.
