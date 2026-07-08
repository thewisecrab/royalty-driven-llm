# Hosting

This repository is ready to host as a static GitHub Pages site. The hosted site
publishes the human-facing documentation in `docs/`, the public schema set, and
the well-known RDLLM discovery/proof surface under `docs/.well-known/`.

## GitHub Pages

1. Push the repository to GitHub.
2. In repository settings, enable Pages with GitHub Actions as the source.
3. The `pages` workflow uploads `docs/` and deploys it.
4. The landing page is `docs/index.html`.
5. The public discovery entry point is `/.well-known/rdllm.json`.

Before pushing, run:

```bash
PYTHONPATH=src python tools/hosting_export.py --write
PYTHONPATH=src python tools/hosted_surface_audit.py
PYTHONPATH=src python tools/public_surface_privacy_audit.py
PYTHONPATH=src python tools/github_readiness.py
PYTHONPATH=src python tools/docs_link_audit.py
PYTHONPATH=src python tools/production_readiness.py
PYTHONPATH=src python tools/production_profile_matrix.py
PYTHONPATH=src python tools/deployment_audit.py
PYTHONPATH=src python tools/service_smoke.py
PYTHONPATH=src python tools/service_load_smoke.py
PYTHONPATH=src python tools/provider_live_smoke.py
PYTHONPATH=src python tools/security_abuse_smoke.py
```

The check verifies required GitHub workflows, Pages links, source-package pruning,
well-known artifact export freshness, artifact presence, and GitHub-safe file
sizes. The hosted-surface audit additionally verifies that `/.well-known/rdllm.json`
matches `artifacts/discovery_manifest.json`, every advertised artifact path
resolves under `docs/.well-known/rdllm/`, all manifest schema paths resolve from
the hosted root, and hosted artifact hashes match the manifest catalog. The
public-surface privacy audit verifies that hosted artifacts and mirrored schemas
do not expose prompts, raw source text, private reasoning, secrets, customer
records, payment details, or payout account data.

## Static Host

Any static host can serve the `docs/` directory. No server-side runtime is
required.

```bash
python3 -m http.server 8000 --directory docs
```

Then open `http://localhost:8000/`.

## Published Surfaces

- `docs/index.html`: hosted documentation entry point
- `docs/.well-known/rdllm.json`: hosted RDLLM discovery manifest
- `docs/.well-known/rdllm/`: hosted public proof artifacts advertised by the
  discovery manifest
- `docs/docs/schemas/`: schema mirror used so the discovery manifest's
  source-tree schema paths resolve unchanged on GitHub Pages
- `docs/mechanism.md`: technical design
- `docs/evidence.md`: evidence map
- `docs/recent_research.md`: research and provider-source notes
- `docs/provider_onboarding.md`: provider adapter requirements
- `docs/provider_compatibility_matrix.md`: supported provider families and
  required native surfaces
- `docs/deployment.md`: service deployment, readiness probes, and rollout checks
- `docs/service_api.md`: HTTP service API, auth, metrics, and smoke test
- `docs/production_readiness.md`: production-grade operator controls
- `docs/operator_runbook.md`: deployment, incident, settlement, and upgrade
  procedures
- `docs/release_checklist.md`: release verification steps
- `docs/schemas/`: public JSON schemas

Reference artifacts remain in `artifacts/` in the GitHub repository as the
authoritative generated proof pack. The hosting export mirrors the public
artifact catalog into `docs/.well-known/rdllm/` so static hosting can serve the
same discovery paths.
