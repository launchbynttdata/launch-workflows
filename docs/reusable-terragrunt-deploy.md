# Terragrunt Environment Deployment

Plans and deploys a single Terragrunt environment. This workflow unifies the previously separate `reusable-terragrunt-deploy-aws.yml` and `reusable-terragrunt-deploy-azure.yml` workflows into a single, provider-agnostic workflow controlled by the `auth_method` input.

`auth_method` accepts a comma-delimited list of authentication methods, enabling multiple providers to be authenticated simultaneously (e.g. `"aws,github"` to authenticate with AWS via OIDC while also generating a GitHub App token for private module access). It can also be omitted or set to an empty string to run Terragrunt without any authentication.

## Usage

### AWS authentication (`auth_method: aws`)

Use this when your environment is deployed to AWS. Authentication is performed via OIDC using a role you provide (or set the `DEPLOY_ROLE_ARN` variable on your environment or repository).

Let's say we have a repository with the structure shown below:

> ./
>   platform/
>     sandbox/
>       us-east-2/
>         000/
>     test/
>       us-east-2/
>         000/
>     production/
>       us-east-2/
>         000/

If we wanted to deploy our production environment when a release was published, we might create a workflow like so:

```yaml
name: Release to Production

on:
  release:
    types:
      - published

jobs:
  deploy-production:
    permissions:
      contents: read
      id-token: write
      statuses: write
    uses: launchbynttdata/launch-workflows/.github/workflows/reusable-terragrunt-deploy.yml@ref
    with:
      auth_method: "aws"
      git_branch: ${{ github.head_ref }}
      tf_version: '1.5.5'
      tg_version: '0.54.11'
      gh_environment: 'production'
      tg_dir: 'platform/production/us-east-2/000'
      aws_auth_region: 'us-east-2'
      aws_assume_role_arn: 'arn:aws:iam::123456789012:role/my-assumed-role'
```

If you wanted to deploy all regions and instances within a given environment -- say you had production resources that were in us-east-1 and us-east-2 -- then you can utilize GitHub's matrix functionality and our [workflow to create a matrix for Terragrunt](./reusable-github-matrix-tg.md).

### Azure authentication (`auth_method: azure`)

Use this when your environment is deployed to Azure. Authentication is performed via OIDC using Azure credentials passed as secrets.

Let's say we have a repository with the structure shown below:

> ./
>   platform/
>     sandbox/
>       eastus2/
>         000/
>     test/
>       eastus2/
>         000/
>     production/
>       eastus2/
>         000/

If we wanted to deploy our production environment when a release was published, we might create a workflow like so:

```yaml
name: Release to Production

on:
  release:
    types:
      - published

jobs:
  deploy-production:
    permissions:
      contents: read
      id-token: write
      statuses: write
    uses: launchbynttdata/launch-workflows/.github/workflows/reusable-terragrunt-deploy.yml@ref
    with:
      auth_method: "azure"
      git_branch: ${{ github.head_ref }}
      tf_version: '1.5.5'
      tg_version: '0.77.22'
      gh_environment: 'production'
      tg_dir: 'platform/production/eastus2/000'
    secrets: inherit # pragma: allowlist secret

    # For usage outside the launchbynttdata organization, pass the secrets explicitly:
    # secrets:
    #   TERRAGRUNT_DEPLOY_AZURE_CLIENT_ID: ${{ secrets.your_azure_client_id_secret }}
    #   TERRAGRUNT_DEPLOY_AZURE_TENANT_ID: ${{ secrets.your_azure_tenant_id_secret }}
    #   TERRAGRUNT_DEPLOY_AZURE_SUBSCRIPTION_ID: ${{ secrets.your_azure_subscription_id_secret }}
```

If you wanted to deploy all regions and instances within a given environment -- say you had production resources that were in eastus and eastus2 -- then you can utilize GitHub's matrix functionality and our [workflow to create a matrix for Terragrunt](./reusable-github-matrix-tg.md). For more information on OIDC setup for Azure, see the [azure/login action documentation](https://github.com/Azure/login?tab=readme-ov-file#login-with-openid-connect-oidc-recommended).

