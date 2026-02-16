# Configure an Organization for running Workflow Tests

Our tests will end up creating repositories, and so we isolate them to a particular GitHub Organization. You will need to be an `Owner` of the organization to set this up correctly.

## Ensure the Organization is configured for GitHub Actions

First, enter the Organization's Settings page. Navigate to Actions > General blade and set the following:

- **Policies** must be set to allow usage of our actions from the `launchbynttdata` organization. Additionally, we use third-party actions contained in other organizations, so you must either explicitly allow the third-party actions we use or allow all actions. Since this Organization should be isolated for testing and have no other use, the recommendation is to set `Allow all actions and reusable workflows`.

- **Require actions to be pinned to a full-length commit SHA** must NOT be set.

- **Approval for running fork pull request workflows from contributors** should be set to `Require approval for all external contributors`
 
- **Workflow permissions** should be set to `Read repository contents and packages permissions`

- **Allow GitHub Actions to create and approve pull requests** must NOT be set.

- Ensure you save your changes before continuing!

## Install the GitHub App

Our workflow testing utilizes a [GitHub App](https://github.com/apps/launch-workflow-testing) to provide authentication and manage permissions. You will need to install this App to the organization you wish to use.

> [!TIP]
> The basics are now configured for your organization, but there is still work to do. You must configure OIDC between the organization and the cloud providers, which is covered in the [next sections](2-configuring-aws-oidc.md).
