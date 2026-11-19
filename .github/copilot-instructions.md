# Copilot review instructions

Follow [AGENTS.md](../AGENTS.md) in the repository root.

## Language

Write review comments in English. Deliverables (commits, PRs, code comments, docs) are English; runtime messages are English.

## Review checklist

- `flake8` (the command in `.github/workflows/ci.yml`) passes.
- `python3 -m pytest` passes after installing `requirements-dev.txt`; CI currently runs only `flake8`.
- Commit messages and PR titles follow Conventional Commits.
- No secrets are hard-coded or logged (`DISCORD_TOKEN`, channel ID).
- Failures of `systemctl` and Discord API calls are not silently swallowed.
- Changes to `notified_ids.json` handling do not cause duplicate or missing notifications.
- A service's journal or notification failure does not prevent later failure and recovery checks, unsuccessful notifications remain pending, and the process returns a nonzero result when work remains unsuccessful.
- Discord retries are bounded and honor rate-limit responses.
- `README.md` and `AGENTS.md` still match the code.

## Known false positives (do not flag)

- `subprocess` with `shell=True` is used with a fixed `systemctl` command line; flag it only if user input reaches the shell.
- The tool targets Linux with systemd only; missing cross-platform support is intentional.
