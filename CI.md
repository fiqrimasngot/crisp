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

The image is private by default. Publication does not establish kubelet pull
access. The deployment worker must verify package access from the target
namespace and use an approved read-only pull credential if needed. Do not make
the repository or package public to work around an access problem.

## Protection and release gates

The GitHub branch-protection and ruleset APIs returned HTTP 403 for this private
repository: its plan requires an upgrade for those features. Do not claim that
required checks or review approvals are enforced. The owner must enable an
eligible plan, then require the exact check name `test` on main. A real reviewer
must be chosen before adding required approvals; the only observed collaborator
was the owner. Keep the repository private unless separately authorized.

Model-owner confirmation of the canonical artifact, authoritative attribute
labels and independent labelled acceptance data remain outside CI. Attributes
stay omitted and the UI identifies this as an unvalidated candidate. Read the
README before approving any use beyond an internal candidate evaluation.

GitOps deployment is a separate step in `fiqrimasngot/kube`: review the successful
release record, update the internal-only workload to that exact digest, reconcile
Flux and verify routed real inference. Do not grant this workflow cluster access
or reuse a broad token for cross-repository writes. Roll back by restoring the
previous approved image digest in Git, then verify Flux and the workload again.
