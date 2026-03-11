# Investigation Report: PR Workflow Failures
**Date:** March 9, 2026  
**Investigator:** GitHub Copilot  
**Scope:** Comparing passing Azure PRs vs failing AWS PRs for launch-workflows v0.14.2 migration

---

## Executive Summary

Investigation of 15 failing AWS Terraform module PRs and 6 passing Azure Terraform module PRs revealed that the original `make lint` failures (TFLint config path issue) have been **resolved**. The remaining failures are now occurring at the `make test` step due to actual Terraform test failures, not workflow configuration issues.

---

## Original Issue

### Reported Problem
- 15 AWS Terraform module PRs were failing workflow checks
- All PRs were migrating to `launch-workflows@0.14.2`

### Initial Root Cause (Now Resolved)
The original failures were caused by TFLint unable to find config file:
```
Failed to load TFLint config; failed to load file: open ../../.tflint.hcl: no such file or directory
```

This was traced to `lcaf-component-terraform/tasks/modules/Makefile` which had a path fallback that didn't work correctly in all directory structures.

---

## Investigation: Passing vs Failing Comparison

### Workflow Comparison

| Aspect | AWS Workflow | Azure Workflow |
|--------|-------------|----------------|
| Reusable Workflow | `reusable-terraform-check-aws.yml` | `reusable-terraform-check-azure.yml` |
| LCAF Version | `refs/tags/1.8.1` | `refs/tags/1.8.1` |
| Steps | checkout → asdf → cache → lint → AWS creds → test | checkout → asdf → cache → lint → Azure login → test |
| Primary Difference | Uses `aws-actions/configure-aws-credentials` | Uses `azure/login` |

### Key Finding
Both workflows are **structurally identical** - they use the same LCAF version, same Makefile targets, and same step sequence. The cloud authentication is the only difference.

---

## Current Status of Original 15 PRs

### PRs Now Passing ✅
| Repository | PR # | Status |
|------------|------|--------|
| tf-aws-module_primitive-virtual_node | #3 | All checks pass |
| tf-aws-module_primitive-ecs_cluster | #5 | All checks pass |

### PRs Still Failing ❌ (Different Root Cause)
| Repository | PR # | Failing Step | Issue |
|------------|------|--------------|-------|
| tf-aws-module_primitive-appmesh_gateway_route | #4 | `make test` | Terraform test failure |
| tf-aws-module_collection-ecr | #7 | `make test` | ECR repository collision (`ecr-test` already exists) |

### Repos Not Found (Possibly Deleted)
- tf-aws-module_primitive-service_discovery_service
- tf-aws-module_primitive-service_discovery_http_namespace
- tf-aws-module_primitive-ecs_task_definition
- tf-aws-module_primitive-appmesh_virtual_gateway
- tf-aws-module_primitive-appmesh_virtual_router
- tf-aws-module_primitive-appmesh_virtual_service
- tf-aws-module_primitive-ecs_capacity_provider

---

## Passing Azure PRs (Reference)

All 6 Azure PRs successfully pass all checks:

| Repository | PR # | Status |
|------------|------|--------|
| tf-azurerm-module_primitive-log_analytics_workspace | #12 | ✅ Pass |
| tf-azurerm-module_primitive-private_dns_zone | #9 | ✅ Pass |
| tf-azurerm-module_primitive-private_endpoint | #11 | ✅ Pass |
| tf-azurerm-module_primitive-resource_group | #16 | ✅ Pass |
| tf-azurerm-module_primitive-virtual_network | #12 | ✅ Pass |
| tf-azurerm-module_primitive-subnet | #8 | ✅ Pass |

---

## Technical Details

### Workflow Files in PR Branch
```
.github/workflows/
├── pull-request-label.yml          # Uses reusable-pr-label-by-branch.yml
├── pull-request-terraform-check-aws.yml  # Uses reusable-terraform-check-aws.yml
└── release-publish.yml             # Uses reusable-release-on-merge.yml
```

### Successful Step Sequence (Example from tf-azurerm-module_primitive-log_analytics_workspace)
1. ✅ Set up job
2. ✅ Checkout
3. ✅ Setup asdf
4. ✅ Restore cached asdf tools
5. ✅ Setup Repository for Checks
6. ✅ Cache asdf tools
7. ✅ **make lint** ← Previously failing, now passing
8. ✅ Azure login
9. ✅ **make test**
10. ✅ Complete job

---

## Remaining Issues & Recommendations

### 1. ECR Repository Collision
**Repo:** `tf-aws-module_collection-ecr` PR #7  
**Error:** `RepositoryAlreadyExistsException` for `ecr-test`  
**Action Required:** Delete orphaned ECR repository `ecr-test` from AWS account `020127659860`

```bash
aws ecr delete-repository --repository-name ecr-test --region us-east-2 --force
```

### 2. AppMesh Gateway Route Test Failure
**Repo:** `tf-aws-module_primitive-appmesh_gateway_route` PR #4  
**Failing Step:** `make test`  
**Action Required:** Review Terraform test output for actual test assertion failures

### 3. Missing Repositories
Several repositories from the original list are no longer accessible. Verify if they were:
- Renamed
- Deleted
- Made private

---

## Conclusion

The original TFLint configuration path issue has been resolved (likely through an update to `lcaf-component-terraform`). The remaining failures are legitimate Terraform test failures that need to be addressed on a per-repository basis, not workflow configuration issues.

**No changes were made to launch-workflows during this investigation.**

---

## Appendix: Commands Used

```bash
# Check PR status
gh pr checks <PR#> --repo "launchbynttdata/<repo>"

# Get workflow run details
gh api "repos/launchbynttdata/<repo>/actions/runs/<run_id>/jobs" \
  --jq '.jobs[] | {name, conclusion, steps}'

# Compare workflow files
gh api "repos/launchbynttdata/<repo>/contents/.github/workflows" --jq '.[].name'

# Get LCAF version from Makefile
gh api "repos/launchbynttdata/<repo>/contents/Makefile" --jq '.content' | base64 -d | grep LCAF_COMPONENT_URL
```
