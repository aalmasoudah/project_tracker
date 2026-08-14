# Phase 21 Local LM Studio Runbook

## Purpose / الغرض

This runbook operates the approved local-development LM Studio provider for
Insight Tracker. It can be selected directly for Phase 15 briefings or the
Project Recovery Agent, and it can serve as the controlled fallback from Groq
for Telegram report summaries, Telegram executive questions, and Recovery
Agent decisions.

هذا الدليل يشغّل مزود LM Studio المحلي المعتمد لبيئة التطوير. يمكن اختياره
مباشرة للموجز الذكي أو وكيل تعافي المشروع، كما يمكن استخدامه كبديل مضبوط من
Groq لتقارير وأسئلة تيليجرام ووكيل التعافي.

LM Studio is user-operated and is not a Docker Compose service. Staging and
production remain Groq-only. The local API must never be exposed to a phone,
LAN, n8n, Telegram, Cloudflare tunnel, reverse proxy, or public internet.

LM Studio خدمة يديرها المستخدم وليست جزءًا من Docker Compose. بيئتا Staging
وProduction تستمران باستخدام Groq فقط، ولا يجوز كشف المنفذ المحلي للشبكة أو
الجوال أو n8n أو تيليجرام أو أي نفق عام.

## Fixed Security Contract / عقد الأمان الثابت

- Base URL: `http://127.0.0.1:1234/v1` exactly.
- Logical model code: exactly one of `qwen/qwen3.5-9b` or
  `openai/gpt-oss-20b`.
- `LM_STUDIO_MODEL_ID`: the exact installed/loaded API identifier returned by
  `/v1/models`; it is separate from the logical code.
- CORS is off. Never add `--cors` to the server command.
- MCP and model-controlled tools are off. Insight Tracker sends no tool to LM
  Studio and grants it no database, filesystem, shell, web, or credential
  access.
- Effective model parallelism is one.
- `LM_STUDIO_REASONING_EFFORT` is sent on every local request. It accepts
  `none`, `low`, `medium`, or `high`; the approved Qwen model requires `none`.
- Optional local bearer authentication uses only `LM_STUDIO_API_TOKEN` in the
  ignored `.env`. Never print, paste, commit, or include the token in a command
  transcript.
- Django independently validates strict JSON Schema, citations, identifiers,
  permissions, and scope. Any reasoning field is discarded.
- Startup and readiness commands never download a model.

بالعربي: الرابط والنموذج والصلاحيات ثابتة. النموذج لا يدخل قاعدة البيانات؛
Django يرسل له بيانات محدودة فقط ثم يتحقق من JSON والمراجع والصلاحيات محليًا.
لا تستخدم CORS أو MCP، ولا تعرض السر في الشاشة أو Git.

## 1. Verify the Existing Installation / التحقق من التثبيت

LM Studio is already installed on the local Windows computer. From PowerShell
in the repository root, locate the CLI without changing system configuration:

```powershell
$lmStudioCli = (Get-Command lms -ErrorAction SilentlyContinue).Source
if (-not $lmStudioCli) {
    $lmStudioCli = "$env:USERPROFILE\.lmstudio\bin\lms.exe"
}
if (-not (Test-Path -LiteralPath $lmStudioCli)) {
    throw "LM Studio CLI was not found. Open the installed LM Studio app once."
}
& $lmStudioCli --help
```

Do not install another copy if this succeeds. Do not run an installer from an
unreviewed URL.

إذا ظهر دليل أوامر `lms` فالتثبيت موجود ولا تحتاج تثبيت نسخة أخرى.

## 2. Select or Install an Approved Model / اختيار النموذج المعتمد

First list the models already on disk:

```powershell
& $lmStudioCli ls --llm
```

The current machine already has `qwen/qwen3.5-9b` Q4_K_M. Its live Arabic and
English strict JSON Schema probe passed with a 32,768-token loaded context,
parallelism one, and reasoning effort `none`. Use its real identifier without
a gpt-oss alias:

```text
qwen/qwen3.5-9b
```

`openai/gpt-oss-20b` is also on the approved logical allowlist but is not
currently installed. If the operator later chooses it, the following explicit
command starts the large download:

```powershell
& $lmStudioCli get openai/gpt-oss-20b
```