### GitHub App authentication (`auth_method: github`)

Use this when your Terragrunt configuration needs to apply changes via the GitHub Terraform Provider. Authentication is performed using a GitHub App, which generates a short-lived token:

```yaml
name: Release to Production

on:
  release:
    types:
      - published

jobs:
  deploy-production:
    permissions:
      contents: read
      id-token: write
      statuses: write
    uses: launchbynttdata/launch-workflows/.github/workflows/reusable-terragrunt-deploy.yml@ref
    with:
      auth_method: "github"
      git_branch: ${{ github.head_ref }}
      tf_version: '1.5.5'
      tg_version: '0.54.11'
      gh_environment: 'production'
      tg_dir: 'platform/production/us-east-2/000'
      github_app_id: "123456"
    secrets:
      TERRAGRUNT_DEPLOY_GITHUB_APP_SECRET: ${{ secrets.MY_GITHUB_APP_PRIVATE_KEY }}
```

Replace `ref` with an appropriate ref to this repository, and replace the `TERRAGRUNT_DEPLOY_GITHUB_APP_ID` input and `TERRAGRUNT_DEPLOY_GITHUB_APP_SECRET` secret with values for your GitHub App.

Note that this does not perform the checkout with the obtained GitHub token, it is only used in the context of applying GitHub resources with Terragrunt!

### Combined authentication (e.g. `auth_method: "aws,github"`)

Use this when your infrastructure is deployed across multiple Terraform providers. The example below might deploy a new GitHub repository (authenticating as a GitHub App to use the GitHub API) and then stand up some additional resources for that repository in AWS. Both AWS OIDC and a GitHub App token will be configured:

```yaml
name: Release to Production

on:
  release:
    types:
      - published

jobs:
  deploy-production:
    permissions:
      contents: read
      id-token: write
      statuses: write
    uses: launchbynttdata/launch-workflows/.github/workflows/reusable-terragrunt-deploy.yml@ref
    with:
      auth_method: "aws,github"
      git_branch: ${{ github.head_ref }}
      tf_version: '1.5.5'
      tg_version: '0.54.11'
      gh_environment: 'production'
      tg_dir: 'platform/production/us-east-2/000'
      aws_auth_region: 'us-east-2'
      aws_assume_role_arn: 'arn:aws:iam::123456789012:role/my-assumed-role'
      github_app_id: "123456"
    secrets:
      TERRAGRUNT_DEPLOY_GITHUB_APP_SECRET: ${{ secrets.MY_GITHUB_APP_PRIVATE_KEY }}
```

## Inputs

| Name | Description | Required | Default |
|------|-------------|----------|---------|
| `auth_method` | Comma-delimited list of authentication methods to use. Valid values are `aws`, `azure`, and `github` (e.g. `"aws"`, `"aws,github"`, `"aws,azure"`). Omit or pass an empty string to run without authentication. | No | `""` |
| `git_branch` | Branch triggering this deployment. | Yes | — |
| `tf_version` | Version of Terraform to utilize. | Yes | `1.5.5` |
| `tg_version` | Version of Terragrunt to utilize. | Yes | — |
| `gh_environment` | GitHub Environment to deploy to (e.g. test, production). Leave blank to use repo-level values. | No | — |
| `tg_dir` | Folder containing the Terragrunt configuration to deploy (relative to the repository root). | Yes | — |
| `aws_auth_region` | AWS region to use for authentication. Required when `auth_method` includes `aws`. | No | — |
| `aws_assume_role_arn` | ARN of the role to assume prior to Terragrunt invocation. Required when `auth_method` includes `aws`. Defaults to `vars.DEPLOY_ROLE_ARN`. | No | `${{ vars.DEPLOY_ROLE_ARN }}` |
| `github_app_id` | GitHub App ID for authentication. Required when `auth_method` includes `github`. Defaults to `vars.TERRAGRUNT_DEPLOY_GITHUB_APP_ID`. | No | `${{ vars.TERRAGRUNT_DEPLOY_GITHUB_APP_ID }}` |
| `before_plan_commands` | Commands to run prior to executing Terragrunt plan. | No | `""` |
| `before_deploy_commands` | Commands to run prior to executing Terragrunt apply. | No | `""` |
| `before_shared_commands` | Commands to run prior to both Terragrunt plan and apply (after the specific before commands). | No | `""` |
| `after_plan_commands` | Commands to run after executing Terragrunt plan. | No | `""` |
| `after_deploy_commands` | Commands to run after executing Terragrunt apply. | No | `""` |
| `after_shared_commands` | Commands to run after both Terragrunt plan and apply (after the specific after commands). | No | `""` |

