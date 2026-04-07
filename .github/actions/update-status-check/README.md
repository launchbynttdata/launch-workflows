# Update Status Check Action

GitHub's [Commit Status API](https://docs.github.com/en/rest/commits/statuses) allows workflows to report the state of a check back to a specific commit SHA. This is useful for surfacing the outcome of external processes, gating merges, or providing richer context in pull requests beyond what a workflow run alone provides.

This action wraps the Commit Status API with a simple interface: provide a check name and a status, and we handle the API call.

## Behavior

This action will:
1. Validate that the provided `status` is one of the accepted values (`error`, `failure`, `pending`, `success`)
2. Call the GitHub Commit Status API to create or update the named status check on the specified commit SHA
3. Optionally attach a human-readable description and a target URL to the status

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `check_name` | The name (context) of the status check to create or update | Yes | — |
| `status` | The state to set. One of: `error`, `failure`, `pending`, `success` | Yes | — |
| `sha` | The commit SHA to attach the status check to | No | `${{ github.sha }}` |
| `description` | A short human-readable description of the status | No | `""` |
| `target_url` | A URL to associate with the status (e.g. a link to a build log) | No | `""` |
| `github_token` | GitHub token for API access | No | `${{ github.token }}` |

## Usage

### Basic Usage

Mark a status check as successful on the current commit:

```yaml
jobs:
  your-job:
    runs-on: ubuntu-latest
    permissions:
      statuses: write
    steps:
      - name: Set status check to success
        uses: launchbynttdata/launch-workflows/.github/actions/update-status-check@main
        with:
          check_name: "my-check"
          status: "success"
```

### With Description and Target URL

Provide additional context visible in the GitHub UI:

```yaml
- name: Set status check to failure
  uses: launchbynttdata/launch-workflows/.github/actions/update-status-check@main
  with:
    check_name: "security-scan"
    status: "failure"
    description: "Vulnerabilities were detected."
    target_url: "https://example.com/scan-results/123"
```

### Marking a Check as Pending Before a Long-Running Step

Use `pending` to signal that a check is in progress, then update it on completion:

```yaml
- name: Mark check as pending
  uses: launchbynttdata/launch-workflows/.github/actions/update-status-check@main
  with:
    check_name: "integration-tests"
    status: "pending"
    description: "Integration tests are running..."

- name: Run integration tests
  run: make test-integration

- name: Mark check as success
  if: success()
  uses: launchbynttdata/launch-workflows/.github/actions/update-status-check@main
  with:
    check_name: "integration-tests"
    status: "success"
    description: "All integration tests passed."

- name: Mark check as failure
  if: failure()
  uses: launchbynttdata/launch-workflows/.github/actions/update-status-check@main
  with:
    check_name: "integration-tests"
    status: "failure"
    description: "One or more integration tests failed."
```

### Targeting a Specific Commit SHA

Override the default SHA to set a status on a commit other than the one that triggered the workflow:

```yaml
- name: Set status on a specific commit
  uses: launchbynttdata/launch-workflows/.github/actions/update-status-check@main
  with:
    check_name: "my-check"
    status: "success"
    sha: "abc1234def5678"
```

## Required Permissions

This action requires the following permission on the workflow job:

```yaml
permissions:
  statuses: write
```
