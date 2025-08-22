# Check a Terraform Module in Azure

Performs a series of checks of a Terraform module, including deploying the example modules to Azure.

This action wraps both the `make lint` and `make test` targets in the Makefile.

## Usage

To check the Terraform code on a PR:

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
    uses: launchbynttdata/launch-workflows/.github/workflows/reusable-terraform-check-azure.yml@ref
    secrets: inherit
    
    # Alternately, pass the following secrets:
    #   TERRAFORM_CHECK_AZURE_CLIENT_ID: ${{ secrets.your_azure_client_id_secret }}
    #   TERRAFORM_CHECK_AZURE_TENANT_ID: ${{ secrets.your_azure_tenant_id_secret }}
    #   TERRAFORM_CHECK_AZURE_SUBSCRIPTION_ID: ${{ secrets.your_azure_subscription_id_secret }}

```

Be sure you replace `ref` with an appropriate ref to this repository. For more information on OIDC setup for Azure, see the [azure/login action documentation](https://github.com/Azure/login?tab=readme-ov-file#login-with-openid-connect-oidc-recommended).
