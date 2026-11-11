# Copilot review instructions

Follow [AGENTS.md](../AGENTS.md) in the repository root.

## Language

Write review comments in English. Deliverables (commits, PRs, code comments, docs) are English; runtime messages are English.

## Review checklist

- `flake8` (the command in `.github/workflows/ci.yml`) passes.
- Commit messages and PR titles follow Conventional Commits.
- No secrets are hard-coded or logged (`DISCORD_TOKEN`, channel ID).
- Failures of `systemctl` and Discord API calls are not silently swallowed.
- Changes to `notified_ids.json` handling do not cause duplicate or missing notifications.
- `README.md` and `AGENTS.md` still match the code.

## Known false positives (do not flag)

- No automated tests exist; do not require new test files.
- `subprocess` with `shell=True` is used with a fixed `systemctl` command line; flag it only if user input reaches the shell.
- The tool targets Linux with systemd only; missing cross-platform support is intentional.
