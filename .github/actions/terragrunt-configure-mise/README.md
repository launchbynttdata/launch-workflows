# (Re-)Configure Mise for Terragrunt Action

We use [gruntwork-io/terragrunt-action](https://github.com/gruntwork-io/terragrunt-action) in our Terragrunt workflows, which uses Mise under the hood to set up its environment. As a compatibility layer between our legacy .tool-versions files for `asdf` (which Mise supports, with some caveats), our Terragrunt actions ask for a tf_version and tg_version input, but a [change to terragrunt-action](https://github.com/gruntwork-io/terragrunt-action/releases/tag/v3.0.0) removed explicit support for Terraform and substituted in support for OpenTofu. We're not ready to make that jump, but we can leverage Mise to install Terraform and set `tf_path` to override the OpenTofu behavior and revert to Terraform.

## Usage

```yaml
- name: Configure Mise
  uses: ./.github/actions/terragrunt-configure-mise
  with:
    tf_version: '1.5.5'
    tg_version: '0.54.11'
```

## Inputs

- `tf_version` (required): Version of Terraform to install (default: `1.5.5`)
- `tg_version` (required): Version of Terragrunt to install (default: `0.54.11`)

## Behavior

This action will:
1. Create a `mise.toml` file with the specified Terraform and Terragrunt versions if one doesn't exist
2. Update an existing `mise.toml` file with the specified versions if it already exists
3. Install `toml-cli` if needed for updating existing configurations

The configured `mise.toml` file will then be used by subsequent `gruntwork-io/terragrunt-action` steps to install the correct tool versions.
