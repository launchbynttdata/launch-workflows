# Security Policy

## Supported Versions

Security fixes are developed on `main` and published in a new release. The latest published release is supported. Older releases may contain known security defects and are not patched in place.

Callers should pin reusable workflows and actions to a reviewed release tag or full commit SHA and update that reference when a security release is published.

## Reporting a Vulnerability

Report suspected vulnerabilities through [GitHub private vulnerability reporting](https://github.com/launchbynttdata/launch-workflows/security/advisories/new).

Do not disclose the vulnerability in a public issue, pull request, discussion, or other public channel before the maintainers have assessed it.

Include enough information to reproduce and evaluate the issue:

- The affected workflow, action, script, and release or commit.
- The caller event and permissions required to reach the vulnerable behavior.
- Whether untrusted pull-request content or another untrusted input is involved.
- The credentials, repository operations, infrastructure, or other assets at risk.
- The observed result and the result you expected.
- A minimal reproduction, with secrets and sensitive data removed.

Do not include live credentials, private keys, production data, or unnecessary exploit details.

Before submitting a report, review the [open issues](https://github.com/launchbynttdata/launch-workflows/issues) to see whether the concern has already been reported publicly.

Do not add sensitive details to an existing public issue. If the issue does not already describe the security implications, continue using private vulnerability reporting.

## System and Scope

This repository provides reusable GitHub Actions workflows, composite actions, and supporting scripts. Calling repositories run this code in their own GitHub Actions context.

Depending on the selected workflow and caller configuration, an invocation may:

- Receive repository or environment secrets.
- Request GitHub OIDC tokens and short-lived cloud credentials.
- Create GitHub App tokens.
- Read or modify pull requests, approvals, releases, labels, or commit statuses.
- Run Terraform or Terragrunt against cloud infrastructure.
- Execute checked-out code and caller-supplied command hooks.

The security boundary covers code and configuration maintained in this repository. A finding may occur in a calling repository when the root cause is an unsafe default, missing validation, permission error, or boundary violation in this repository.

## Threat Model and Trust Boundaries

Treat the following as untrusted unless the calling repository establishes a stronger boundary:

- Workflow inputs and outputs.
- Pull-request metadata, branch names, commit data, and repository contents.
- Files and programs executed after checkout.
- API, command-line tool, and external-service responses.
- Cache and artifact contents.
- Values derived from forks or other contributors.

Important trust boundaries include:

- The caller-to-reusable-workflow interface.
- Checked-out repository content entering shell commands and tools.
- GitHub Actions exchanging OIDC tokens for cloud credentials.
- Workflows using GitHub tokens or GitHub App tokens to change repository state.
- Command-hook inputs entering a shell.
- Third-party actions and downloaded tools executing on a runner.

Callers remain responsible for their event triggers, job permissions, environment protections, cloud role trust policies, GitHub App permissions, secret inheritance, runner security, and selected workflow reference.

## Security Invariants

The following properties must hold:

- Untrusted values are validated before they influence paths, refs, API requests, credentials, or executable syntax.
- Shell steps pass external values through quoted environment variables or positional arguments. They do not interpolate untrusted values into shell programs.
- Workflows request only the permissions needed for their documented behavior.
- OIDC credentials, GitHub App tokens, and other privileged credentials are created only when the selected operation requires them.
- Secrets and credentials are not written to logs, outputs, caches, artifacts, or other persistent locations.
- Untrusted fork or pull-request code cannot gain access to privileged credentials or mutation capabilities through these workflows.
- Third-party actions used in privileged contexts are pinned to reviewed, immutable commit SHAs.
- Automated approval logic fails closed when author identity, commit provenance, or policy evaluation is incomplete or ambiguous.
- Commit statuses and approvals apply to the intended repository, pull request, and current commit. A skipped or incomplete check is not reported as successful verification.
- Deployment and destruction operations remain within the caller-selected, authorized environment and respect configured environment protections.

The documented before-and-after command inputs intentionally execute shell code. They are safe only when their values are controlled by trusted workflow authors; callers must not populate them from untrusted pull-request data.

## Reportable Findings and Severity Context

Report vulnerabilities that can realistically cause:

- Execution of attacker-controlled code with secrets or privileged credentials.
- Unauthorized cloud, repository, release, approval, or status changes.
- Bypass of an authentication, authorization, environment, or approval boundary.
- Credential disclosure or persistence.
- Use of credentials for a different repository, ref, commit, environment, or cloud identity than intended.
- A false successful status or approval that permits an unsafe merge or deployment.
- Path, argument, expression, or command injection across a documented trust boundary.

Severity depends on reachability and the caller's effective permissions. Cross-repository compromise, credential theft, production infrastructure changes, or reliable approval bypasses generally warrant higher severity than issues limited to non-sensitive output or an already-authorized caller.

## Out of Scope and Limitations

The following are not vulnerabilities in this repository by themselves:

- An overprivileged cloud role, GitHub App, token, or runner configured solely by a caller.
- A caller passing untrusted data to a documented command hook.
- A caller deliberately granting secrets to untrusted pull-request code.
- Defects confined to a third-party service or action that this repository invokes safely.
- General GitHub Actions availability, runner capacity, or cloud service cost.

These cases become reportable when this repository's implementation defeats a documented safe configuration, provides an unsafe default, exposes credentials, or crosses a boundary the caller cannot reasonably enforce.

Assessment of a suspected vulnerability may require the caller workflow, permissions, event payload, environment protections, and cloud identity trust configuration. Source inspection alone may be insufficient to establish reachability or impact.
