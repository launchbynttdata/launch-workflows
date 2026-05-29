# Check a Terraform Module

Performs a series of checks of a Terraform module, including linting the Terraform code via `make lint`, and deploying the example modules to a cloud provider (or no provider at all) and running the golang tests via the `make test` target. This workflow unifies the previously separate `reusable-terraform-check-aws.yml` and `reusable-terraform-check-azure.yml` workflows into a single, provider-agnostic workflow controlled by the `auth_method` input.

This workflow wraps both the `make lint` and `make test` targets in the Makefile.

## Usage

### No cloud authentication (`auth_method: none`)

Use this when your module does not require cloud credentials to run tests (e.g., pure Terraform logic tests, mocked providers):

```yaml
name: Check Terraform Code

on:
  pull_request:
    types: [ opened, reopened, synchronize, ready_for_review ]
    branches: [ main ]

permissions:
  id-token: write
  contents: read

jobs:
  check:
    name: "Check Terraform Code"
    permissions:
      contents: read
      id-token: write
    uses: launchbynttdata/launch-workflows/.github/workflows/reusable-terraform-check.yml@ref
    with:
      auth_method: "none"
```

### AWS authentication (`auth_method: aws`)

Use this when your module deploys example resources to AWS. Authentication is performed via OIDC using a role you provide:

```yaml
name: Check AWS Terraform Code

on:
  pull_request:
    types: [ opened, reopened, synchronize, ready_for_review ]
    branches: [ main ]

permissions:
  id-token: write
  contents: read

jobs:
  check:
    name: "Check AWS Terraform Code"
    permissions:
      contents: read
      id-token: write
    uses: launchbynttdata/launch-workflows/.github/workflows/reusable-terraform-check.yml@ref
    with:
      auth_method: "aws"
      assume_role_arn: "arn:aws:iam::123456789012:role/my-assumed-role" # optional, falls back to TERRAFORM_CHECK_AWS_ASSUME_ROLE_ARN variable
      region: "us-east-2"  # optional, falls back to TERRAFORM_CHECK_AWS_REGION variable
```

Replace `ref` with an appropriate ref to this repository, and replace `assume_role_arn` and `region` with values of your choosing. If either is not provided, they fall back to the `TERRAFORM_CHECK_AWS_ASSUME_ROLE_ARN` and `TERRAFORM_CHECK_AWS_REGION` variables set at the repository, organization, or enterprise level.

### Azure authentication (`auth_method: azure`)

Use this when your module deploys example resources to Azure. Authentication is performed via OIDC using Azure credentials passed as secrets:

```yaml
name: Check Azure Terraform Code

on:
  pull_request:
    types: [ opened, reopened, synchronize, ready_for_review ]
    branches: [ main ]

permissions:
  id-token: write
  contents: read

jobs:
  check:
    name: "Check Azure Terraform Code"
    permissions:
      contents: read
      id-token: write
    uses: launchbynttdata/launch-workflows/.github/workflows/reusable-terraform-check.yml@ref
    with:
      auth_method: "azure"
    secrets: inherit # pragma: allowlist secret

    # For usage outside the launchbynttdata organization, pass the secrets explicitly:
    # secrets:
    #   TERRAFORM_CHECK_AZURE_CLIENT_ID: ${{ secrets.your_azure_client_id_secret }}
    #   TERRAFORM_CHECK_AZURE_TENANT_ID: ${{ secrets.your_azure_tenant_id_secret }}
    #   TERRAFORM_CHECK_AZURE_SUBSCRIPTION_ID: ${{ secrets.your_azure_subscription_id_secret }}
```

Replace `ref` with an appropriate ref to this repository. For more information on OIDC setup for Azure, see the [azure/login action documentation](https://github.com/Azure/login?tab=readme-ov-file#login-with-openid-connect-oidc-recommended).

## Inputs

| Name | Description | Required | Default |
|------|-------------|----------|---------|
| `auth_method` | Authentication method to use. Valid values are `none`, `aws`, and `azure`. | Yes | — |
| `assume_role_arn` | ARN of the IAM role to assume. Required when `auth_method` is `aws`. | No | `${{ vars.TERRAFORM_CHECK_AWS_ASSUME_ROLE_ARN }}` |
| `region` | AWS region to use when deploying test resources. Only used when `auth_method` is `aws`. | No | `${{ vars.TERRAFORM_CHECK_AWS_REGION }}` |

## Secrets

| Name | Description | Required |
|------|-------------|----------|
| `TERRAFORM_CHECK_AZURE_CLIENT_ID` | Azure client ID for OIDC authentication. Required when `auth_method` is `azure`. | No* |
| `TERRAFORM_CHECK_AZURE_TENANT_ID` | Azure tenant ID for OIDC authentication. Required when `auth_method` is `azure`. | No* |
| `TERRAFORM_CHECK_AZURE_SUBSCRIPTION_ID` | Azure subscription ID for OIDC authentication. Required when `auth_method` is `azure`. | No* |

*These secrets are declared as optional at the workflow level to allow reuse in non-Azure contexts, but the workflow will fail at the `validate-inputs` job if any of them are missing when `auth_method` is `azure`.

## Migrating from the provider-specific workflows

If you are currently using `reusable-terraform-check-aws.yml`, replace the `uses` reference and add `auth_method: "aws"`:

```yaml
# Before
uses: launchbynttdata/launch-workflows/.github/workflows/reusable-terraform-check-aws.yml@ref
with:
  assume_role_arn: "arn:aws:iam::123456789012:role/my-assumed-role"

# After
uses: launchbynttdata/launch-workflows/.github/workflows/reusable-terraform-check.yml@ref
with:
  auth_method: "aws"
  assume_role_arn: "arn:aws:iam::123456789012:role/my-assumed-role"
```

If you are currently using `reusable-terraform-check-azure.yml`, replace the `uses` reference and add `auth_method: "azure"`:

```yaml
# Before
uses: launchbynttdata/launch-workflows/.github/workflows/reusable-terraform-check-azure.yml@ref
secrets: inherit # pragma: allowlist secret

# After
uses: launchbynttdata/launch-workflows/.github/workflows/reusable-terraform-check.yml@ref
with:
  auth_method: "azure"
secrets: inherit # pragma: allowlist secret
```

For our Terraform modules, the `auth_method` can be derived automatically from the repository name: repositories prefixed with `tf-aws` use AWS authentication, those prefixed with `tf-az` use Azure authentication, and all others use no authentication:

```yaml
uses: launchbynttdata/launch-workflows/.github/workflows/reusable-terraform-check.yml@ref
with:
  auth_method: ${{ startsWith(github.event.repository.name, 'tf-aws') && 'aws' || startsWith(github.event.repository.name, 'tf-az') && 'azure' || 'none' }}
secrets: inherit # pragma: allowlist secret
```
