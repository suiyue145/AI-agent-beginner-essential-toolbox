# skill-publish-safety-check

Run a safety check before publishing a skill online or to a skill marketplace, removing traces of the authoring environment.

## Features

- **Privacy leak scan**: API keys, tokens, real email addresses, absolute home-directory paths, internal hostnames, public IPs.
- **Authoring-environment cleanup**: rewrite `.workbuddy` / `.claude` paths and absolute workspace paths into placeholders for readers to fill in (e.g. `<your skills directory>`).
- **README maintainer redaction**: remove maintainer sections, field lines, local configuration lines, and blocks marked `<!-- publish:remove -->`.
- **Non-destructive**: only staging copies are modified; the source skill directory is never touched.

## Installation

Place `SKILL.md`, `scripts/`, and `references/` into your Agent's skills directory, e.g. `<your skills root>/skill-publish-safety-check/`. Default directories vary by Agent; use your actual installation path.

## Usage

When another agent is about to publish a skill version, submit to a marketplace, or perform a pre-release redaction review, run these three steps in order:

```bash
python3 scripts/skill_publish_check.py scan <skill-directory>
python3 scripts/skill_publish_check.py sanitize <skill-directory> --out <staging-directory>
python3 scripts/skill_publish_check.py verify <staging-directory>
```

Hard issues reported by `scan` (e.g. real secrets) require manual handling; only an exit code of 0 from `verify` means the skill is ready to publish. See `SKILL.md` and `references/rewrite-rules.md` for full rules, configuration format, and limitations.

## License

**Personal use only; commercial use is prohibited.**

See [LICENSE](LICENSE): free for personal use, modification, and distribution, but no commercial use (including integration, invocation, or paid provision in commercial products/services) without written permission.
