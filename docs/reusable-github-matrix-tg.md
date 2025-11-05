# GitHub Matrix Generator

This workflow uses our standard Terragrunt folder structure and produces a matrix of all regions and environment instances within a given environment.

## Usage

Let's say we have a repository with the structure shown below:

```
./
  platform/
    sandbox/
      us-east-1/
        000/
        001/
      us-west-1/
        000/
        001/
```

We want to run Terragrunt to deploy all the environments that are under the "sandbox" environment, so we invoke the workflow as follows:

```yaml
name: Your excellent workflow

on:
  pull_request: # or another event of your choosing

jobs:
  build-matrix:
    permissions:
      contents: read
    uses: launchbynttdata/launch-workflows/.github/workflows/reusable-github-matrix-tg.yml@<commit hash>
    with:
      platform_environment: sandbox
```

This will produce a build-matrix job output that contains the following entries:

```json
{
    "sandbox/us-east-1/000": {
        "environment": "sandbox",
        "region": "us-east-1",
        "instance": "000"
    },
    "sandbox/us-east-1/001": {
        "environment": "sandbox",
        "region": "us-east-1",
        "instance": "001"
    },
    "sandbox/us-east-2/000": {
        "environment": "sandbox",
        "region": "us-east-2",
        "instance": "000"
    },
    "sandbox/us-east-2/001": {
        "environment": "sandbox",
        "region": "us-east-2",
        "instance": "001"
    }
}
```

You can then utilize this matrix in e.g. Terragrunt deployments like so:

```yaml
name: Your excellent workflow

on:
  pull_request:

jobs:
  build-matrix: ... # Same as above
  call-terragrunt-deploy:
    needs: build-matrix
    permissions:
      contents: read
      id-token: write
    strategy:
      fail-fast: false
      matrix: ${{ fromJson(needs.build-matrix.outputs.matrix) }}

    uses: launchbynttdata/launch-workflows/.github/workflows/reusable-terragrunt-deploy.yml@<commit hash>
    with:
      tf_version: '1.5.5'
      tg_version: '0.54.11'
      environment: ${{ matrix.terragrunt_environment.environment }}
      region: ${{ matrix.terragrunt_environment.region }}
      env_id: ${{ matrix.terragrunt_environment.instance }}
```

### Alternate Platform Subfolder

If you need to nest your environments under a subfolder of the platform/ directory, supply the `environments_path` input as demonstrated below:

```
./
  platform/
    terragrunt/
      sandbox/
        us-east-1/
          000/
          001/
        us-west-1/
          000/
          001/
```

```yaml
name: Your excellent workflow

on:
  pull_request: # or another event of your choosing

jobs:
  build-matrix:
    permissions:
      contents: read
    uses: launchbynttdata/launch-workflows/.github/workflows/reusable-github-matrix-tg.yml@<commit hash>
    with:
      environments_path: terragrunt
      platform_environment: sandbox
```