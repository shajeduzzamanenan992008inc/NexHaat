# NexHaat Copilot Specialist Agents

All agents follow `.github/copilot-instructions.md`. Start with read-only inspection,
give each agent a bounded scope, and require evidence in its report.

| Agent | Use it for |
|---|---|
| `dependency-guardian` | Dependency inventory, alerts, update PRs, supply-chain compatibility |
| `security-architect` | Threat modeling, application security, security design review |
| `quality-engineer` | Test strategy, regression analysis, acceptance evidence |
| `architecture-reviewer` | Modules, system boundaries, architecture decision records |
| `release-guardian` | Release readiness, migration/rollback, deployment review |
| `database-steward` | Schema, migrations, data integrity, tenant isolation, recovery |
| `performance-reliability` | Profiling, reliability, capacity evidence, observability |
| `ai-safety` | LLM, prompt injection, RAG, MCP, model/tool governance |
| `api-identity` | API contracts, authentication, authorization, webhook security |

## Recommended coordination
1. Main Copilot session owns task scope and integration.
2. REA maps current source and affected dependencies.
3. One or two relevant specialists review the change in parallel when useful.
4. Quality Engineer identifies tests; Security Architect reviews relevant trust boundaries.
5. Release Guardian reviews only when release/deployment is in scope.
6. Main session reconciles findings, implements the bounded change, runs tests, and
   reports evidence.

Do not ask every agent to review every task. Avoid duplicated analysis and token cost.
External REA/MCP agents must receive the instructions explicitly unless automatic
loading is verified.
