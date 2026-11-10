# Fiction Writing Skills

Five portable Markdown skills for evidence-based canon maintenance, causal outlining, scene auditing, voice-preserving revision, and chapter closeout. Two documented workflows support author-mediated drafting/review and optional staged roles. Instructions are primarily Chinese; the architecture is genre-neutral.

Copy one complete `skills/<name>/` directory into an Agent Skills-compatible client's skill location, or supply its SKILL.md and relevant references manually. Each skill is self-contained. Keep your manuscripts outside this repository.

Optional tools require Python 3.10+ and the standard library only:

```sh
python scripts/validate_repo.py
python -m unittest discover -s tests -v
python scripts/fiction_tools.py demo
```

Scripts verify file hashes and explicit review records; they do not perform semantic literary review, authenticate approvals, or orchestrate agents. See [test boundaries](docs/TEST_RESULTS.md) and [installation](docs/install.md).

MIT covers this repository's newly authored materials. No source novel, private manuscript, conversation, account information, or third-party media is included or licensed. User manuscripts remain under their own rights. Public release requires a separately reviewed exact file allowlist.
