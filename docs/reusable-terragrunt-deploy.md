# Terragrunt Environment Deployment

Plans and deploys a single Terragrunt environment.

In order for us to assume an AWS role to perform the deployment, we need to have an Environment configured on the repository implementing this workflow, and that Environment needs to contain an environment variable named DEPLOY_ROLE_ARN, containing the ARN of an IAM role with rights to deploy your resources.

## Usage

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
    uses: launchbynttdata/launch-workflows/.github/workflows/reusable-terragrunt-deploy.yml@<commit hash>
    with:
      tf_version: '1.5.5'
      tg_version: '0.54.11'
      environment: 'production'
      region: 'us-east-2'
      env_id: '000'
```

If you wanted to deploy all regions and instances within a given environment -- say you had production resources that were in us-east-1 and us-east-2 -- then you can utilize GitHub's matrix functionality and our [workflow to create a matrix for Terragrunt](./reusable-github-matrix-tg.md).
