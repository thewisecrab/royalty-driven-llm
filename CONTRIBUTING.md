# Contributing

RDLLM is a provider-neutral attribution and settlement proof system. Contributions
should preserve the core invariant: no response may imply source reliance or
creator settlement unless the relevant evidence, rights, provider, and release
gates verify.

## Development Setup

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -U pip
python -m pip install -e ".[dev]"
```

Run the full local verification gate before opening a pull request:

```bash
PYTHONPATH=src python tools/ship_check.py
```

For a faster edit loop:

```bash
PYTHONPATH=src python -m unittest discover -s tests
PYTHONPATH=src python tools/ship_check.py --skip-tests --skip-regenerate
```

## Contribution Rules

- Keep new provider integrations adapter-based. Do not special-case one provider
  path if the same behavior belongs in a universal contract, schema, or fixture.
- Add fail-closed negative fixtures for every new release, attribution, citation,
  safety, meter, or settlement path.
- Public artifacts must not expose prompts, raw source text, evidence text,
  customer records, private reasoning, secrets, API keys, payout account details,
  or other private payloads.
- Update schemas, reference artifacts, certification cases, documentation, and
  tests together when adding a new RDLLM level or public artifact.
- Cite primary sources in `docs/recent_research.md` or `paper/references.bib`
  when a design decision depends on external research, standards, policy, or
  provider API behavior.

## Pull Request Checklist

- The full test suite passes.
- `tools/regenerate_reference_artifacts.py` has been run when artifact-producing
  code changed.
- `tools/ship_check.py` passes.
- New or changed public JSON validates against its schema.
- README and docs explain any new public command, artifact, or provider contract.
- No generated caches, virtual environments, local secrets, or private corpora are
  included.
