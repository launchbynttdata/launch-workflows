# Plan a Terragrunt Environment in AWS

Plans a single Terragrunt environment.

Rather than utilizing a GitHub Environment (which may require approval for this plan-only scenario), this workflow takes an `assume_role_arn` input. The typical use case for this workflow is to perform a plan against an upper environment, e.g. production, when the code is being PRed.

## Usage

```yaml
name: Plan Production Environment

on:
  pull_request:
    types: [opened, synchronize, reopened]
    branches: [ "**" ]

jobs:
  get-tg-versions:
    permissions:
      contents: read
    uses: launchbynttdata/launch-workflows/.github/workflows/reusable-terragrunt-versions.yml@ref

  build-matrix:
    permissions:
      contents: read
    uses: launchbynttdata/launch-workflows/.github/workflows/reusable-github-matrix-tg.yml@ref
    with:
      platform_environment: production

  call-terragrunt-plan:
    needs: [get-tg-versions, build-matrix]
    permissions:
      contents: read
      id-token: write
    strategy:
      fail-fast: false
      matrix: ${{ fromJson(needs.build-matrix.outputs.matrix) }}

    uses: launchbynttdata/launch-workflows/.github/workflows/reusable-terragrunt-plan-only.yml@ref
    with:
      git_branch: ${{ github.head_ref }}
      tf_version: ${{ needs.get-tg-versions.outputs.tf_version }}
      tg_version: ${{ needs.get-tg-versions.outputs.tg_version }}
      assume_role_arn: "arn:aws:iam::123456789012:role/my-assumed-role"
      environment: ${{ matrix.terragrunt_environment.environment }}
      region: ${{ matrix.terragrunt_environment.region }}
      env_id: ${{ matrix.terragrunt_environment.instance }}
    secrets: inherit

```

Be sure you replace `ref` with an appropriate ref to this repository, and replace the `assume_role_arn` input with the ARN of your choice.
