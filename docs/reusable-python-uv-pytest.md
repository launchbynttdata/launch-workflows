# Run Python Unit Tests with Pytest

Runs Python unit tests using Pytest in a reusable GitHub Actions workflow. This workflow is designed to be used in pull requests to ensure that the code changes do not break existing functionality. This workflow can be customized to report coverage in a Pull Request Comment or not, depending on the needs of the project.

## Usage

To run Python tests against a given PR:

```yaml
name: Run Tests

on:
  pull_request:
    types: [opened, reopened, synchronize]

permissions:
  contents: read
  id-token: write

jobs:
  check:
    name: "Run Tests"
    permissions:
      contents: read
      checks: write
      pull-requests: write
    uses: launchbynttdata/launch-workflows/.github/workflows/reusable-python-uv-pytest.yml@ref
    with:
      report-coverage: false
    secrets: inherit # pragma: allowlist secret

```

Be sure you replace `ref` with an appropriate ref to this repository.
