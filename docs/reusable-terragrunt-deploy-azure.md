# Terragrunt Environment Deployment to Azure

Plans and deploys a single Terragrunt environment.

In order for us to authenticate to Azure and obtain a role to perform the deployment, we need to pass three secrets, either using secrets inheritance (if your secret name matches) or rebinding your existing secrets to the names that this workflow expects.

## Usage

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
    uses: launchbynttdata/launch-workflows/.github/workflows/reusable-terragrunt-deploy-azure.yml@ref
    with:
      git_branch: ${{ github.head_ref }}
      tf_version: '1.5.5'
      tg_version: '0.54.11'
      environment: 'production'
      region: 'eastus2'
      env_id: '000'
    secrets: inherit # pragma: allowlist secret

    # Alternately, pass the following secrets:
    #   TERRAGRUNT_DEPLOY_AZURE_CLIENT_ID: ${{ secrets.your_azure_client_id_secret }}
    #   TERRAGRUNT_DEPLOY_AZURE_TENANT_ID: ${{ secrets.your_azure_tenant_id_secret }}
    #   TERRAGRUNT_DEPLOY_AZURE_SUBSCRIPTION_ID: ${{ secrets.your_azure_subscription_id_secret }}
```

If you wanted to deploy all regions and instances within a given environment -- say you had production resources that were in eastus and eastus2 -- then you can utilize GitHub's matrix functionality and our [workflow to create a matrix for Terragrunt](./reusable-github-matrix-tg.md). For more information on OIDC setup for Azure, see the [azure/login action documentation](https://github.com/Azure/login?tab=readme-ov-file#login-with-openid-connect-oidc-recommended).
