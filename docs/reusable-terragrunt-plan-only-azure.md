# Plan a Terragrunt Environment in Azure

Plans a single Terragrunt environment.

The typical use case for this workflow is to perform a plan against an upper environment, e.g. production, when the code is being PRed.

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

    uses: launchbynttdata/launch-workflows/.github/workflows/reusable-terragrunt-plan-only-azure.yml@ref
    with:
      git_branch: ${{ github.head_ref }}
      tf_version: ${{ needs.get-tg-versions.outputs.tf_version }}
      tg_version: ${{ needs.get-tg-versions.outputs.tg_version }}
      environment: ${{ matrix.terragrunt_environment.environment }}
      region: ${{ matrix.terragrunt_environment.region }}
      env_id: ${{ matrix.terragrunt_environment.instance }}
    secrets: inherit # pragma: allowlist secret
    
    # Alternately, pass the following secrets:
    #   TERRAGRUNT_DEPLOY_AZURE_CLIENT_ID: ${{ secrets.your_azure_client_id_secret }}
    #   TERRAGRUNT_DEPLOY_AZURE_TENANT_ID: ${{ secrets.your_azure_tenant_id_secret }}
    #   TERRAGRUNT_DEPLOY_AZURE_SUBSCRIPTION_ID: ${{ secrets.your_azure_subscription_id_secret }}

```

Be sure you replace `ref` with an appropriate ref to this repository. For more information on OIDC setup for Azure, see the [azure/login action documentation](https://github.com/Azure/login?tab=readme-ov-file#login-with-openid-connect-oidc-recommended).
