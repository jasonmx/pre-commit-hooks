# pre-commit-hooks

[pre-commit](https://pre-commit.com) hooks shared by my repos.

## check-private

Refuses a commit whose staged files or message name a private detail: a hostname, a person's name, an entity ID, a
token. A public repo can't hold its own blocklist, so the terms live in gitignored files in the repo's main checkout
(also read from a linked worktree):

- `.private-terms` and `.private-terms.rig` by default, or the files named with `--terms-file NAME` (repeatable).
- One term per line, matched case-insensitively. `term<TAB>label` reports a hit by its label, so a secret is never
  echoed. Lines starting with `#` are comments.
- With no terms file (CI, a contributor's clone) the check passes.

```yaml
default_install_hook_types: [pre-commit, commit-msg]
repos:
  - repo: https://github.com/jasonmx/pre-commit-hooks
    rev: v1.0.0
    hooks:
      - id: check-private
```

Add the terms files to `.gitignore`.

## Development

`uv run pytest`
