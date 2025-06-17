# Terragrunt Versions

This workflow retrieves the versions of Terragrunt and Terraform from the .tool-versions file, as a precursor to using the [Terragrunt Deploy](./reusable-terragrunt-deploy.md) step to push resources to the cloud.

## Usage

The repository in question must contain a .tool-versions compatible file (the actual filename defaults to .tool-versions and can be overridden).

The example workflow below outputs two versions from our .tool-versions file, contained in `tf_version` and `tg_version`, which are passed to the call-terragrunt-deploy job.

```yaml
name: Your excellent workflow

on:
  pull_request: # or another event of your choosing

jobs:
  get-tg-versions:
    permissions:
      contents: read
    uses: launchbynttdata/launch-workflows/.github/workflows/reusable-terragrunt-versions.yml@<commit hash>

  build-matrix:
    permissions:
      contents: read
    uses: launchbynttdata/launch-workflows/.github/workflows/reusable-github-matrix-tg.yml@<commit hash>
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

    uses: launchbynttdata/launch-workflows/.github/workflows/reusable-terragrunt-deploy.yml@0.1.3
    with:
      tf_version: ${{ needs.get-tg-versions.outputs.tf_version }}
      tg_version: ${{ needs.get-tg-versions.outputs.tg_version }}
      environment: ${{ matrix.terragrunt_environment.environment }}
      region: ${{ matrix.terragrunt_environment.region }}
      env_id: ${{ matrix.terragrunt_environment.instance }}
    secrets: inherit
```
