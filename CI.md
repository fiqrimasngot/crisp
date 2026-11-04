# CI and image releases

Push reviewed changes to `main`, or dispatch `CI and image release` on `main`.
The workflow tests the real pinned model, builds a container, publishes it to
GHCR, pulls the published digest, and tests that exact image without network
access. It does not deploy to Kubernetes or claim classification accuracy.

## Runner and trust boundary

- `fiqrimasngot/crisp` uses the repository-scoped ARC label `gha-crisp` for
  trusted main-branch work. `fiqrimasngot/kube` keeps its separate `gha-kube`
  label. Neither repository borrows the other's runner registration.
- Pull requests use GitHub-hosted `ubuntu-latest`, read-only repository access,
  and no package credentials. Non-main manual runs are skipped. There is no
  `pull_request_target` workflow.
- ARC configuration lives in the kube repository at
  `kubernetes/apps/arc-systems/gha-runner-scale-set/app/crisp-helmrelease.yaml`.
  The existing ARC GitHub App was tested against the exact registration-token
  endpoint for each repository. No App credential was copied into this repo.
- The Crisp runner has no mounted Kubernetes service-account token. Its network
  policy permits cluster DNS and public HTTP/HTTPS, not RFC1918 or link-local
  destinations. Docker-in-Docker is privileged: repository write access is a
  trusted boundary, not a sandbox for hostile code.

Run `runner-smoke.yaml` in each repository to check checkout, Python, Docker,
Buildx, DNS and HTTPS. Runner registration alone is not a workflow test.

The Crisp runner scales from zero to one job at a time. BuildKit uses the DinD
host network, which is the runner pod network, not the Kubernetes node network.
The measured pod MTU is 1280 while Docker's default bridge MTU is 1500. The
default bridge caused GHCR TLS handshakes to time out during layer publication;
using the pod network avoids that mismatch without opening cluster egress.

## Checks and publication

The `test` job checks fatal Python lint errors, high-confidence/high-severity
Bandit findings, known Python dependency vulnerabilities, unit/contract tests,
real model loading/inference and the packaged API. Synthetic fixtures test the
code path only; they are not a labelled accuracy evaluation.

All actions use full commit SHAs. Repository Actions settings require SHA
pinning. Checkout does not persist credentials. The workflow starts with only
`contents: read`; only `publish` gets `packages: write`, through its ephemeral
same-repository `GITHUB_TOKEN`. No personal publishing secret is configured.
The `release` environment permits only the `main` branch. Publishing also checks
that the source commit is still the remote main tip. This is not an atomic lock
against later source pushes; promotion must check the intended revision again.

GHCR tags contain the full source commit. Deploy by the registry digest, never
by the tag. BuildKit publishes provenance and an SBOM. The release job retrieves
the registry manifest, checks its SHA-256 against the published digest, verifies
an attestation manifest is present, pulls the digest, and tests actual inference.
It uploads `release.json`, `manifest.json` and `manifest.txt` as the
`release-<source SHA>` Actions artifact. The JSON records the image digest,
source commit, model hash and run URL, and explicitly sets accuracy validation
to false. Failed tests or vulnerability checks prevent publication; a failure
after pushing prevents a successful release handoff, not creation of the image.
Only successful runs are eligible for GitOps promotion.

The source repository is public. Package visibility is separate: publication
does not establish anonymous or kubelet pull access. The deployment worker must
verify package access from the target namespace and use an approved read-only
pull credential if needed. Do not change package visibility as a workaround.

## Protection and release gates

The owner authorized public repository visibility. Branch protection on `main`
requires a pull request and the exact GitHub Actions check `test`, with the
branch up to date before merging. It applies to administrators and prevents
force pushes and branch deletion. No approvals are required: a separate eligible
reviewer must be chosen before requiring them. Repository rulesets are empty.
Private-repository protection has not been verified; a change back to private
visibility requires checking plan eligibility and protection again.

Model-owner confirmation of the canonical artifact, authoritative attribute
labels and independent labelled acceptance data remain outside CI. Attributes
stay omitted and the UI identifies this as an unvalidated candidate. Read the
README before approving any use beyond an internal candidate evaluation.

GitOps deployment is a separate step in `fiqrimasngot/kube`: review the successful
release record, update the internal-only workload to that exact digest, reconcile
Flux and verify routed real inference. Do not grant this workflow cluster access
or reuse a broad token for cross-repository writes. Roll back by restoring the
previous approved image digest in Git, then verify Flux and the workload again.
