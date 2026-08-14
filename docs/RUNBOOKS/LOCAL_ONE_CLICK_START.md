# Local One-Click Startup

## Purpose

Double-click `START_INSIGHT_TRACKER.cmd` in the repository root to restart the
complete local demonstration stack without copying secrets into the script or
printing them in the terminal.

The launcher:

1. Starts Docker Desktop when necessary.
2. Starts PostgreSQL and Redis through Docker Compose.
3. Starts the existing n8n webhook proxy and Cloudflare quick tunnel.
4. Verifies that the temporary tunnel is publicly reachable, restarts a stale
   tunnel when necessary, detects its replacement URL, and recreates only the
   n8n container while preserving its `insight_n8n_data` volume, credentials,
   and workflows.
5. Stops earlier workspace-owned Django and Celery processes to avoid
   duplicates.
6. Applies Django migrations and system checks.
7. Starts Django on `0.0.0.0:8000`, one Celery worker, and one Celery Beat.
8. When LM Studio fallback or an explicit local provider is configured, finds
   the existing `lms` CLI, starts only `127.0.0.1:1234`, loads the already
   installed exact model ID with parallelism one, and performs bounded
   readiness checks. It never downloads a model or enables CORS.
9. Detects the current hotspot/LAN IPv4 address, verifies Django, n8n, the
   public tunnel, and the published Telegram and reviewed-agent workflows,
   prints the tracker, phone, n8n, and tunnel URLs, and opens the local pages.

## Requirements

- The repository remains in its current directory with `.venv-phase1` and the
  ignored local `.env` file.
- Docker Desktop is installed.
- The initial n8n setup has already created these protected containers:
  `insight-n8n-local`, `insight-n8n-webhook-proxy`, and
  `insight-cloudflared-quick`.
- The n8n container retains its Telegram credential and the required chat and
  HMAC environment values. The launcher reads them into the child processes
  but never prints or writes their values.
- The launcher generates a separate random project-agent HMAC secret on first
  use, retains it only under ignored `tmp/runtime/`, and synchronizes the same
  value into the n8n container and the local Django/Celery child processes.
- Phase 21 local inference additionally requires the user-installed LM Studio
  CLI and an explicitly downloaded approved model. Configure the exact
  loopback/model values in the ignored `.env` and pass
  `python -m scripts.lm_studio_readiness --strict-json --wait-seconds 120`
  before relying on local results. See
  `docs/RUNBOOKS/PHASE_21_LOCAL_LM_STUDIO.md`.

## Phone Access

Connect the laptop to the phone hotspot before using the launcher. It prints a
phone URL such as `http://172.20.10.3:8000/`.

If Windows Firewall blocks the phone, right-click
`START_INSIGHT_TRACKER.cmd`, choose **Run as administrator** once, and approve
the prompt. The launcher then creates or updates one inbound TCP-8000 rule
scoped to the current local subnet, which supports home Wi-Fi and phone
hotspots. Some phone hotspots isolate connected
devices; in that case use a normal Wi-Fi network or a separately approved HTTPS
application tunnel.

## Logs and Failure Handling

Runtime logs and process ID files are stored under `tmp/runtime/`. The launcher
does not delete database volumes, n8n data, credentials, workflows, protected
records, or application uploads. If any required container or persistent n8n
volume is missing, it stops instead of attempting a new insecure setup.

If the tunnel container is running but its temporary address no longer resolves
or accepts HTTPS, the launcher now restarts only that container and waits for a
new reachable address before updating n8n. It also stops with a clear message
when either required n8n workflow is not published instead of reporting a
false successful startup.

If requested local inference is unavailable or unsafe, the launcher disables
fallback for that launch. An explicitly local Phase 15 or Phase 17 feature is
also disabled for that launch, while the non-local application and Groq-primary
stack continue. It never weakens loopback/model checks or downloads a model to
recover automatically.
