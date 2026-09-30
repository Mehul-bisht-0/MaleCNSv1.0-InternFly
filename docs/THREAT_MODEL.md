# Threat model

## High-value assets

Profile facts, credentials, approval decisions, provider tokens, event history,
and host integrity.

## Trust boundaries

- Browser to control API.
- Orchestrator to model/job providers.
- Orchestrator to restricted runner.
- Application database to backups/archives.

## MVP controls

- Offline mode is the default and has no job-provider connector.
- The code runner is a separate non-root container with a read-only root,
  dropped capabilities, process/memory/CPU limits, and an internal-only network.
- Static AST policy rejects imports and dangerous built-ins before execution.
- Draft approval binds an exact SHA-256 content hash.
- Approval never means submission; no submission connector exists.
- State-changing commands and approvals append audit events.

The local non-container runner is a deterministic fake and refuses unknown code.
Do not set an unsafe host-execution escape hatch in production.

