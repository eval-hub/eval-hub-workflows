# Repository guidance

These instructions apply to the entire repository.

## Commits and pushes

- Every commit pushed to this repository must include a DCO sign-off. Use
  `git commit -s` (or `--signoff`) to add the `Signed-off-by` trailer. In this
  repository, "signed" means this sign-off; cryptographic signing is not required.
- Use Conventional Commits: `type(scope): description`, with an optional scope.
  Examples: `ci: add fork sync workflow`, `test: cover fork sync failures`, and
  `docs: describe workflow credentials`.
- Run `pre-commit run --all-files` before committing or pushing changes.
- Install hooks with `pre-commit install`; this enables both workflow checks at
  `pre-commit` and Conventional Commit/DCO checks at `commit-msg`.
- Let the user review the local branch before pushing or creating a pull request
  when requested. Do not push or open a PR until that review is complete.

## Workflow changes

- Keep reusable workflows in `.github/workflows/` and document their inputs,
  secrets, permissions, and caller examples in `README.md`.
- Pass workflow inputs to shell steps through environment variables and quote
  expansions. Do not interpolate untrusted inputs directly into shell scripts.
- Pin third-party GitHub Actions to full commit SHAs.
- Pin Docker actions to `sha256` digests; local `./` action references are allowed.
- Keep local pre-commit checks and `.github/workflows/checks.yml` aligned.
- Keep tests offline: mock `gh` and never synchronize a real fork during tests.
- Update the fork-sync tests when changing its behavior or interface.
