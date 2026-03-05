# Remove Dependabot Labels Action

When Dependabot creates pull requests, it often applies ecosystem-specific labels (such as `go`, `javascript`, `python`, `docker`, etc.) in addition to the `dependencies` label. These labels can interfere with branch-based labeling strategies used by tools like [release-drafter](https://github.com/release-drafter/release-drafter).

This action removes labels that were applied by Dependabot while preserving specified labels (by default, only `dependencies`). Labels applied by other users or bots are not affected.

## Behavior

This action will:
1. Query the GitHub Issues Events API to identify labels applied specifically by `dependabot[bot]`
2. Remove all Dependabot-applied labels except those in the preserve list
3. Leave labels applied by other users or bots untouched

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `pr_number` | The pull request number to process | No | `${{ github.event.pull_request.number }}` |
| `github_token` | GitHub token for API access | No | `${{ github.token }}` |
| `preserve_labels` | Comma-separated list of labels to preserve (not remove even if applied by Dependabot) | No | `dependencies` |

## Usage

### Basic Usage

When used in a `pull_request` event workflow, all inputs are optional:

```yaml
jobs:
  your-job:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: write
    steps:
      - uses: actions/checkout@v4

      - name: Remove Dependabot Labels
        uses: launchbynttdata/launch-workflows/.github/actions/remove-dependabot-labels@main
```

### Preserve Additional Labels

To preserve additional Dependabot labels beyond `dependencies`:

```yaml
- name: Remove Dependabot Labels
  uses: launchbynttdata/launch-workflows/.github/actions/remove-dependabot-labels@main
  with:
    preserve_labels: "dependencies,security"
```

### Explicit PR Number

If running outside a `pull_request` event context, provide the PR number explicitly:

```yaml
- name: Remove Dependabot Labels
  uses: launchbynttdata/launch-workflows/.github/actions/remove-dependabot-labels@main
  with:
    pr_number: "123"
```

## Required Permissions

This action requires the following permissions:
- `pull-requests: write` - To remove labels from pull requests
