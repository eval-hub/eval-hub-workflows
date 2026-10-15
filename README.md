# eval-hub-workflows

Reusable GitHub Actions workflows shared across repositories.

## Development checks

Install [pre-commit](https://pre-commit.com/#install), Python 3.10 or newer,
Bash, and `jq`. Enable the hooks and check the repository:

```sh
pre-commit install
pre-commit run --all-files
```

Pre-commit installs its pinned tools and test dependencies into isolated
environments on its first run, including actionlint and ShellCheck via their
Python distribution packages. No separate Go or ShellCheck installation is needed.
The hooks check:

- YAML syntax, merge-conflict markers, trailing whitespace, final newlines, and
  files larger than 500 KiB.
- Python linting, import ordering, and formatting with Ruff.
- GitHub Actions syntax and embedded shell scripts with actionlint and ShellCheck.
- Full commit SHA references for remote actions and reusable workflows, or
  `sha256` digests for Docker actions. Local `./` references are allowed.
- Offline workflow and repository-policy tests.

The tests include
[`scripts/test_sync_fork.py`](scripts/test_sync_fork.py), which exercises the
workflow's Bash step with a mocked `gh` command. Checks cover successful syncs,
already synchronized forks, API errors, invalid inputs, and literal handling of
branch names. Tests do not call GitHub or update a fork.

`pre-commit install` also enables the `commit-msg` hook, which rejects commit
messages without a Conventional Commit subject or a DCO `Signed-off-by` trailer.

[`checks.yml`](.github/workflows/checks.yml) runs these checks on pull requests
and pushes to `main`. It also validates every commit message in a pull request.
CI installs Python automatically; no GitHub token or fork-sync credential is
needed by the tests.

Use Conventional Commits and include a DCO sign-off on every pushed commit with
`git commit -s`, for example `git commit -s -m "ci: update fork sync workflow"`.
See [AGENTS.md](AGENTS.md) for repository guidance.

## Synchronize a downstream fork

[`sync-fork.yml`](.github/workflows/sync-fork.yml) updates a GitHub fork from its
upstream using GitHub's
[fork-sync API](https://docs.github.com/en/rest/branches/branches#sync-a-fork-branch-with-the-upstream-repository).
Repositories in other organizations can call this public workflow when their
GitHub Actions policies allow it.

The destination must be a GitHub fork. The API synchronizes the selected branch
from the same-named upstream branch; it does not accept an arbitrary source
repository or source branch. For example, `opendatahub-io/eval-hub:main` is updated
from `eval-hub/eval-hub:main`. The API reads the latest upstream state when called,
so a run may include commits newer than the push that triggered it.

### Inputs and secret

- `target-repository` (required string): destination fork in `owner/repository` format.
- `target-branch` (optional string, default `main`): branch to synchronize.
- `sync-token` (required secret): credential with write access to the destination fork.

### Commit history

Synchronization preserves all commits reachable from the upstream branch and
their original commit hashes. It does not squash, rebase, or cherry-pick commits.

- If the destination can fast-forward, its branch advances to the upstream commit
  without creating a merge commit.
- If the branches have diverged and can be merged without conflicts, GitHub
  creates a merge commit that preserves both upstream and fork-specific commits.
- If there are merge conflicts, synchronization fails and the destination branch
  remains unchanged.

### Call from the upstream repository

Add this caller to the upstream repository to sync after each push to `main`,
including pull request merges. In both examples, replace `REVIEWED_COMMIT_SHA`
with the full 40-character SHA of a reviewed commit in
`eval-hub/eval-hub-workflows` containing this workflow before enabling the caller.

```yaml
name: Sync downstream fork

on:
  push:
    branches: [main]
  workflow_dispatch: {}

permissions: {}

jobs:
  sync:
    # Prevent this caller from also running in forks that inherit the file.
    if: github.repository == 'eval-hub/eval-hub'
    uses: eval-hub/eval-hub-workflows/.github/workflows/sync-fork.yml@REVIEWED_COMMIT_SHA
    with:
      target-repository: opendatahub-io/eval-hub
      target-branch: main
    secrets:
      sync-token: ${{ secrets.DOWNSTREAM_SYNC_TOKEN }}
```

Replace the repository names for other projects. Pin the workflow reference to
a reviewed commit SHA for stable behavior; `@main` tracks future workflow changes.
The shared workflow does not install this caller or enable synchronization itself.

### Credentials and permissions

Create `DOWNSTREAM_SYNC_TOKEN` as a repository secret in the caller, or as an
organization secret available to selected caller repositories. Pass it explicitly
as `sync-token`. Secrets in the repository hosting the reusable workflow are not
automatically available to callers.

Use a fine-grained personal access token or a GitHub App installation token with
**Contents: write** access to the destination fork. When upstream changes include
workflow files, the credential also needs permission to update workflows.
The upstream caller's `GITHUB_TOKEN` cannot write to a separate downstream
repository. GitHub App installation tokens expire after one hour, so callers
using them must supply a fresh token for each run.

The destination's branch protections and rulesets still apply. This workflow
directly updates the branch, so destinations requiring pull requests should use
a PR-based synchronization process instead.

### Call from the downstream repository

The same workflow can be called from the destination fork on a schedule or with
`workflow_dispatch`. An upstream push does not trigger workflows in the fork.
When using the destination's `GITHUB_TOKEN`, grant the caller `contents: write`
and pass `${{ secrets.GITHUB_TOKEN }}` explicitly as `sync-token`. The reusable
workflow inherits the caller's `GITHUB_TOKEN` permissions without overriding
them. The upstream example's `permissions: {}` is appropriate only because it
uses a separate token; do not copy that setting into a caller using `GITHUB_TOKEN`.

For example, add this caller to `opendatahub-io/eval-hub`, replacing
`REVIEWED_COMMIT_SHA` as described above:

```yaml
name: Sync from upstream

on:
  schedule:
    - cron: "0 * * * *"
  workflow_dispatch: {}

permissions:
  contents: write

jobs:
  sync:
    if: github.repository == 'opendatahub-io/eval-hub'
    uses: eval-hub/eval-hub-workflows/.github/workflows/sync-fork.yml@REVIEWED_COMMIT_SHA
    with:
      target-repository: opendatahub-io/eval-hub
      target-branch: main
    secrets:
      sync-token: ${{ secrets.GITHUB_TOKEN }}
```

Events caused by `GITHUB_TOKEN` generally do not trigger further workflows; use
a GitHub App token or PAT if the synchronized push must trigger downstream CI.

### Results and failures

Successful runs add the API's result, merge type, and upstream branch to the job
summary. An already synchronized fork is a successful no-op. Merge conflicts
(HTTP 409), insufficient permissions, and branch protection failures fail the job
with the API error visible in its log. Resolve conflicts manually and rerun the
caller. The workflow does not force-push or resolve conflicts automatically.

Runs targeting the same repository and branch are serialized within each caller
repository. GitHub Actions concurrency groups do not serialize runs across
different caller repositories, so use one caller per destination branch.
