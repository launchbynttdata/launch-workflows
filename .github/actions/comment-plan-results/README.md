# Comment Plan Results Action

This action downloads Terraform/Terragrunt plan and output artifacts and comments on a Pull Request with a summary of the changes and any relevant endpoints.

## Behavior

This action will:
1. Download the specified artifact containing `plan.json` and `outputs.json`.
2. Parse the `plan.json` to extract the number of resources added, updated, and deleted, as well as any diagnostics.
3. Parse `outputs.json` to extract the `ephemeral_url` if present.
4. Post a comment to the specified Pull Request (or the current one by default) with a summary of these results.

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `artifact_name` | Name of the artifact containing `plan.json` and `outputs.json` | Yes | N/A |
| `github_token` | GitHub token for commenting on the PR | No | `${{ github.token }}` |
| `pr_number` | The pull request number to comment on | No | `${{ github.event.pull_request.number }}` |
| `comment_title` | Title for the PR comment | No | `Terraform Plan Results` |

## Usage

### Basic Usage

This action is typically used in a workflow after a Terraform/Terragrunt plan step that uploads its results as an artifact.

```yaml
jobs:
  plan:
    runs-on: ubuntu-latest
    outputs:
      artifact_name: ${{ steps.set-artifact-name.outputs.artifact_name }}
    steps:
      # ... run terragrunt plan and upload artifacts ...
      - name: Set artifact name
        id: set-artifact-name
        run: echo "artifact_name=tf-artifacts-${{ github.run_id }}" >> "$GITHUB_OUTPUT"

  comment:
    needs: plan
    runs-on: ubuntu-latest
    permissions:
      pull-requests: write
    steps:
      - name: Comment Plan Results
        uses: launchbynttdata/launch-workflows/.github/actions/comment-plan-results@ref
        with:
          artifact_name: ${{ needs.plan.outputs.artifact_name }}
```

### Customizing the Comment

You can customize the title of the comment to distinguish between different environments or components:

```yaml
- name: Comment Plan Results
  uses: launchbynttdata/launch-workflows/.github/actions/comment-plan-results@ref
  with:
    artifact_name: ${{ needs.plan.outputs.artifact_name }}
    comment_title: "Terragrunt Plan (VPC)"
```

## Required Permissions

This action requires `pull-requests: write` permissions to post comments on the PR.

```yaml
permissions:
  pull-requests: write
```
