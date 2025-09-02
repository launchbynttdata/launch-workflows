# Deploy an Ephemeral Terragrunt Environment to Azure

Plans and deploys a single Terragrunt environment in an ephemeral manner; you are expected to use the [reusable-terragrunt-destroy-ephemeral-azure](./reusable-terragrunt-destroy-ephemeral-azure.md) workflow to remove the environment when you are done with it. In order to avoid naming conflicts with ephemeral environments, care must be taken in the Terraform module that Terragrunt references to ensure resources are named in a unique manner.

This workflow operates only on the `sandbox` environment folder. Unlike the persistent Terragrunt deployment workflow, this workflow does not require a GitHub Environment to exist, but you must pass the correct secrets to this workflow (or provide them at the organization/repository level and utilize secrets inheritance).

The typical use case for this workflow is to create a throwaway environment each time a pull request is created, and then use [the destroy workflow](./reusable-terragrunt-destroy-ephemeral-azure.md) to clean up the environment once the PR closes.

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
      tf_version: ${{ needs.get-tg-versions.outputs.tf_version }}
      tg_version: ${{ needs.get-tg-versions.outputs.tg_version }}
      region: ${{ matrix.terragrunt_environment.region }}
      env_id: ${{ matrix.terragrunt_environment.instance }}
    secrets: inherit

    # Alternately, pass the following secrets:
    #   TERRAGRUNT_DEPLOY_AZURE_CLIENT_ID: ${{ secrets.your_azure_client_id_secret }}
    #   TERRAGRUNT_DEPLOY_AZURE_TENANT_ID: ${{ secrets.your_azure_tenant_id_secret }}
    #   TERRAGRUNT_DEPLOY_AZURE_SUBSCRIPTION_ID: ${{ secrets.your_azure_subscription_id_secret }}
```

Be sure you replace `ref` with an appropriate ref to this repository. For more information on OIDC setup for Azure, see the [azure/login action documentation](https://github.com/Azure/login?tab=readme-ov-file#login-with-openid-connect-oidc-recommended).