That is the only step in this runbook that downloads model weights. Review the
displayed artifact, quantization, disk requirement, and source before
confirming it. The application launcher and readiness probe never execute this
command. A matching name is not enough: the chosen artifact must still pass
the Phase 21 capability gate.

إذا لم يكن النموذج موجودًا، أمر `lms get` هو خطوة تنزيل صريحة وكبيرة. راجع
الحجم والإصدار قبل الموافقة. التطبيق نفسه لا ينزّل أي نموذج.

Obtain/confirm the exact model key:

```powershell
& $lmStudioCli ls --llm --json
```

For the current Qwen artifact, configure both logical code and exact model ID
as `qwen/qwen3.5-9b`. For a later gpt-oss artifact, copy its real exact model
key without aliasing it as another model. Do not copy the full command output
into a ticket or commit it; it may disclose unrelated installed model names.

## 3. Configure the Ignored Local Environment / إعداد `.env`

Keep these values in the repository's ignored `.env`, not in source:

```dotenv
LM_STUDIO_BASE_URL=http://127.0.0.1:1234/v1
LM_STUDIO_MODEL_CODE=qwen/qwen3.5-9b
LM_STUDIO_MODEL_ID=qwen/qwen3.5-9b
LM_STUDIO_REASONING_EFFORT=none
LM_STUDIO_API_TOKEN=
LM_STUDIO_FALLBACK_ENABLED=false
LM_STUDIO_TIMEOUT_SECONDS=180
LM_STUDIO_CONTEXT_LENGTH=32768
LM_STUDIO_CONTEXT_TOKEN_RESERVE=512
```

`LM_STUDIO_MODEL_CODE` is the stable allowlist and persisted model code.
`LM_STUDIO_MODEL_ID` is the exact server identifier used in the request body.
They are intentionally separate and neither is inferred from user input.

The accepted timeout range is 10 through 600 seconds. Context length is 4,096
through 131,072 tokens. The context reserve must be at least 128 and smaller
than the context length. The general code default is 16,384; the shown 32,768
is the successfully gated Qwen configuration on this machine. Each feature's
existing output ceiling still applies; transport reduces `max_tokens` so the
estimated input plus reserve plus output stays within the local context.

`LM_STUDIO_REASONING_EFFORT` accepts `none`, `low`, `medium`, or `high` and is
sent on every local completion. Qwen requires exactly `none`; any other value
fails Django/readiness configuration. The live probe showed that other Qwen
reasoning modes can consume the output budget before producing the required
JSON. A future gpt-oss artifact still requires its own gated setting.

Leave `LM_STUDIO_API_TOKEN` empty only when LM Studio local authentication is
off. If authentication is enabled in LM Studio, place the matching token here
without quoting or printing it. Authentication never permits a non-loopback
binding.

## 4. Manual Server and Model Startup / التشغيل اليدوي

The one-click launcher normally performs these non-download actions when a
local provider or fallback is configured. For manual diagnosis, use the exact
commands below:

```powershell
& $lmStudioCli server start --port 1234 --bind 127.0.0.1
& $lmStudioCli load 'qwen/qwen3.5-9b' `
    --identifier 'qwen/qwen3.5-9b' `
    --context-length 32768 `
    --parallel 1 `
    --yes
& $lmStudioCli server status
& $lmStudioCli ps --json
```

This exact command matches the installed, gated Qwen artifact. For a future
approved artifact, replace both ID arguments and the local environment with
that artifact's real, gated values. `lms load` loads an already installed
artifact; it does not download one. Do not add `--cors`, bind `0.0.0.0`, use a
LAN address, or give Qwen a deceptive gpt-oss identifier.

للتشغيل الآمن استخدم `127.0.0.1` فقط، ومعامل `--parallel 1`. أمر `load` يحمل
النموذج الموجود في الذاكرة ولا ينزله من الإنترنت.

## 5. Readiness and Capability Gate / فحص الجاهزية والقدرات

Use the repository probe. It reads the safe local settings, rejects redirects,
non-loopback endpoints, a CORS response header, missing/mismatched model IDs,
and unsafe configuration. It may send the optional bearer token but never
prints it.

Readiness and exact `/v1/models` ID check:

```powershell
uv run python -m scripts.lm_studio_readiness
```

