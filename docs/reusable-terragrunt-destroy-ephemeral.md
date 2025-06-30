# Destroy an Ephemeral Terragrunt Environment

This workflow Destroys a single ephemeral Terragrunt environment; it is the counterpart to [reusable-terragrunt-deploy-ephemeral](./reusable-terragrunt-deploy-ephemeral.md) workflow which creates the environment for you.

Unlike the persistent Terragrunt deployment workflow, this workflow does not require a GitHub Environment to exist, you must pass a role ARN which will be assumed prior to invoking any Terragrunt commands.

The typical use case for this workflow is to clean up a throwaway environment once the PR closes. This workflow operates only on the `sandbox` environment folder.

## Usage

To destroy an ephemeral sandbox environment when each PR is completed, implement a workflow similar to the following:

```yaml
name: Destroy Ephemeral Sandbox Environment

on:
  pull_request:
    types: [ closed ]
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
      platform_environment: sandbox

  call-terragrunt-destroy:
    needs: [get-tg-versions, build-matrix]
    permissions:
      contents: read
      id-token: write
    strategy:
      fail-fast: false
      matrix: ${{ fromJson(needs.build-matrix.outputs.matrix) }}

    uses: launchbynttdata/launch-workflows/.github/workflows/reusable-terragrunt-destroy-ephemeral.yml@ref
    with:
      git_branch: ${{ github.head_ref }}
      assume_role_arn: "arn:aws:iam::123456789012:role/my-assumed-role"
      tf_version: ${{ needs.get-tg-versions.outputs.tf_version }}
      tg_version: ${{ needs.get-tg-versions.outputs.tg_version }}
      region: ${{ matrix.terragrunt_environment.region }}
      env_id: ${{ matrix.terragrunt_environment.instance }}
    secrets: inherit
```

Be sure you replace `ref` with an appropriate ref to this repository, and replace the `assume_role_arn` input with the ARN of your choice.
