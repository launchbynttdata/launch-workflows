# Label a Pull Request using the Branch Name strategy

> [!NOTE]
> This workflow uses [release-drafter](https://github.com/release-drafter/release-drafter) for most of the heavy lifting. The behaviors described here are a result of a release-drafter.yml configuration similar to [the one used in this repository](../.github/release-drafter.yml). This is a highly flexible workflow, and if you wish to deviate from our standard approach, a review of the capabilities and [configuration options](https://github.com/release-drafter/release-drafter?tab=readme-ov-file#configuration-options) is highly encouraged.

Applies labels to your pull request using the Branch Naming strategy, that is,

| Branch Prefix                         | SemVer Change Type | Version Increment Example | Notes                                                                                                                       |   |
|---------------------------------------|--------------------|---------------------------|-----------------------------------------------------------------------------------------------------------------------------|---|
| bug/, chore/, fix/, patch/, dependabot/               | PATCH              | 1.0.0 -> 1.0.1            | This is the default change type. If you submit a branch without a matching prefix, it is assumed to be a PATCH update.      |   |
| feature/                              | MINOR              | 1.0.1 -> 1.1.0            |                                                                                                                             |   |
| bug!/, chore!/, fix!/, patch!/, feature!/ | MAJOR              | 1.1.0 -> 2.0.0            | The presence of the exclamation mark (`!`) in the prefix denotes a breaking change, which will increment the major version. |   |

## Usage

To label your PR:

```yaml
on:
  pull_request:
    types: [opened, reopened, synchronize]

jobs:
  check:
    name: "Label Pull Request"
    permissions:
      contents: read
      issues: write
      pull-requests: write
    uses: launchbynttdata/launch-workflows/.github/workflows/reusable-pr-label-by-branch.yml@ref
    secrets: inherit


```

Be sure you replace `ref` with an appropriate ref to this repository.
