# skill-radar-cn

Scan for essential tools before starting work and list candidates for you to choose from — recommendation only, never installs.

## Features

- **Multi-source scanning**: covers skills.sh popular list, official directories (Anthropic / OpenAI Codex / Vercel / DeepSeek Harness / Hermes Agent), platform topics, the MCP registry, and GitHub search.
- **Cloud-first**: check GitHub for shared scan results from the last 3 days (anonymous read); stop on a hit, otherwise use local cache, then live scan.
- **Result upload**: successful local scans are merged and uploaded to the public repository for other machines; gracefully degrades when offline or without a token.
- **Chinese-friendly**: built-in Chinese-to-English keyword mapping (e.g. 调研市场 → research market), so varied phrasing still matches.
- **Recommend only**: grouped by category with name, stars, one-line description, and reason — you decide what to install.

## Installation

Place `SKILL.md` into your Agent's skills directory, e.g. `<your skills root>/skill-radar-cn/`.

This skill depends on `scripts/scan_cached.py` in `prework-toolcheck` and the underlying `skill-radar` CLI. Paths work directly when both are installed under the same skills root; otherwise replace placeholders per the "Path Convention" in `SKILL.md`. Set `GITHUB_TOKEN` to raise the GitHub API limit from 60 to 5000 requests/hour; anonymous scanning still works without it, just slower.

## Usage

Say "what tools can I use before starting", "is there an existing skill / MCP for this task", or "let me find a usable tool" — this skill triggers automatically.

Scan by task from the command line:

```bash
python3 <your skills directory>/../prework-toolcheck/scripts/scan_cached.py "<task description>"
```

When the user says "rescan" or "I want the latest":

```bash
python3 <your skills directory>/../prework-toolcheck/scripts/scan_cached.py "<task>" --force
python3 <your skills directory>/../prework-toolcheck/scripts/scan_cached.py "<task>" --refresh-shared
python3 <your skills directory>/../prework-toolcheck/scripts/scan_cached.py "<task>" --no-shared
```

The cache file is `~/.skill-radar/scan-cache.json`; delete it for a full rescan. View scan sources with `skill-radar list-sources`. See `SKILL.md` for details.

## License

**Personal use only; commercial use is prohibited.**

See [LICENSE](LICENSE): free for personal use, modification, and distribution, but no commercial use (including integration, invocation, or paid provision in commercial products/services) without written permission.
