# Deploy an Ephemeral Terragrunt Environment to AWS

Plans and deploys a single Terragrunt environment in an ephemeral manner; you are expected to use the [reusable-terragrunt-destroy-ephemeral-aws](./reusable-terragrunt-destroy-ephemeral-aws.md) workflow to remove the environment when you are done with it. In order to avoid naming conflicts with ephemeral environments, care must be taken in the Terraform module that Terragrunt references to ensure resources are named in a unique manner.

This workflow operates only on the `sandbox` environment folder. Unlike the persistent Terragrunt deployment workflow, this workflow does not require a GitHub Environment to exist, you must pass a role ARN which will be assumed prior to invoking any Terragrunt commands.

The typical use case for this workflow is to create a throwaway environment each time a pull request is created, and then use [the destroy workflow](./reusable-terragrunt-destroy-ephemeral.md) to clean up the environment once the PR closes.

## Usage

To deploy an ephemeral sandbox environment for each PR, implement a workflow similar to the following:

```yaml
name: Deploy Ephemeral Sandbox Environment

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
      platform_environment: sandbox

  call-terragrunt-deploy:
    needs: [get-tg-versions, build-matrix]
    permissions:
      contents: read
      id-token: write
    strategy:
      fail-fast: false
      matrix: ${{ fromJson(needs.build-matrix.outputs.matrix) }}

    uses: launchbynttdata/launch-workflows/.github/workflows/reusable-terragrunt-deploy-ephemeral.yml@ref
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
