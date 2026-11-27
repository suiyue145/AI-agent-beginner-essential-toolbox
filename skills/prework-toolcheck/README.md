# prework-toolcheck

Automatically scan for and list existing tools relevant to the current task before you start working — reminder and recommendation only, never installs without explicit approval.

## Features

- **Prework reminder**: scan the ecosystem for existing skills, tools, or MCPs at task start; beginners need no skill knowledge — just review the list and approve.
- **Three-tier list**: "already installed / recommended / optional", up to 3 items each, with a plain-language description per item.
- **Offline by default**: prework reads only local stored data — no network, no upload; network access only when the user explicitly asks to rescan.
- **Silent when irrelevant**: if no tools match the task, no list, no install prompt — just start working.
- **Installation delegated**: after approval, `github-skill-installer` handles reliable installation; this skill never installs itself.

## Installation

Place `SKILL.md`, `scripts/`, `references/`, and `config/` into your Agent's skills directory, e.g. `<your skills root>/prework-toolcheck/`. Default directories vary by Agent; use your actual installation path.

Optional: register `scripts/hook_user_prompt_submit.py` as a UserPromptSubmit hook to auto-remind prework scanning on the first substantive task of each new session.

## Usage

Say "what tools can I use before starting", "what should I use for this task", "what must a beginner install", or let the hook trigger it — this skill performs the scan.

Invoke directly:

```bash
# Default: local data only (offline)
bash <your skills directory>/scripts/scan.sh "<task description>"

# When the user explicitly requests network access
bash <your skills directory>/scripts/scan.sh "<task description>" --online

# Force rescan / local only / no upload
python3 <your skills directory>/scripts/scan_cached.py "<task>" --force
python3 <your skills directory>/scripts/scan_cached.py "<task>" --no-shared
python3 <your skills directory>/scripts/scan_cached.py "<task>" --no-upload
```

The list ends by explicitly asking whether to install or use anything; work continues only after your answer. See `SKILL.md` for details.

## License

**Personal use only; commercial use is prohibited.**

See [LICENSE](LICENSE): free for personal use, modification, and distribution, but no commercial use (including integration, invocation, or paid provision in commercial products/services) without written permission.
