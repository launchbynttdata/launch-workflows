# Destroy an Ephemeral Terragrunt Environment to Azure

This workflow Destroys a single ephemeral Terragrunt environment; it is the counterpart to [reusable-terragrunt-deploy-ephemeral-azure](./reusable-terragrunt-deploy-ephemeral-azure.md) workflow which creates the environment for you.

Unlike the persistent Terragrunt deployment workflow, this workflow does not require a GitHub Environment to exist, you must pass three secret values which will be used to obtain a role prior to invoking any Terragrunt commands.

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

    uses: launchbynttdata/launch-workflows/.github/workflows/reusable-terragrunt-destroy-ephemeral-azure.yml@ref
    with:
      git_branch: ${{ github.head_ref }}
      tf_version: ${{ needs.get-tg-versions.outputs.tf_version }}
      tg_version: ${{ needs.get-tg-versions.outputs.tg_version }}
      region: ${{ matrix.terragrunt_environment.region }}
      env_id: ${{ matrix.terragrunt_environment.instance }}
    secrets: inherit # pragma: allowlist secret
    
    # Alternately, pass the following secrets:
    #   TERRAFORM_CHECK_AZURE_CLIENT_ID: ${{ secrets.your_azure_client_id_secret }}
    #   TERRAFORM_CHECK_AZURE_TENANT_ID: ${{ secrets.your_azure_tenant_id_secret }}
    #   TERRAFORM_CHECK_AZURE_SUBSCRIPTION_ID: ${{ secrets.your_azure_subscription_id_secret }}
```

Be sure you replace `ref` with an appropriate ref to this repository. For more information on OIDC setup for Azure, see the [azure/login action documentation](https://github.com/Azure/login?tab=readme-ov-file#login-with-openid-connect-oidc-recommended).
