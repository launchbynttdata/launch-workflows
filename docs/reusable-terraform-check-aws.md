# Check a Terraform Module in AWS

Performs a series of checks of a Terraform module, including deploying the example modules to AWS.

This action wraps both the `make lint` and `make test` targets in the Makefile.

## Usage

To check the Terraform code on a PR:

```yaml
name: Check AWS Terraform Code

on:
  pull_request:
    types: [ opened, reopened, synchronize, ready_for_review ]
    branches: [ main ]

permissions:
  id-token: write
  contents: read

jobs:
  check:
    name: "Check AWS Terraform Code"
    permissions:
      contents: read
      id-token: write
    uses: launchbynttdata/launch-workflows/.github/workflows/reusable-terraform-check-aws.yml@ref
    with:
      assume_role_arn: "arn:aws:iam::123456789012:role/my-assumed-role"
      region: "us-east-2"
    secrets: inherit

```

Be sure you replace `ref` with an appropriate ref to this repository, and replace the `assume_role_arn` input with the ARN of your choice.
