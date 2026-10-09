# AI Builder and Project Guardian operations

Stage 14 is an Admin-only workspace in the existing Flask application. It stores projects only after an Admin opts in. A one-off upload remains transient. Project files are bounded and owner-scoped, and saved source is screened for common credential literals. Do not store production secrets, customer data, provider keys, or private deployment files in a project.

## Local analysis and external consent

The Builder uses the Stage 13 Core and tries the configured private local model first. ZIP, source-text, PDF, DOCX, image, and audio attachments are size-bounded. ZIP inspection is in memory and rejects traversal, symlinks, unsupported file types, excessive expansion, and generated/private directories. PDF and DOCX extraction is text-only. Image and audio bytes go only to the configured local vision or ASR endpoint; browser speech recognition is not used.

External processing is off by default. Source code requires Admin external-AI consent, project-level consent for a saved project, and a per-request choice. One-off code analysis requires the per-upload choice. External document or media analysis additionally requires consent saved in the current browser session and a per-upload choice. External calls still require configured providers, a positive budget, and a successfully delivered metadata-only Security Bot notice before each model request. Notices contain no prompt, source, media, secret, or personal data. Project prompts that look like credentials are rejected before external processing.

## Sandbox image and patch workflow

The test runner accepts only an immutable image reference: either a repository digest or a local Docker image ID in SHA-256 form. Build the repository's docker/ai-builder-sandbox.Dockerfile in a controlled build environment, then set AI_BUILDER_SANDBOX_IMAGE to the exact resulting image digest or image ID. Never configure a mutable tag. The image contains pytest and Flask only; project dependency files are not installed or executed during image build.

At runtime the app uses Docker with pull disabled, no network, a read-only project mount, a read-only root filesystem, a non-root UID, dropped capabilities, no-new-privileges, a PID limit, memory and CPU limits, and a bounded ephemeral temp filesystem. Only the current candidate source is mounted. Test output is not persisted. No host secrets, production database, Docker socket, or user-provided test command is mounted into the container.

When Docker or a pinned image is unavailable, patch tests report unavailable and approval remains blocked. Add a Python test file before running the test action. A passing test is required before approval; approval, applying to the saved project, and exporting the approved patch are separate authenticated actions. No route merges into the marketplace repository or deploys a project.

The Docker CLI is not installed in the current development workspace. Configure and verify the sandbox image in a controlled operator environment before treating patch execution or Stage 14 acceptance as complete.

## Guardian scans, deployment checks, and notices

The manual scan button runs the local static checks over a saved project. Scan queue rows have an HMAC signature derived from the application secret; a changed or invalid queue record fails closed. The scanner does not send source to external providers. High and critical findings create a durable audit-backed Security Bot alert with a protected Admin workspace link. Findings are deduplicated per project and rule location; failed deliveries remain in the existing retry queue.

Schedule the nightly scan command from the deployment scheduler:

    flask --app run.py guardian-scan --trigger nightly

Run a deployment review before publishing a saved project:

    flask --app run.py guardian-scan --trigger deployment

Only an Admin-confirmed open high or critical finding blocks the deployment command. A scan warning or unavailable scanner does not block deployment. This gate covers saved Builder projects; connect the command to a deployment pipeline only after reviewing the target environment and approval process.

## Hidden coding benchmark

Run the private-local coding quality gate after configuring both the local model and the digest-pinned sandbox:

    flask --app run.py benchmark-builder --minimum-pass-rate 70

The benchmark asks the local model for one fixed Decimal money-normalization function and runs ten hidden tests in the same restricted container. External specialists are disabled. The command prints only pass counts and the score, never the generated source or raw test output. It refuses to run if the local model, Docker image, or test-count evidence is unavailable.

## Lessons and migration

A reusable lesson may be proposed only from a patch whose restricted sandbox tests passed. The Admin review checks the sanitized title and content, then embeds the lesson into the private Admin knowledge scope only after approval and a successful 1,024-value embedding response. Rejecting a lesson does not index it. Deleting a project also removes its approved lesson chunks.

Back up the target database and apply the additive Alembic revision with:

    flask --app run.py db upgrade

Revision 20261009_33 adds owner-scoped project, patch, scan, finding, and lesson records. It tolerates fresh databases where the baseline adoption migration already created the current model tables.

Stage 14 still needs operator verification with the private inference and embedding endpoints, a digest-pinned Docker runtime, the PostgreSQL vector extension, the hidden coding-task quality benchmark, and staging Telegram delivery. Local browser and mocked tests do not prove those external services are ready.
