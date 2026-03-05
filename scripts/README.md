# scripts

Maintenance scripts for rolling out and managing the `launch-workflows` reusable workflows across `tf-*` repos in the `launchbynttdata` GitHub org.

All scripts require the [`gh` CLI](https://cli.github.com/) to be authenticated.

## sync_workflows.py

Syncs CI workflow files, `dependabot.yml`, `release-drafter.yml`, `Makefile`, and `.tool-versions` to `tf-*` repos. Migrates legacy repos from `actions-lcaf` workflows to `launch-workflows` reusable workflows, and keeps already-migrated repos on the latest version.

The script embeds canonical templates for each file and validates them against the `lcaf-skeleton-terraform` repo before applying. If the skeleton has changed, the script exits with an error until the templates and blob SHAs are updated.

```sh
# Preview changes for a single repo
python scripts/sync_workflows.py --repo tf-aws-module_primitive-sqs_queue --dry-run

# Apply changes (clones, branches, commits, pushes, opens a PR)
python scripts/sync_workflows.py --repo tf-aws-module_primitive-sqs_queue

# Apply to all tf-* repos
python scripts/sync_workflows.py --all --version 0.14.2
```

## create_missing_releases.py

Backfills GitHub releases for repos that have semver tags but no releases. This is needed because the old `increment_tagged_version` workflow created tags on merge but never created GitHub releases, while the new `launch-workflows` release pipeline requires a release to exist.

```sh
# Preview what would be created
python scripts/create_missing_releases.py --all --dry-run

# Create missing releases
python scripts/create_missing_releases.py --all
```
