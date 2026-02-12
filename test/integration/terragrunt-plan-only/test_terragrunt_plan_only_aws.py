import os

import pytest

from src.launch_github import (
    WorkflowRunConclusion,
    WorkflowRunStatus,
    branch_created,
    get_workflow_run_logs,
    populate_file,
    workflow_run_completed,
    workflow_run_created,
)

LAUNCH_WORKFLOWS_REF_TO_TEST = os.environ.get("LAUNCH_WORKFLOWS_REF_TO_TEST", "main")

PULL_REQUEST_WORKFLOW = f"""
name: Plan AWS Environment

on:
  pull_request:
    types: [opened, synchronize, reopened]
    branches: [ "**" ]

jobs:
  get-tg-versions:
    permissions:
      contents: read
    uses: launchbynttdata/launch-workflows/.github/workflows/reusable-terragrunt-versions.yml@{LAUNCH_WORKFLOWS_REF_TO_TEST}

  build-matrix:
    permissions:
      contents: read
    uses: launchbynttdata/launch-workflows/.github/workflows/reusable-github-matrix-tg.yml@{LAUNCH_WORKFLOWS_REF_TO_TEST}
    with:
      platform_environment: production

  call-terragrunt-plan:
    needs: [get-tg-versions, build-matrix]
    permissions:
      contents: read
      id-token: write
    strategy:
      fail-fast: false
      matrix: ${{{{ fromJson(needs.build-matrix.outputs.matrix) }}}}

    uses: launchbynttdata/launch-workflows/.github/workflows/reusable-terragrunt-plan-only.yml@{LAUNCH_WORKFLOWS_REF_TO_TEST}
    with:
      git_branch: ${{{{ github.head_ref }}}}
      tf_version: ${{{{ needs.get-tg-versions.outputs.tf_version }}}}
      tg_version: ${{{{ needs.get-tg-versions.outputs.tg_version }}}}
      assume_role_arn: "arn:aws:iam::123456789012:role/my-assumed-role"
      environment: ${{{{ matrix.terragrunt_environment.environment }}}}
      region: ${{{{ matrix.terragrunt_environment.region }}}}
      env_id: ${{{{ matrix.terragrunt_environment.instance }}}}
    secrets: inherit
"""

ROOT_HCL = """
locals {
  # After initial apply, changes to these naming values will result in the creation of a new state bucket!
  logical_product_family  = "test"
  logical_product_service = "tg_plan"

  # Don't modify the locals below this line.
  name_dash                = replace("${trimspace(local.logical_product_family)}_${trimspace(local.logical_product_service)}", "_", "-")
  name_hash                = substr(sha256(local.name_dash), 0, 8)
  resource_names_strategy  = local.account_name == "sandbox" ? "minimal_random_suffix" : "standard"
  relative_path            = path_relative_to_include()
  path_parts               = split("/", local.relative_path)
  account_name             = local.path_parts[2]
  region                   = local.path_parts[3]
  environment_instance     = basename(local.relative_path)
  git_branch               = get_env("GIT_BRANCH", "")
  current_user             = get_env("USER", "")
  state_path_override      = get_env("TERRAGRUNT_STATE_PATH_OVERRIDE", "") # useful for cleaning up ephemeral environments if a workflow fails, otherwise should be left blank.
  bucket                   = "${local.name_dash}-${local.account_name}-${local.region}-${local.name_hash}-tfstate"
  repo_name                = basename(abspath("${get_path_to_repo_root()}"))
  state_filename_ephemeral = "${local.account_name}/${coalesce(local.state_path_override, local.git_branch, local.current_user, "/")}/${local.environment_instance}/terraform.tfstate"
  state_filename_persist   = "${local.account_name}/${local.environment_instance}/terraform.tfstate"
}

# Generate the AWS provider settings
generate "provider" {
  path      = "provider.tf"
  if_exists = "overwrite"
  contents  = <<EOF
provider "aws" {
  region  = "${local.region}"

  default_tags {
    tags = {
      Organization = var.organization_tag
      Repository = coalesce(var.repository_tag, "${basename(abspath(dirname(find_in_parent_folders("root.hcl"))))}")
      Branch = var.branch_tag
      CommitHash = var.commit_hash_tag
    }
  }
}

provider "aws" {
  alias   = "global"
  region  = "us-east-1"

  default_tags {
    tags = {
      Organization = var.organization_tag
      Repository = coalesce(var.repository_tag, "${basename(abspath(dirname(find_in_parent_folders("root.hcl"))))}")
      Branch = var.branch_tag
      CommitHash = var.commit_hash_tag
    }
  }
}

variable "organization_tag" {
  type = string
  default = "launchbynttdata"
}

variable "repository_tag" {
  type = string
  default = ""
}

variable "branch_tag" {
  type = string
  default = "RUN OUTSIDE PIPELINE"
}

variable "commit_hash_tag" {
  type = string
  default = "RUN OUTSIDE PIPELINE"
}

EOF
}

# Generates the config file for s3 backend
remote_state {
  backend = "s3"
  generate = {
    path      = "backend.tf"
    if_exists = "overwrite"
  }
  config = {
    bucket       = "${local.bucket}"
    key          = local.account_name == "sandbox" ? local.state_filename_ephemeral : local.state_filename_persist
    region       = "${local.region}"
    encrypt      = true
    use_lockfile = true
  }
}

inputs = {
  logical_product_family  = local.logical_product_family
  logical_product_service = local.logical_product_service
  class_env               = local.account_name
  region                  = local.region
  resource_names_strategy = local.resource_names_strategy
}
"""

