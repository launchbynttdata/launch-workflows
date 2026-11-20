# Rebuild Caches

Rebuilds and persists the GitHub Actions caches used by `pre-commit` and `asdf install` so that downstream pull request workflows (e.g. [Pre-Commit Checks](reusable-pre-commit-checks.md)) start with a primed cache and complete more quickly.

This workflow is intended to run on `push` to your default branch. When it runs, it:

- Installs `pre-commit` (via [`uv`](https://docs.astral.sh/uv/) and the [`pre-commit-uv`](https://github.com/tox-dev/pre-commit-uv) plugin), executes `pre-commit install-hooks` to populate hook environments, and saves `~/.cache/pre-commit` to the cache keyed on the hash of `.pre-commit-config.yaml`.
- Installs all tools declared in `.tool-versions` via [`asdf`](https://asdf-vm.com/) and saves `~/.asdf/installs` and `~/.asdf/plugins` to the cache keyed on the hash of `.tool-versions`.

Because the cache keys match those used by [`reusable-pre-commit-checks.yml`](../.github/workflows/reusable-pre-commit-checks.yml), pull request runs will find a cache hit until either `.pre-commit-config.yaml` or `.tool-versions` changes.

## Usage

Add the following workflow to your repository (suggested name: `.github/workflows/push-rebuild-caches.yml`):

```yaml
name: Rebuild Caches

on:
  push:
    branches: [main]
    paths:
      - .pre-commit-config.yaml
      - .tool-versions
  workflow_dispatch:

jobs:
  rebuild-caches:
    name: Rebuild Caches
    permissions:
      contents: read
    uses: launchbynttdata/launch-workflows/.github/workflows/reusable-rebuild-caches.yml@ref
```

Be sure you replace `ref` with an appropriate ref to this repository.

The `paths` filter ensures the workflow only runs when `.pre-commit-config.yaml` or `.tool-versions` actually changes — the cache keys are derived from the hashes of these files, so other pushes to `main` would just rebuild an identical cache.

To rebuild only one of the two caches, set the other input to `false`:

```yaml
jobs:
  rebuild-caches:
    name: Rebuild Caches
    permissions:
      contents: read
    uses: launchbynttdata/launch-workflows/.github/workflows/reusable-rebuild-caches.yml@ref
    with:
      cache_precommit: true
      cache_asdf: false
```

> [!TIP]
> Pair this workflow with [Pre-Commit Checks](reusable-pre-commit-checks.md) on pull requests. The PR workflow will restore the caches produced here, avoiding the cost of reinstalling hook environments and `asdf` tools on every PR run.

> [!NOTE]
> GitHub Actions caches are scoped by branch. Running this workflow on your default branch makes the resulting caches available to all PR branches (which fall back to the default branch's cache on a miss). Running it on a feature branch will only benefit that branch.

## Inputs

| Input | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `cache_precommit` | `boolean` | No | `true` | Rebuild and persist the cache for `pre-commit` hook environments (`~/.cache/pre-commit`). |
| `cache_asdf` | `boolean` | No | `true` | Rebuild and persist the cache for `asdf`-installed tools (`~/.asdf/installs` and `~/.asdf/plugins`). |

## Secrets

This workflow does not consume any secrets.

## Required Permissions

The calling workflow must grant the following permissions:

| Permission | Level | Reason |
|------------|-------|--------|
| `contents` | `read` | Check out the repository so that `.pre-commit-config.yaml` and `.tool-versions` are available. |
