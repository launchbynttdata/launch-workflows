# Plan a Terragrunt Environment

Plans a single Terragrunt environment. This workflow unifies the previously separate `reusable-terragrunt-plan-only-aws.yml` and `reusable-terragrunt-plan-only-azure.yml` workflows into a single, provider-agnostic workflow controlled by the `auth_method` input.

`auth_method` accepts a comma-delimited list of authentication methods, enabling multiple providers to be authenticated simultaneously (e.g. `"aws,github"` to authenticate with AWS via OIDC while also generating a GitHub App token for private module access). It can also be omitted or set to an empty string to run Terragrunt without any authentication.

Rather than utilizing a GitHub Environment (which may require approval for this plan-only scenario), this workflow takes authentication credentials directly. The typical use case for this workflow is to perform a plan against an upper environment, e.g. production, when the code is being PRed.

## Usage

### AWS authentication (`auth_method: aws`)

Use this when your environment is deployed to AWS. Authentication is performed via OIDC using a role you provide:

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
      statuses: write
    strategy:
      fail-fast: false
      matrix: ${{ fromJson(needs.build-matrix.outputs.matrix) }}

    uses: launchbynttdata/launch-workflows/.github/workflows/reusable-terragrunt-plan-only.yml@ref
    with:
      auth_method: "aws"
      git_branch: ${{ github.head_ref }}
      tf_version: ${{ needs.get-tg-versions.outputs.tf_version }}
      tg_version: ${{ needs.get-tg-versions.outputs.tg_version }}
      tg_dir: "platform/${{ matrix.terragrunt_environment.environment }}/${{ matrix.terragrunt_environment.region }}/${{ matrix.terragrunt_environment.instance }}"
      aws_auth_region: "us-east-2"
      aws_assume_role_arn: "arn:aws:iam::123456789012:role/my-assumed-role"
```

Replace `ref` with an appropriate ref to this repository, and replace the `assume_role_arn` and `auth_region` inputs with values of your choosing.

### Azure authentication (`auth_method: azure`)

Use this when your environment is deployed to Azure. Authentication is performed via OIDC using Azure credentials passed as secrets:

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
      statuses: write
    strategy:
      fail-fast: false
      matrix: ${{ fromJson(needs.build-matrix.outputs.matrix) }}

    uses: launchbynttdata/launch-workflows/.github/workflows/reusable-terragrunt-plan-only.yml@ref
    with:
      auth_method: "azure"
      git_branch: ${{ github.head_ref }}
      tf_version: ${{ needs.get-tg-versions.outputs.tf_version }}
      tg_version: ${{ needs.get-tg-versions.outputs.tg_version }}
      tg_dir: "platform/${{ matrix.terragrunt_environment.environment }}/${{ matrix.terragrunt_environment.region }}/${{ matrix.terragrunt_environment.instance }}"
    secrets: inherit # pragma: allowlist secret

    # For usage outside the launchbynttdata organization, pass the secrets explicitly:
    # secrets:
    #   TERRAGRUNT_DEPLOY_AZURE_CLIENT_ID: ${{ secrets.your_azure_client_id_secret }}
    #   TERRAGRUNT_DEPLOY_AZURE_TENANT_ID: ${{ secrets.your_azure_tenant_id_secret }}
    #   TERRAGRUNT_DEPLOY_AZURE_SUBSCRIPTION_ID: ${{ secrets.your_azure_subscription_id_secret }}
```

