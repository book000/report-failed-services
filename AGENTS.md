# AGENTS.md

Guidance for AI coding agents and contributors. `CLAUDE.md` imports this file, and `.github/copilot-instructions.md` adds the review checklist.

## Language

- All deliverables are written in **English**: commit messages, PR/Issue titles and bodies, review comments, code comments and docstrings, and documentation (`README.md`, `AGENTS.md`, etc.).
- Exceptions (keep as is): quotations, technical identifiers, generated files, and external source text.
- Runtime messages (logs, errors) are English.
- Do not rewrite Git history to change the language of past commits.

## Overview

`report-failed-services` is a Python tool for Linux with systemd. It lists failed services with `systemctl`, posts each newly failed service to a Discord channel through the Bot API (with the last journal lines), and posts a recovery message when a notified service is no longer failed. A systemd timer runs it every 30 minutes.

## Commands

```bash
pip install -U -r requirements.txt   # install dependencies
python3 -m src                        # run locally (needs .env, systemctl and journalctl)
flake8 . --count --select=E1,E2,E3,E4,E7,E9,W1,W2,W3,W4,W5,F63,F7,F82 --show-source --statistics
```

CI (`.github/workflows/ci.yml`) only runs the `flake8` command above. There are no automated tests; verify behavior manually on a systemd host.

## Structure

- `src/__main__.py`: main logic. Runs `systemctl list-units --failed`, skips ignored and already notified services, sends a failure embed, and sends a recovery embed for notified services that are no longer failed.
- `src/__init__.py`: shared helpers (`init_logger`, `send_to_discord`, notified-ID and ignore-list file access).
- `src/config.py`: loads `.env` and exposes `DISCORD_TOKEN` and `DISCORD_CHANNEL_ID`; exits if either is missing.
- `SystemdFiles/`: service and timer units plus `install-systemd.sh`, which rewrites the tracked `.service` file in place (do not commit that change). The service runs `venv/bin/python -m src` as root, so the installation needs a `venv` in the repository root.

## State and configuration

- `.env`: `DISCORD_TOKEN`, `DISCORD_CHANNEL_ID`. Found by searching upward from `src/`; values override environment variables (`load_dotenv(override=True)`).
- `ignore_services.json` (optional): JSON array of service names to skip.
- `notified_ids.json` (runtime): JSON array of service names already reported as failed. It prevents duplicate notifications and drives recovery notifications.
- `logs/` (runtime): daily log files. Rotation cleanup (`backupCount`) runs only on rollover inside one process, which a short-lived run rarely reaches, so old files may accumulate.
- `ignore_services.json`, `notified_ids.json` and `logs/` are relative to the working directory. `.env`, `logs/` and `notified_ids.json` are git-ignored.

## Conventions

- Follow the existing style and keep `flake8` clean for the selected rules.
- Commits follow [Conventional Commits](https://www.conventionalcommits.org/); branches follow [Conventional Branch](https://conventional-branch.github.io) short form (`feat/...`, `fix/...`).
- Do not commit to Renovate PRs.
- Never commit secrets such as `DISCORD_TOKEN`, and never write tokens or channel IDs to logs.
- Update `README.md` when setup or behavior changes, and `requirements.txt` when dependencies change.
