# build.postmarketos.org agent guide

This repository keeps downstream image build automation on top of upstream
`postmarketOS/build.postmarketos.org`.

## Branch policy

- `upstream`
  - Exact mirror of `https://gitlab.postmarketos.org/postmarketOS/build.postmarketos.org.git` `master`.
  - No fork-only commits.
  - Refresh by hard reset/force update only.

- `to-upstream`
  - Clean, upstream-safe commit stack only.
  - Exclude local hacks, fork-only CI wiring, and environment workarounds.
  - Recreate from `upstream` when curating a fresh upstreamable stack.

- `main`
  - Downstream branch for fork-specific workflow and local build integration.
  - Rebases on top of `upstream` (or `to-upstream` when carrying pending upstreamable commits).

## Sync expectations

- Nightly sync workflow runs from `main`.
- Sync flow is always:
  1. fetch `upstream/master`
  2. force-refresh `upstream`
  3. rebase `main` on refreshed `upstream`
  4. push updated `main`

## Conflict handling policy

- Never auto-merge divergence in sync automation.
- If rebase conflicts:
  - abort rebase,
  - fail workflow loudly,
  - do not push rewritten `main`.
- Resolve conflicts manually on `main`, then rerun sync.
