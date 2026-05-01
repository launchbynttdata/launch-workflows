# Automated Approvals for Pull Requests

Automatically approves pull requests authored entirely by trusted automation accounts (`dependabot[bot]` and `launch-skeleton-auto-updater[bot]`). If any non-automated commits are detected on the PR, existing automated approvals are revoked instead.

This workflow uses two separate GitHub App identities to provide the two approvals typically required by branch protection rules.

## Behavior

1. **Approve** — If all commits on the PR are from allowed automation authors, both approver apps submit an approval review.
2. **Revoke** — If any commit is from a non-automated author, any existing approvals from the approver apps are dismissed. This prevents a human from pushing commits onto an automated PR to bypass review requirements.
3. **Skeleton updater title check** — For PRs authored by `launch-skeleton-auto-updater[bot]`, the PR title must start with `chore`. If it does not, approval is withheld.

## Usage

Add the following workflow to your repository (suggested name: `.github/workflows/pr-automated-approvals.yml`):

```yaml
name: Automated Approvals

on:
  pull_request:
    types: [opened, reopened, synchronize]

permissions:
  pull-requests: read
  contents: read

jobs:
  automated-approvals:
    name: Automated Approvals
    permissions:
      pull-requests: read
      contents: read
    uses: launchbynttdata/launch-workflows/.github/workflows/reusable-pr-automated-approvals.yml@ref
    secrets: inherit
```

Be sure you replace `ref` with an appropriate ref to this repository.

## Inputs

This workflow has no configurable inputs.

## Required Secrets and Variables

| Name | Type | Description |
|------|------|-------------|
| `LAUNCH_APPROVER_ALPHA_ID` | Variable | The GitHub App ID for the first approver app. |
| `LAUNCH_APPROVER_ALPHA_KEY` | Secret | The private key for the first approver app. |
| `LAUNCH_APPROVER_BRAVO_ID` | Variable | The GitHub App ID for the second approver app. |
| `LAUNCH_APPROVER_BRAVO_KEY` | Secret | The private key for the second approver app. |

Both approver apps must be installed on the repository with permission to submit pull request reviews.
