# Get Custom Properties Action

This action retrieves custom properties from a GitHub repository using the GitHub API. Custom properties are organization-defined metadata that can be applied to repositories for classification, automation, and policy enforcement.

## Behavior

This action will:
1. Call the GitHub API to retrieve all custom properties applied to the specified repository
2. Return the properties as a JSON object that can be used in subsequent workflow steps

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `owner` | The owner (organization or user) of the repository | No | `${{ github.repository_owner }}` |
| `repo` | The name of the repository | No | `${{ github.event.repository.name }}` |
| `github_token` | GitHub token for API access | No | `${{ github.token }}` |

## Outputs

| Output | Description |
|--------|-------------|
| `properties` | JSON object containing all custom properties applied to the repository |

## Usage

### Basic Usage

When used in a workflow, all inputs are optional. The action defaults to the current repository and automatic GITHUB_TOKEN:

```yaml
jobs:
  your-job:
    runs-on: ubuntu-latest
    steps:
      - name: Get Custom Properties
        id: props
        uses: launchbynttdata/launch-workflows/.github/actions/get-custom-properties@main

      - name: Use Properties
        run: |
          echo "Properties: ${{ steps.props.outputs.properties }}"
```

### Query a Different Repository

To retrieve properties from a different repository:

```yaml
- name: Get Custom Properties
  id: props
  uses: launchbynttdata/launch-workflows/.github/actions/get-custom-properties@main
  with:
    owner: "my-org"
    repo: "my-repo"
```

### Parse Properties in Workflow

You can use `jq` to parse specific properties from the output:

```yaml
- name: Get Custom Properties
  id: props
  uses: launchbynttdata/launch-workflows/.github/actions/get-custom-properties@main

- name: Check Environment Property
  run: |
    ENVIRONMENT=$(echo '${{ steps.props.outputs.properties }}' | jq -r '.[] | select(.property_name == "environment") | .value')
    echo "Environment: $ENVIRONMENT"
```

## Required Permissions

The default `GITHUB_TOKEN` has sufficient permissions to read custom properties for the repository where the workflow runs. When querying a different repository, the token needs "Metadata" repository permission (read).

## Response Format

The API returns an array of property objects:

```json
[
  {
    "property_name": "environment",
    "value": "production"
  },
  {
    "property_name": "team",
    "value": "platform"
  }
]
```