Replace `ref` with an appropriate ref to this repository. For more information on OIDC setup for Azure, see the [azure/login action documentation](https://github.com/Azure/login?tab=readme-ov-file#login-with-openid-connect-oidc-recommended).

### GitHub App authentication (`auth_method: github`)

Use this when your Terragrunt configuration needs to plan changes via the GitHub Terraform Provider. Authentication is performed using a GitHub App, which generates a short-lived token:

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
      statuses: write
    strategy:
      fail-fast: false
      matrix: ${{ fromJson(needs.build-matrix.outputs.matrix) }}

    uses: launchbynttdata/launch-workflows/.github/workflows/reusable-terragrunt-plan-only.yml@ref
    with:
      auth_method: "github"
      git_branch: ${{ github.head_ref }}
      tf_version: ${{ needs.get-tg-versions.outputs.tf_version }}
      tg_version: ${{ needs.get-tg-versions.outputs.tg_version }}
      tg_dir: "platform/${{ matrix.terragrunt_environment.environment }}/${{ matrix.terragrunt_environment.region }}/${{ matrix.terragrunt_environment.instance }}"
      github_app_id: "123456"
    secrets:
      TERRAGRUNT_DEPLOY_GITHUB_APP_SECRET: ${{ secrets.MY_GITHUB_APP_PRIVATE_KEY }}
```

Replace `ref` with an appropriate ref to this repository, and replace the `github_app_id` input and `TERRAGRUNT_DEPLOY_GITHUB_APP_SECRET` secret with values for your GitHub App.

Note that this does not perform the checkout with the obtained GitHub token, it is only used in the context of planning GitHub resources managed with Terragrunt!

### Combined authentication (e.g. `auth_method: "aws,azure"`)

Use this when your infrastructure is deployed across AWS and Azure within a single Terragrunt environment:

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
      statuses: write
    strategy:
      fail-fast: false
      matrix: ${{ fromJson(needs.build-matrix.outputs.matrix) }}

    uses: launchbynttdata/launch-workflows/.github/workflows/reusable-terragrunt-plan-only.yml@ref
    with:
      auth_method: "aws,azure"
      git_branch: ${{ github.head_ref }}
      tf_version: ${{ needs.get-tg-versions.outputs.tf_version }}
      tg_version: ${{ needs.get-tg-versions.outputs.tg_version }}
      tg_dir: "platform/${{ matrix.terragrunt_environment.environment }}/${{ matrix.terragrunt_environment.region }}/${{ matrix.terragrunt_environment.instance }}"
      aws_auth_region: "us-east-2"
      aws_assume_role_arn: "arn:aws:iam::123456789012:role/my-assumed-role"
    secrets:
      TERRAGRUNT_DEPLOY_AZURE_CLIENT_ID: ${{ secrets.your_azure_client_id_secret }}
      TERRAGRUNT_DEPLOY_AZURE_TENANT_ID: ${{ secrets.your_azure_tenant_id_secret }}
      TERRAGRUNT_DEPLOY_AZURE_SUBSCRIPTION_ID: ${{ secrets.your_azure_subscription_id_secret }}
```

Replace `ref` with an appropriate ref to this repository, and replace the `aws_assume_role_arn`, `aws_auth_region`, and `TERRAGRUNT_DEPLOY_AZURE_*` secrets with your own.

## Inputs

| Name | Description | Required | Default |
|------|-------------|----------|---------|
| `auth_method` | Comma-delimited list of authentication methods to use. Valid values are `aws`, `azure`, and `github` (e.g. `"aws"`, `"aws,github"`, `"aws,azure"`). Omit or pass an empty string to run without authentication. | No | `""` |
| `git_branch` | Branch triggering this plan. | Yes | — |
| `tf_version` | Version of Terraform to utilize. | Yes | `1.5.5` |
| `tg_version` | Version of Terragrunt to utilize. | Yes | — |
| `tg_dir` | Folder containing the Terragrunt configuration to plan (relative to the repository root). | Yes | — |
| `aws_auth_region` | AWS region to use for authentication. Required when `auth_method` includes `aws`. | No | — |
| `aws_assume_role_arn` | ARN of the role to assume prior to Terragrunt invocation. Required when `auth_method` includes `aws`. | No | — |
| `github_app_id` | GitHub App ID for authentication. Required when `auth_method` includes `github`. Defaults to `vars.TERRAGRUNT_DEPLOY_GITHUB_APP_ID`. | No | `${{ vars.TERRAGRUNT_DEPLOY_GITHUB_APP_ID }}` |
| `before_plan_commands` | Commands to run prior to executing Terragrunt plan. | No | `""` |
| `after_plan_commands` | Commands to run after executing Terragrunt plan. | No | `""` |

## Secrets

| Name | Description | Required |
|------|-------------|----------|
| `TERRAGRUNT_DEPLOY_AZURE_CLIENT_ID` | Azure client ID for OIDC authentication. Required when `auth_method` includes `azure`. | No* |
| `TERRAGRUNT_DEPLOY_AZURE_TENANT_ID` | Azure tenant ID for OIDC authentication. Required when `auth_method` includes `azure`. | No* |
| `TERRAGRUNT_DEPLOY_AZURE_SUBSCRIPTION_ID` | Azure subscription ID for OIDC authentication. Required when `auth_method` includes `azure`. | No* |
| `TERRAGRUNT_DEPLOY_GITHUB_APP_SECRET` | GitHub App private key for authentication. Required when `auth_method` includes `github`. | No* |

*These secrets are declared as optional at the workflow level to allow reuse across different auth methods, but the workflow will fail at the `validate-inputs` job if the required secrets for the selected `auth_method` are missing.

## Migrating from the provider-specific workflows

If you are currently using `reusable-terragrunt-plan-only-aws.yml`, replace the `uses` reference and add `auth_method: "aws"`. Several other inputs have been consolidated down to a `tg_dir` input:

```yaml
# Before
uses: launchbynttdata/launch-workflows/.github/workflows/reusable-terragrunt-plan-only-aws.yml@ref
with:
  git_branch: ${{ github.head_ref }}
  assume_role_arn: "arn:aws:iam::123456789012:role/my-assumed-role"
  environment: production
  region: us-east-2
  env_id: "000"

# After
uses: launchbynttdata/launch-workflows/.github/workflows/reusable-terragrunt-plan-only.yml@ref
with:
  auth_method: "aws"
  git_branch: ${{ github.head_ref }}
  tg_dir: "platform/production/us-east-2/000"
  aws_auth_region: "us-east-2"
  aws_assume_role_arn: "arn:aws:iam::123456789012:role/my-assumed-role"
```

If you are currently using `reusable-terragrunt-plan-only-azure.yml`, replace the `uses` reference and add `auth_method: "azure"`. Several other inputs have been consolidated down to a `tg_dir` input:

```yaml
# Before
uses: launchbynttdata/launch-workflows/.github/workflows/reusable-terragrunt-plan-only-azure.yml@ref
with:
  git_branch: ${{ github.head_ref }}
  environment: production
  region: eastus2
  env_id: "000"
secrets: inherit # pragma: allowlist secret

# After
uses: launchbynttdata/launch-workflows/.github/workflows/reusable-terragrunt-plan-only.yml@ref
with:
  auth_method: "azure"
  git_branch: ${{ github.head_ref }}
  tg_dir: "platform/production/eastus2/000"
secrets: inherit # pragma: allowlist secret
```