ENVIRONMENT_HCL = """
include "root" {
  path = find_in_parent_folders("root.hcl")
}

locals {
  git_tag = "main"
}

# terraform {
#   source = "git::https://github.com/launchbynttdata/launch-terraform-registry.git?ref=${local.git_tag}"
# }

terraform {
  source = "../../../../infrastructure/"
}
"""

VARIABLES_TF = """
variable "resource_names_map" {
  description = "A map of key to resource_name that will be used by tf-launch-module_library-resource_name to generate resource names"
  type = map(object({
    name       = string
    max_length = optional(number, 60)
    region     = optional(string, "us-east-2")
  }))

  default = {
    layer = {
      name       = "lyr"
      max_length = 80
    }
  }
}

variable "resource_names_strategy" {
  type        = string
  description = "Strategy to use for generating resource names, taken from the outputs of the naming module, e.g. 'standard', 'minimal_random_suffix', 'dns_compliant_standard', etc."
  nullable    = false
  default     = "minimal_random_suffix"
}

variable "logical_product_family" {
  type        = string
  description = <<EOF
    (Required) Name of the product family for which the resource is created.
    Example: org_name, department_name.
  EOF
  nullable    = false
  default     = "launch"

  validation {
    condition     = can(regex("^[A-Za-z0-9_]+$", var.logical_product_family))
    error_message = "logical_product_family may only contain letters, numbers, and underscores"
  }
}

variable "logical_product_service" {
  type        = string
  description = <<EOF
    (Required) Name of the product service for which the resource is created.
    For example, backend, frontend, middleware etc.
  EOF
  nullable    = false
  default     = "example"

  validation {
    condition     = can(regex("^[A-Za-z0-9_]+$", var.logical_product_service))
    error_message = "logical_product_service may only contain letters, numbers, and underscores"
  }
}

variable "class_env" {
  type        = string
  description = "(Required) Environment where resource is going to be deployed. For example: dev, qa, uat"
  nullable    = false
  default     = "sandbox"

  validation {
    condition     = can(regex("^[A-Za-z0-9_]+$", var.class_env))
    error_message = "class_env may only contain letters, numbers, and underscores"
  }
}

variable "instance_env" {
  type        = number
  description = "Number that represents the instance of the environment."
  nullable    = false
  default     = 0

  validation {
    condition     = var.instance_env >= 0 && var.instance_env <= 999
    error_message = "instance_env must be between 0 and 999, inclusive."
  }
}

variable "instance_resource" {
  type        = number
  description = "Number that represents the instance of the resource."
  nullable    = false
  default     = 0

  validation {
    condition     = var.instance_resource >= 0 && var.instance_resource <= 100
    error_message = "instance_resource must be between 0 and 100, inclusive."
  }
}
"""

MAIN_TF = """
module "resource_names" {
  source  = "terraform.registry.launch.nttdata.com/module_library/resource_name/launch"
  version = "~> 2.0"

  for_each = var.resource_names_map

  region                  = join("", split("-", each.value.region))
  class_env               = var.class_env
  cloud_resource_type     = each.value.name
  instance_env            = var.instance_env
  instance_resource       = var.instance_resource
  maximum_length          = each.value.max_length
  logical_product_family  = var.logical_product_family
  logical_product_service = var.logical_product_service
}

module "sqs_queue" {
  source  = "terraform.registry.launch.nttdata.com/module_library/sqs_queue/aws
  version = "~> 1.0"

  name                    = module.resource_names["queue"][var.resource_names_strategy]
}
"""


@pytest.fixture(scope="function")
def terragrunt_skeleton(temporary_repository):
    with branch_created(temporary_repository, "main") as main:
        populate_file(
            repository=temporary_repository,
            path="README.md",
            content="# Test Repository\nThis is a test repository for integration testing.",
            branch=main.name,
            commit_message="Add README file",
        )
        populate_file(
            repository=temporary_repository,
            path="terragrunt.hcl",
            content=ROOT_HCL,
            branch=main.name,
        )
        populate_file(
            repository=temporary_repository,
            path="platform/envs/production/us-east-1/sandbox/terragrunt.hcl",
            content=ENVIRONMENT_HCL,
            branch=main.name,
            commit_message="Add terragrunt.hcl file",
        )
        populate_file(
            repository=temporary_repository,
            path="platform/infrastructure/variables.tf",
            content=VARIABLES_TF,
            branch=main.name,
            commit_message="Add variables.tf file",
        )
        populate_file(
            repository=temporary_repository,
            path="platform/infrastructure/main.tf",
            content=MAIN_TF,
            branch=main.name,
            commit_message="Add main.tf file",
        )
        populate_file(
            repository=temporary_repository,
            path=".github/workflows/plan.yml",
            content=PULL_REQUEST_WORKFLOW,
            branch=main.name,
            commit_message="Add GitHub workflow for Terragrunt plan",
        )
    with branch_created(
        temporary_repository, "feature/terragrunt-plan-only"
    ) as feature_branch:
        populate_file(
            repository=temporary_repository,
            path="README.md",
            content="# Test Repository\nMaking a change to run the plan workflow.",
            branch=feature_branch.name,
            commit_message="Update README file",
        )

        label_workflow = temporary_repository.get_workflow(id_or_file_name="plan.yml")

        with workflow_run_created(
            label_workflow, branch=feature_branch.name
        ) as label_run:
            with workflow_run_completed(label_run) as status:
                if status != WorkflowRunStatus.COMPLETED:
                    raise AssertionError(
                        f"Workflow run for {feature_branch.name} did not complete successfully: {status}"
                    )
                if label_run.conclusion != WorkflowRunConclusion.SUCCESS:
                    logs = get_workflow_run_logs(label_run, drop_log_timestamps=True)
                    raise AssertionError(
                        f"Workflow run for {feature_branch.name} did not succeed as expected: {label_run.conclusion}\nLogs:\n{logs}"
                    )