Explicit bilingual strict-JSON gate with a bounded readiness wait:

```powershell
uv run python -m scripts.lm_studio_readiness --strict-json --wait-seconds 120
```

If using the existing virtual environment without `uv`, the equivalent is:

```powershell
.\.venv-phase1\Scripts\python.exe -m scripts.lm_studio_readiness --strict-json --wait-seconds 120
```

Do not enable local inference if either command fails. The strict probe is a
smoke gate, not the full application evaluation: run the Phase 21 automated
tests and the feature-specific fictional-data checks before relying on the
model.

إذا فشل فحص الجاهزية أو JSON فلا تفعل المزود المحلي. أصلح تشغيل LM Studio أو
رقم النموذج ثم أعد الفحص؛ لا تخفف Schema ولا تقبل JSON جزئيًا.

## 6. Enable One Local Mode / تفعيل الوضع المطلوب

Restart Django and Celery after changing `.env`. Enable only the mode being
tested.

### Direct local Phase 15 briefing

```dotenv
AI_BRIEFING_ENABLED=true
AI_BRIEFING_PROVIDER=lm_studio
AI_BRIEFING_MODEL=qwen/qwen3.5-9b
LM_STUDIO_FALLBACK_ENABLED=false
```

Generate one Arabic and one English briefing using fictional data. Open every
citation. Enabling the fallback flag alone never silently changes a Phase 15
Groq briefing to local inference.

### Direct local Recovery Agent

```dotenv
PROJECT_AGENT_ENABLED=true
PROJECT_AGENT_PROVIDER=lm_studio
PROJECT_AGENT_DEFAULT_MODEL=qwen/qwen3.5-9b
LM_STUDIO_FALLBACK_ENABLED=false
```

Use fictional data and verify the existing multi-tool, proposal, human
approval, idempotent execution, and cited verification workflow.

### Groq-primary Telegram and Recovery fallback

```dotenv
AI_BRIEFING_ENABLED=true
AI_BRIEFING_PROVIDER=groq
PROJECT_AGENT_ENABLED=true
PROJECT_AGENT_PROVIDER=groq
LM_STUDIO_FALLBACK_ENABLED=true
```

Keep the existing Groq key and feature settings in the ignored environment.
Telegram reports/assistant and Recovery use Groq first. They make at most one
local transition after an eligible transient timeout, connection failure,
rate limit, or provider 5xx. Recovery persists the local provider/model before
the first local request, after its safety rechecks; Telegram keeps the selected
local pair for the rest of the request. Retries never return to Groq.

No fallback occurs for authentication/configuration, HMAC/chat/role,
permission/scope, unsafe input or prompt injection, schema/citation, quota or
token/step/time budget, cancellation, stale/duplicate state, or a business-
rule error. If local inference is unavailable or invalid, the existing safe
failure is final; there is no switch back or provider oscillation.

## 7. One-Click Launcher Behavior / سلوك ملف التشغيل

`START_INSIGHT_TRACKER.cmd` reads process environment first and named values
from the ignored `.env`. It treats local AI as requested only when at least one
of these is true:

- `LM_STUDIO_FALLBACK_ENABLED=true`;
- `AI_BRIEFING_PROVIDER=lm_studio`;
- `PROJECT_AGENT_PROVIDER=lm_studio`.

When requested, the launcher:

1. finds `lms` on `PATH` or at
   `%USERPROFILE%\.lmstudio\bin\lms.exe`;
2. starts `lms server start --port 1234 --bind 127.0.0.1` without CORS;
3. verifies that no non-loopback listener is used;
4. loads a missing exact ID with
   `lms load <LM_STUDIO_MODEL_ID> --identifier <LM_STUDIO_MODEL_ID>
   --context-length <LM_STUDIO_CONTEXT_LENGTH> --parallel 1 --yes`;
5. waits at most 45 seconds for the server, 300 seconds for load, and 120
   seconds for exact readiness;
6. sends an optional bearer token without printing it and rejects redirects or
   a CORS response header.

The launcher never calls `lms get`. If local startup fails, it sets fallback
off for that launch. If Phase 15 or Phase 17 explicitly selected LM Studio, it
disables that feature for that launch, then continues the non-local application
and Groq-primary stack. Review the safe launcher/log message, correct LM
Studio, and restart; do not weaken endpoint or model validation.

