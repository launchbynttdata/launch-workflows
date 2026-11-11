# Update Status Check Action

GitHub's [Commit Status API](https://docs.github.com/en/rest/commits/statuses) allows workflows to report the state of a check back to a specific commit SHA. This is useful for surfacing the outcome of external processes, gating merges, or providing richer context in pull requests beyond what a workflow run alone provides.

This action wraps the Commit Status API with a simple interface: provide a check name and a status, and we handle the API call.

## Behavior

This action will:
1. On pull request events, look up the pull request's current head SHA. When the lookup returns a full commit SHA, it replaces `sha`, whether `sha` was defaulted or passed explicitly. If the lookup fails (for example, the token lacks `pull-requests: read`) or doesn't return a full commit SHA, the action keeps `sha` and logs a warning with the cause
2. Fail if the resulting SHA isn't a full 40-character lowercase commit SHA
3. Validate that the provided `status` is one of the accepted values (`error`, `failure`, `pending`, `success`)
4. Call the GitHub Commit Status API to create or update the named status check on the resulting commit SHA
5. Optionally attach a human-readable description and a target URL to the status

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `check_name` | The name (context) of the status check to create or update | Yes | — |
| `status` | The state to set. One of: `error`, `failure`, `pending`, `success` | Yes | — |
| `sha` | The full 40-character commit SHA to attach the status check to. On pull request events, a successful lookup of the PR's current head SHA replaces this input, whether defaulted or explicit; otherwise the input is kept and a warning is logged | No | `${{ github.event.pull_request.head.sha \|\| github.sha }}` |
| `description` | A short human-readable description of the status | No | `""` |
| `target_url` | A URL to associate with the status (e.g. a link to a build log) | No | `""` |
| `github_token` | GitHub token for API access | No | `${{ github.token }}` |

## Usage

### Basic Usage

Mark a status check as successful on the current commit (replacing `ref` with a tag or commit SHA from this repository):

```yaml
jobs:
  your-job:
    runs-on: ubuntu-latest
    permissions:
      statuses: write
    steps:
      - name: Set status check to success
        uses: launchbynttdata/launch-workflows/.github/actions/update-status-check@ref
        with:
          check_name: "my-check"
          status: "success"
```

### With Description and Target URL

Provide additional context visible in the GitHub UI:

```yaml
- name: Set status check to failure
  uses: launchbynttdata/launch-workflows/.github/actions/update-status-check@ref
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
  uses: launchbynttdata/launch-workflows/.github/actions/update-status-check@ref
  with:
    check_name: "integration-tests"
    status: "pending"
    description: "Integration tests are running..."

- name: Run integration tests
  run: make test-integration

- name: Mark check as success
  if: success()
  uses: launchbynttdata/launch-workflows/.github/actions/update-status-check@ref
  with:
    check_name: "integration-tests"
    status: "success"
    description: "All integration tests passed."

- name: Mark check as failure
  if: failure()
  uses: launchbynttdata/launch-workflows/.github/actions/update-status-check@ref
  with:
    check_name: "integration-tests"
    status: "failure"
    description: "One or more integration tests failed."
```

### Targeting a Specific Commit SHA

Override the default SHA to set a status on a commit other than the one that triggered the workflow. The SHA must be the full 40 characters:

```yaml
- name: Set status on a specific commit
  uses: launchbynttdata/launch-workflows/.github/actions/update-status-check@ref
  with:
    check_name: "my-check"
    status: "success"
    sha: "0123456789abcdef0123456789abcdef01234567"
```

On pull request events, a successful lookup of the PR's head SHA replaces an explicit `sha`, so a non-head SHA only takes effect outside pull request events, or when the lookup fails and the action logs a warning.

## Required Permissions

This action requires the following permission on the workflow job:

```yaml
permissions:
  statuses: write
```

On pull request events, also grant `pull-requests: read` so the action can look up the PR's current head SHA. Without it, the action warns and sets the status on `sha`.
