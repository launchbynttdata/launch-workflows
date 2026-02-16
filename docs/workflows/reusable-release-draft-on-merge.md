# Draft a Release on Merge to Main

> [!NOTE]
> This workflow uses [release-drafter](https://github.com/release-drafter/release-drafter) for most of the heavy lifting. The behaviors described here are a result of a release-drafter.yml configuration similar to [the one used in this repository](../.github/release-drafter.yml). This is a highly flexible workflow, and if you wish to deviate from our standard approach, a review of the capabilities and [configuration options](https://github.com/release-drafter/release-drafter?tab=readme-ov-file#configuration-options) is highly encouraged.

Creates a Draft release once a PR merges to the main branch. This workflow depends on your Pull Request having an appropriate Label applied to it, which is generally accomplished with something like our [PR labeling workflow](./reusable-pr-label-by-branch.md). Once the PR merges to the main branch, a workflow will run to create a Draft release and bump the version according to the PR(s) that have been merged since the last release.

This workflow is intended for use with software teams that don't release every single update to their codebase as a distinct version -- perhaps they use a cadence aligned with their sprints or quarterly releases -- the draft will aggregate the changes that have been made since the last release and will continually update the projected next version as PRs are merged. In order to release a new version of the software, someone will have to view the draft release and publish it.

The following diagram shows the state of the repository and tags as multiple pull requests are merged prior to a release.

```mermaid
sequenceDiagram
  autonumber
  actor Human
  Note left of Human: Initial tag: 1.0.0
  Human->>Repository: Merge Pull Request 1 (bugfix)
  Repository->>+Release: Draft a release with tag 1.0.1
  Human->>Repository: Merge Pull Request 2 (feature)
  Repository->>Release: Update draft to tag 1.1.0
  Note right of Release: While a draft release exists,<br />it accumulates merged updates and<br />will select the next version according<br />to its component PRs.
  Note left of Human: Decision is made to perform a release
  Human->>Release: Set drafted release to published
  Release->>-Repository: Create tag 1.1.0
  Note right of Release: Publishing a release creates<br /> a new tag and can trigger other<br/>workflows like publishing to a<br />package manager.
  Note left of Human: The cycle restarts with a new<br />draft release ready to be published<br/>whenever the team is ready. 
  Human->>Repository: Merge Pull Request 3 (feature)
  Repository->>Release: Draft a release with tag 1.2.0
```

## Usage

To utilize this reusable workflow, add a new workflow to your repository (suggested name: `.github/workflows/release-draft.yml`):

```yaml
name: Draft Release

on:
  push:
    branches:
      - main

permissions:
  contents: read

jobs:
  draft-release:
    name: "Draft Release on Merge"
    permissions:
      contents: write
      pull-requests: write
    uses: launchbynttdata/launch-workflows/.github/workflows/reusable-release-draft-on-merge.yml@ref
    secrets: inherit # pragma: allowlist secret
```

Be sure you replace `ref` with an appropriate ref to this repository.

If this workflow runs in a repository without a prior Release being published, the first release will always be drafted with version 0.1.0. This is expected behavior and conforms to the SemVer spec, which permits a major version zero. From the SemVer documentation:

> How should I deal with revisions in the 0.y.z initial development phase?
> The simplest thing to do is start your initial development release at 0.1.0 and then increment the minor version for each subsequent release.
>
> How do I know when to release 1.0.0?
> If your software is being used in production, it should probably already be 1.0.0. If you have a stable API on which users have come to depend, you should be 1.0.0. If you’re worrying a lot about backward compatibility, you should probably already be 1.0.0.
>
> Doesn’t this discourage rapid development and fast iteration?
> Major version zero is all about rapid development. If you’re changing the API every day you should either still be in version 0.y.z or on a separate development branch working on the next major version.

Given that this workflow only drafts the release, you may manually edit the drafted release to rename and re-tag it with the version of your choosing if you wanted your first release to reflect 1.0.0 prior to publishing. If you are integrating this workflow into a repository that has tags, but no releases, you will need to perform this manual step to make sure your first true release follows your existing tags. If you integrate this workflow into a repository that has prior releases, the next drafted release will take the prior releases into account and will increment its version according to the tags found on the pull request that initiates the workflow run.
