# Run Python Unit Tests with Pytest

Runs Python unit tests using Pytest in a reusable GitHub Actions workflow. This workflow is designed to be used in pull requests to ensure that the code changes do not break existing functionality. By default, we'll attempt to install any tools that are specified in your `.tool-versions` file.

Pytest can be configured through files in your repository, and we recommend using [pyproject.toml](https://docs.pytest.org/en/stable/reference/customize.html#configuration-file-formats) for Pytest and any other Python configurations where possible. See [the Pytest documentation](https://docs.pytest.org/en/stable/reference/reference.html#ini-options-ref) for all configuration options.

This workflow can perform rich unit test coverage checking, set the input for `report-coverage` to true, ensure that your project depends on `pytest-cov`, and consider setting your pyproject.toml options like [this example](https://github.com/launchbynttdata/launch-cert-tool/blob/ffe571499003e0ace49484da9379247abc97a1cf/pyproject.toml#L52-L61).

If your tests rely on having an environment compatible with the LCAF Makefile, you may pass `lcaf-makefile-setup: true` as an input to this workflow, and pass an `lcaf-aws-region` if you wish to set a region for LCAF/AWS other than the default `us-east-2`.

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
