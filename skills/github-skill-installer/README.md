# github-skill-installer

Reliably install skills / tools from GitHub, bypassing stuck `git clone`, unreachable raw/zip downloads, and GitHub API rate limits.

## Features

- **Confirm before installing**: verify repository authenticity and source reliability; never install without user consent.
- **Reliable download**: auto-detect repository layout (root or `skills/xxx/`), download via jsDelivr CDN in parallel, use only 1 API call for the file tree.
- **Verify after install**: integrity check + runtime self-test; retries fetch only missing files, no half-installed directories.
- **Beginner-friendly**: explains in plain language whether installation succeeded and how to trigger the skill.

## Installation

Place `SKILL.md`, `scripts/`, and `references/` into your Agent's skills directory, e.g. `<your skills root>/github-skill-installer/`. Default directories vary by Agent; use your actual installation path.

The installation target can be overridden with the `WB_SKILLS_DIR` environment variable.

## Usage

Say "install this skill", "install XX from GitHub", or "go ahead, install it" in conversation, or explicitly approve a tool after a prework scan — this skill takes over automatically.

Invoke the install script directly:

```bash
bash <your skills directory>/scripts/install.sh <owner/repo> <subdirectory> <local-name>
```

Examples:

```bash
bash <your skills directory>/scripts/install.sh mvanhorn/last30days-skill skills/last30days last30days
bash <your skills directory>/scripts/install.sh DeezGit21/skill-radar . skill-radar-from-gh
```

Set `GH_BRANCH=master` first if the branch is not `main`. After installation, check for `FILECHECK missing=0 sizebad=0` in the output; newly installed skills only enter the auto-trigger list **on the next session**. See `SKILL.md` for details.

## License

**Personal use only; commercial use is prohibited.**

See [LICENSE](LICENSE): free for personal use, modification, and distribution, but no commercial use (including integration, invocation, or paid provision in commercial products/services) without written permission.
