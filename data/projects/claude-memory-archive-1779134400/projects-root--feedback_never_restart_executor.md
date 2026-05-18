---
name: Never restart executor container
description: Never docker compose down/restart the executor container — exec into it to start/restart services instead
type: feedback
---

Never restart or recreate the executor container (no `docker compose down`, `docker compose restart`, `docker stop`). The container runs persistent sessions and processes.

**Why:** Restarting kills all running processes, sessions, and state inside the container. Sam starts services from within the container.

**How to apply:** To start/restart services, use `docker exec specdocv2-executor <command>` to run commands inside the existing container. To fix port mappings, update the compose file and flag it — Sam will decide when to recreate.
