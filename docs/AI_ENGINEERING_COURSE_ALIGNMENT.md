# AI Engineering Daily Plan Alignment

Source reviewed: `AI_Engineering_Daily_Plan.pdf`, 7 weeks, 35 sessions.

Status terms:

- **Supported**: the repository provides the implementation or artifact needed
  for the exercise.
- **Exercise evidence required**: the project supports the task, but a trainee
  must still execute and record the requested comparison or reflection.
- **Adapted**: the learning outcome is supported with a safer engineering
  equivalent.
- **Phase 16/17**: the separately approved Telegram automation and project
  agent artifacts provide the integration/agent evidence.

| Week/day | Daily task | Project alignment |
| --- | --- | --- |
| 1/1 | Environment and first LLM API call | Supported by the Groq provider, `.env.example`, and Phase 15 runbook; a live key is required for the trainee's recorded call. |
| 1/2 | Five-prompt comparison | Exercise evidence required; use the fake provider for structure and Groq staging for output comparison. |
| 1/3 | AI development workflow map | Supported: User -> Django form -> evidence selectors -> Celery -> Groq -> validation -> briefing UI. |
| 1/4 | Four prompt patterns | Adapted: versioned system/role and strict structured-output prompting are implemented; private chain-of-thought is not requested or stored. |
| 1/5 | Prompt-only mini-project | Exercise evidence required; briefing prompt/evaluation can be presented without changing code. |
| 2/1 | One-page software specification | Supported by `docs/PHASES/PHASE_15_AI_PROJECT_BRIEFINGS.md`. |
| 2/2 | First AI-paired application | Supported by the running Django application and Phase 15 feature. |
| 2/3 | Review AI-written code | Supported by Ruff, mypy, tests, migration review, and Git diff review; trainee annotations remain evidence. |
| 2/4 | Introduce/debug three bugs | Exercise evidence required; use a disposable branch and never weaken production tests. |
| 2/5 | Ship and reflect | Supported by the Git/CI workflow; trainee reflection remains evidence. |
| 3/1 | Structured Markdown | Supported across the requirements, ADR, phase, runbook, and verification documents. |
| 3/2 | Context engineering document | Supported by `AGENTS.md` plus the ordered requirements set. |
| 3/3 | Precise coding specification | Supported by the 18-section phase specification. |
| 3/4 | README and system instructions | Supported by `README.md`, `AGENTS.md`, prompts, and runbook. |
| 3/5 | Test and revise specification | Supported by acceptance traceability and the automated quality gate. |
| 4/1 | Analyze Claude Skills | Exercise evidence required; not an application runtime feature. |
| 4/2 | Execute existing Claude Skills | Exercise evidence required in a Claude-enabled training environment. |
| 4/3 | Design `SKILL.md` | Supported by the standalone safe design in `skills/insight-project-agent/SKILL.md`. |
| 4/4 | Implement custom Claude Skill | Supported: the Phase 17 skill has Arabic/English examples, a safe trigger, no credential, and no approval bypass. |
| 4/5 | Chain and peer-review skills | Exercise evidence required; validate the skill and review it against Phase 17 acceptance without granting runtime permission. |
| 5/1 | Design an agent | Supported by Phase 17's goal, state machine, strict planner loop, permissions, HITL, and verification design. Phase 15 remains deliberately non-agentic. |
| 5/2 | Single-tool agent | Adapted: each of the seven Phase 17 read tools can be evaluated alone, while a successful production run requires two distinct tools. |
| 5/3 | Tools and memory | Supported by exact read/proposal allowlists and reviewed same-project persistent memory. |
| 5/4 | Planning/decomposition | Supported by a stored bounded plan and observation-dependent dynamic tool selection. |
| 5/5 | Failure modes/guardrails | Supported across Phase 15 and Phase 17 with strict schemas/citations, access rechecks, exclusions, retries, budgets, HITL, stale/expiry checks, idempotency, and verification. |
| 6/1 | Scheduled n8n workflow | Phase 16 Telegram/n8n integration. |
| 6/2 | Connect two APIs | Phase 16: signed Django API plus Telegram API through n8n. |
| 6/3 | Chained AI workflow | Supported by Phase 16's fixed Telegram flow and Phase 17's minimized reviewed-event claim/checkpoint/callback flow. |
| 6/4 | Error handling and human checkpoint | Supported: Phase 16 binds CEO/chat; Phase 17 validates HMAC/replay and pauses at an explicit n8n human checkpoint. |
| 6/5 | Document summary/store/notify | Supported: Phase 17 emits only a reviewed minimized summary/cited outcomes for a human-selected safe notification/archive result. |
| 7/1 | Complete proposal | Supported by the approved Phase 15, 16, and 17 specifications, ADRs, threat boundaries, and runbooks. |
| 7/2 | Core prototype | Phase 15 briefing, Phase 16 Telegram reporting, and Phase 17 recovery-agent prototypes are implemented. |
| 7/3 | Skill and n8n integration | Supported by `skills/insight-project-agent/` and `deploy/n8n/insight_project_agent_reviewed.json`. |
| 7/4 | Test and evaluate | Supported by unit, PostgreSQL integration, security, n8n static/HMAC, Arabic/English, and Playwright mobile acceptance tests. |
| 7/5 | Live demo and write-up | Supported after final verification; use fictional data and the deterministic provider when a live key is unsuitable. |

## Phase 16 Boundary Identified From the Course

The requested CEO Telegram bot and n8n orchestration cover the remaining
agentic/automation outcomes. They must remain outside Phase 15 because they add
an external delivery channel and tool execution. The safe proposed boundary is
CEO-only account linking, fixed report commands, aggregate attendance, signed
n8n callbacks, Django-owned authorization/PDF generation, no direct n8n
database access, and no personal trainee data sent to Telegram without an
explicit privacy decision.

## Phase 17 Agentic Course Deliverable

Phase 17 closes the remaining agent-design, tools, reviewed memory,
planning/decomposition, human-in-the-loop execution, custom-skill, and signed
n8n checkpoint outcomes without weakening Phase 15. Its provider chooses only
strict allowlisted decisions; Django owns authorization, tools, proposals,
execution, and verification. The course skill is an inspectable artifact, not
a hidden runtime dependency, and the inactive n8n export carries only a
minimized reviewed summary through signed replay-protected endpoints.