## Outputs

| Name | Description |
|------|-------------|
| `terraform_outputs` | JSON string containing all Terraform outputs from the deployment (base64 encoded). |

## Secrets

| Name | Description | Required |
|------|-------------|----------|
| `TERRAGRUNT_DEPLOY_AZURE_CLIENT_ID` | Azure client ID for OIDC authentication. Required when `auth_method` includes `azure`. | No* |
| `TERRAGRUNT_DEPLOY_AZURE_TENANT_ID` | Azure tenant ID for OIDC authentication. Required when `auth_method` includes `azure`. | No* |
| `TERRAGRUNT_DEPLOY_AZURE_SUBSCRIPTION_ID` | Azure subscription ID for OIDC authentication. Required when `auth_method` includes `azure`. | No* |
| `TERRAGRUNT_DEPLOY_GITHUB_APP_SECRET` | GitHub App private key for authentication. Required when `auth_method` includes `github`. | No* |

*These secrets are declared as optional at the workflow level to allow reuse across different auth methods, but the workflow will fail at the `validate-inputs` job if the required secrets for the selected `auth_method` are missing.

## Migrating from the provider-specific workflows

If you are currently using `reusable-terragrunt-deploy-aws.yml`, replace the `uses` reference and add `auth_method: "aws"`. Several other inputs have been consolidated down to a `tg_dir` input:

```yaml
# Before
uses: launchbynttdata/launch-workflows/.github/workflows/reusable-terragrunt-deploy-aws.yml@ref
with:
  git_branch: ${{ github.head_ref }}
  tf_version: '1.5.5'
  tg_version: '0.54.11'
  environment: 'production'
  region: 'us-east-2'
  env_id: '000'

# After
uses: launchbynttdata/launch-workflows/.github/workflows/reusable-terragrunt-deploy.yml@ref
with:
  auth_method: "aws"
  git_branch: ${{ github.head_ref }}
  tf_version: '1.5.5'
  tg_version: '0.54.11'
  gh_environment: 'production'
  tg_dir: 'platform/production/us-east-2/000'
  aws_auth_region: 'us-east-2'
```

If you are currently using `reusable-terragrunt-deploy-azure.yml`, replace the `uses` reference and add `auth_method: "azure"`. Several other inputs have been consolidated down to a `tg_dir` input:

```yaml
# Before
uses: launchbynttdata/launch-workflows/.github/workflows/reusable-terragrunt-deploy-azure.yml@ref
with:
  git_branch: ${{ github.head_ref }}
  tf_version: '1.5.5'
  tg_version: '0.77.22'
  environment: 'production'
  region: 'eastus2'
  env_id: '000'
secrets: inherit # pragma: allowlist secret

# After
uses: launchbynttdata/launch-workflows/.github/workflows/reusable-terragrunt-deploy.yml@ref
with:
  auth_method: "azure"
  git_branch: ${{ github.head_ref }}
  tf_version: '1.5.5'
  tg_version: '0.77.22'
  gh_environment: 'production'
  tg_dir: 'platform/production/eastus2/000'
secrets: inherit # pragma: allowlist secret
```