بالعربي: إذا تعطل النموذج المحلي سيكمل البرنامج الأساسي وGroq، ويعطّل المسار
المحلي مؤقتًا لذلك التشغيل فقط. راجع الخطأ ثم أصلحه وأعد تشغيل الملف.

## 8. Safe Verification / الاختبار الآمن

Use fictional records and complete these checks:

1. Run both readiness commands and confirm the exact model ID and Arabic/
   English strict JSON pass without a secret in output. For Qwen, confirm
   `LM_STUDIO_REASONING_EFFORT=none`.
2. Use direct local Phase 15 and inspect both languages and every citation.
3. Use direct local Recovery and verify two observations, proposal pause,
   human decision, execution checks, and final citation.
4. Run the automated fallback tests that simulate timeout, connection, rate
   limit, and 5xx. Verify one transition and one result.
5. Run negative tests for bad authentication/configuration, permission, prompt
   injection, malformed schema, forged citation, and exhausted budget. Verify
   zero fallback calls.
6. Run the existing Telegram `/help`, `/tasks`, `/overdue`, `/attendance`,
   `/last`, a standalone Arabic question, and an English question. Confirm no
   command, PDF, alert, idempotency, or privacy regression.
7. For a live fallback drill, use only fictional data and a reversible local
   test network control that produces a connection/timeout failure. Never
   corrupt or print a real Groq key: an invalid key is an authentication error
   and correctly must not fallback.
8. Inspect safe metrics/logs for provider/model code, transition reason, and
   usage only. They must not contain prompts, questions, evidence, answers,
   reasoning, raw errors, chat IDs, tokens, or credentials.

Local requests run with effective concurrency one. Parallel Telegram and web
requests should queue and must not create duplicate answers, PDFs, proposals,
executions, or notifications.

## 9. Troubleshooting / حل المشاكل

- **`lms` not found:** open the installed LM Studio app once, then retry the
  discovery command. Do not install another copy automatically.
- **Model missing in `lms ls`:** explicitly download the approved artifact or
  correct `LM_STUDIO_MODEL_ID`; the launcher will not download it.
- **Model absent from `/v1/models`:** load the exact installed key with the
  exact same `--identifier`, then rerun readiness.
- **Readiness reports redirect, CORS, or non-loopback:** stop the server and
  restart it with the exact command in section 4. Do not add a host exception.
- **401 from LM Studio:** configure the matching optional token in the ignored
  `.env`; never print it while diagnosing.
- **Strict JSON failure:** keep local inference disabled. Confirm the approved
  artifact and context, then rerun the full capability gate. Do not strip
  fences or repair/drop fields.
- **Slow response or memory pressure:** keep parallelism one. The live Qwen gate
  used 32,768 context; a reviewed lower context may be evaluated without
  raising feature budgets. Stop other local model loads and retry the gate.
- **Qwen reaches length without JSON:** confirm
  `LM_STUDIO_REASONING_EFFORT=none`. Do not accept reasoning content as the
  answer or raise the output ceiling to compensate.
- **Telegram did not fallback:** verify the error is an eligible transient
  class. Auth, configuration, security, validation, and budget errors are
  intentionally ineligible.
- **Local fails after Recovery transition:** the run fails safely and cannot
  return to Groq. Start a fresh run only after readiness passes again.

## 10. Disable and Roll Back / التعطيل والرجوع

Restore Groq primary and disable fallback in the ignored `.env`:

```dotenv
AI_BRIEFING_PROVIDER=groq
PROJECT_AGENT_PROVIDER=groq
LM_STUDIO_FALLBACK_ENABLED=false
```

Restart Django/Celery, then stop only the local API if it is no longer needed:

```powershell
& $lmStudioCli server stop
```

Stopping the server does not delete the model. Do not delete model files,
database rows, AI requests, proposals, verification steps, provider transition
metadata, audit evidence, or n8n data during rollback. All non-AI application
features continue normally.

للتعطيل اجعل fallback بقيمة `false` وأعد اختيار Groq ثم أعد تشغيل Django و
Celery. إيقاف السيرفر لا يحذف النموذج أو بيانات المشروع.
