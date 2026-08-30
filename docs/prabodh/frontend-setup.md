# Frontend Setup

Standard local setup for `apps/web` (see the repo's own local-dev tooling for the full stack — this note only covers gaps found while working on white-labelling).

```bash
cd apps/web
bun install
bun run dev     # http://localhost:3000, requires apps/api running on :1338 and DB/Redis containers up
bun run build   # production build / type check
```

## Gaps found versus the upstream docs

- `npx learnhouse dev`'s container-detection step (`isContainerRunning` in `apps/cli/src/commands/dev.ts` / `apps/cli/src/services/docker.ts`) breaks on Windows: it runs `docker inspect --format '{{.State.Running}}' <name>` via Node's `execSync` with no explicit shell, which defaults to `cmd.exe` on Windows. `cmd.exe` doesn't strip the single quotes the way POSIX shells do, so the check always reports containers as not-running even when they are, and the CLI drops into its interactive first-run wizard. Reported as a CLI-tooling bug (outside `apps/web`, not touched this pass) — the workaround is to run `apps/api` (`uv run python app.py`) and `apps/web` (`bun run dev`) directly instead of through `npx learnhouse dev` on Windows.
- `bun install` must be run from a freshly-opened shell if Bun was installed after your terminal session started — Windows doesn't propagate a newly-added `PATH` entry into already-running processes.
