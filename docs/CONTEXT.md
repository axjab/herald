
# Herald Context Handoff

You are an expert in NATS, Docker, Linux systems administration, and event-driven infrastructure. You are assisting with the design and implementation of Herald.

## Environment

This is a small, non-enterprise, self-hosted environment.

The goal is to replace a webhook-driven automation architecture with an event-driven architecture.

## Overall Architecture

Current design:

- One host is designated as the central NATS server.
- A WAN-facing webhook gateway receives external events and publishes them into NATS.
- Multiple hosts and local daemons subscribe remotely to NATS.
- Tailscale is used as the private network layer.
- NATS should only be reachable over Tailscale.
- Remote clients connect using Tailscale MagicDNS names.

Example:

```
nats://firelink:4222
```

The NATS server deployment should:

- Avoid public exposure.
- Bind only to the private Tailscale network.
- Use NATS authentication and subject permissions.
- Start only after Tailscale is available.

The intended systemd relationship is:

```
tailscaled.service
        |
        v
Herald/NATS-dependent services
```

Application-level services should depend on `tailscaled.service` rather than modifying Docker globally.

---

# Herald Responsibility

Herald is a local event consumer/dispatcher daemon.

Each host runs its own Herald instance.

Herald responsibilities:

1. Connect to NATS.
2. Subscribe to event subjects.
3. Convert subjects into local script paths.
4. Execute matching automation scripts.
5. Pass event payload data safely to scripts.
6. Log execution results.

Herald does not know about specific publishers.

Herald only knows:

```
NATS subject -> local script path
```

---

# Subject-to-Script Routing Model

Herald intentionally follows the same model as webhookd.

Webhook model:

```
POST /github/repository/push

maps to:

/scripts/github/repository/push.sh
```

Herald model:

NATS subject:

```
events.github.myorg.backend.push
```

maps to:

```
/scripts/github/myorg/backend/push.sh
```

Mapping algorithm:

1. Remove the `events.` prefix.
2. Split the remaining subject by `.`.
3. Convert tokens into directories.
4. Append `.sh`.

Example:

```
events.github.myorg.backend.push

becomes:

/scripts/github/myorg/backend/push.sh
```

Another example:

```
events.github.myorg.frontend.push

becomes:

/scripts/github/myorg/frontend/push.sh
```

---

# Configuration Philosophy

Do NOT maintain a central subject mapping file.

No:

```
subjects.yaml
```

containing:

```
events.github.myorg.backend.push:
    script: deploy_backend.sh
```

Instead:

The filesystem itself is the routing table.

A script existing means the event is handled.

A script missing means the event is ignored.

This follows:

```
convention over configuration
```

Adding automation:

```
create script
```

Removing automation:

```
remove script
```

No additional registration step.

---

# Safety Model

Unknown events are ignored.

Example:

A NATS message arrives:

```
events.github.some-new-repository.push
```

Herald checks:

```
/scripts/github/some-new-repository/push.sh
```

If it does not exist:

```
log: no handler found, ignoring
```

No execution occurs.

---

# Optional Per-Script Configuration

A future enhancement may allow optional sidecar configuration files.

Example:

```
/scripts/github/myorg/backend/push.sh

/scripts/github/myorg/backend/push.yaml
```

Example:

```yaml
enabled: true
timeout: 30
lock: true
```

Rules:

- Configuration belongs next to the script.
- No global configuration registry.
- Defaults should be safe.

Possible defaults:

```
enabled: true
timeout: unlimited
lock: false
```

A script-specific configuration file overrides defaults only for that script.

---

# Payload Handling

Do not pass event payloads through command-line arguments.

Avoid:

```
script.sh '{"repository":"foo"}'
```

Reason:

Arguments may be visible through process listings.

Preferred:

Pass structured JSON through stdin.

Example:

Script execution:

```
/scripts/github/myorg/backend/push.sh
```

stdin:

```json
{
  "repository": "myorg/backend",
  "ref": "refs/heads/main",
  "commit": "abc123"
}
```

Environment variables may contain simple metadata:

Example:

```
EVENT_SUBJECT=events.github.myorg.backend.push
```

Do not pass arbitrary shell commands or evaluated content.

---

# Security Requirements

Herald must:

- Validate subject names.
- Prevent path traversal.
- Reject subjects containing:
  - `..`
  - absolute path components
  - invalid filesystem characters if necessary

The calculated script path must never escape the configured scripts directory.

Example:

Allowed:

```
events.github.myorg.backend.push
```

Rejected:

```
events.github.../../../etc/passwd
```

---

# Example Execution Flow

Incoming NATS message:

Subject:

```
events.github.myorg.backend.push
```

Payload:

```json
{
  "repository": "myorg/backend",
  "ref": "refs/heads/main",
  "commit": "abc123"
}
```

Herald:

1. Receives NATS message.
2. Calculates:

```
/scripts/github/myorg/backend/push.sh
```

3. Checks if script exists.
4. Loads optional:

```
/scripts/github/myorg/backend/push.yaml
```

5. Executes script.

Script receives:

stdin:

```json
{
  "repository": "myorg/backend",
  "ref": "refs/heads/main",
  "commit": "abc123"
}
```

environment:

```
EVENT_SUBJECT=events.github.myorg.backend.push
```

---

# Subject Design Guidance

Subjects should remain hierarchical.

Examples:

Global event:

```
events.github.myorg.backend.push
```

Potential future host-specific event:

```
events.firelink.github.myorg.backend.push
```

Host-specific routing may be introduced later if needed.

Avoid using the NATS wildcard subscription model (`>`) as the only routing mechanism without local filtering.

Herald may subscribe broadly, but execution is always controlled by:

1. Subject-to-path mapping.
2. Script existence.
3. Optional local configuration.

---

# Implementation Philosophy

Prefer:

- Simple Linux-native solutions.
- Predictable behavior.
- Clear logging.
- Minimal dependencies.
- Docker/systemd conventions.
- Operational simplicity.

Avoid:

- Enterprise abstractions.
- Complex registries.
- Dynamic service discovery.
- Central configuration databases.

Herald should remain a small, reliable daemon.

---

# Next Task

Implement Herald's NATS subscriber and dispatcher logic based on this architecture.
