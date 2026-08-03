
#!/usr/bin/env python3

import asyncio, signal, json, logging, os, re
from pathlib import Path
from nats.aio.client import Client as NATS

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

NATS_URL = os.environ.get("NATS_URL")
SCRIPTS_DIR = Path("/scripts").resolve()
SUBJECT_PREFIX = "events."
TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]+$")

if not NATS_URL:
    raise RuntimeError("NATS_URL is not set")

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    # format="%(asctime)s %(levelname)s %(message)s",
    format="%(message)s"
)

log = logging.getLogger("herald")

# -----------------------------------------------------------------------------
# NATS callback
# -----------------------------------------------------------------------------

async def on_message(msg):
    subject = msg.subject

    script = subject_to_script(subject)

    if script is None:
        log.warning("Rejected invalid subject: %s", subject)
        return

    if not script.is_file():
        log.info("No handler for %s", subject)
        return

    await execute(script, subject, msg.data)

# -----------------------------------------------------------------------------
# Subject validation
# -----------------------------------------------------------------------------

def subject_to_script(subject: str) -> Path | None:
    """
    Convert:

        events.github.myorg.backend.push

    into:

        /scripts/github/myorg/backend/push.sh
    """

    if not subject.startswith(SUBJECT_PREFIX):
        return None

    suffix = subject[len(SUBJECT_PREFIX):]

    if not suffix:
        return None

    tokens = suffix.split(".")

    for token in tokens:
        if token in ("", ".", ".."):
            return None

        if not TOKEN_RE.fullmatch(token):
            return None

    path = SCRIPTS_DIR.joinpath(*tokens).with_suffix(".sh")

    try:
        resolved = path.resolve()
    except Exception:
        return None

    try:
        resolved.relative_to(SCRIPTS_DIR)
    except ValueError:
        return None

    return resolved


# -----------------------------------------------------------------------------
# Script execution
# -----------------------------------------------------------------------------

async def execute(script: Path, subject: str, payload: bytes) -> None:
    log.info("Executing %s", script)

    proc = await asyncio.create_subprocess_exec(
        str(script),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env={
            **os.environ,
            "EVENT_SUBJECT": subject,
        },
    )

    stdout, stderr = await proc.communicate(payload)

    if stdout:
        log.info("%s stdout:\n%s", script, stdout.decode(errors="replace"))

    if stderr:
        log.warning("%s stderr:\n%s", script, stderr.decode(errors="replace"))

    if proc.returncode == 0:
        log.info("%s completed successfully", script)
    else:
        log.error("%s exited with status %d", script, proc.returncode)

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

async def main():
    nc = NATS()

    log.info("Connecting to %s", NATS_URL)

    await nc.connect(
        servers=[NATS_URL],
        reconnect_time_wait=2,
        max_reconnect_attempts=-1,
    )

    await nc.subscribe("events.>", cb=on_message)

    log.info("Subscribed to events.>")
    log.info("Herald ready.")

    stop = asyncio.Event()

    def shutdown():
        log.info("Shutdown requested")
        stop.set()

    loop = asyncio.get_running_loop()
    loop.add_signal_handler(signal.SIGTERM, shutdown)
    loop.add_signal_handler(signal.SIGINT, shutdown)

    await stop.wait()

    log.info("Draining NATS connection...")
    await nc.drain()


if __name__ == "__main__":
    asyncio.run(main())
