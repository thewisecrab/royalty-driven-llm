# RDLLM First 5 Minutes

> **Synthetic demo:** the bundled corpus and economics are fictional test data.
> This walkthrough does not call an external model provider or move money.

This is the lowest-friction path. Do this before reading the long docs.

## 0. What You Are About To See

RDLLM will generate a demo answer and print:

- the answer;
- `Sources`, meaning the works that support the answer;
- `Claim Evidence`, meaning which source supports each claim;
- `support`, `text_match`, and `allocation`, meaning how the source was used and
  what share would be proposed for review;
- `disagreement=passed`, meaning no visible source plainly contradicted the
  claim.

You do not need an API key for this demo.

## 1. Install

From the repository root:

```bash
python -m pip install .
```

Expected result: the command finishes without errors and installs commands such
as `rdllm`, `rdllm-first-run`, and `rdllm-service`.

## 2. Run The Easiest Demo

```bash
rdllm-first-run
```

Expected first line:

```text
rdllm_first_run status: passed
```

If you see that, RDLLM is working locally.

## 3. Read The Output Like A User

Look for this shape:

```text
Royalty-aware answer:
...
Sources
[S1] ... support=... text_match=... payout=...
Claim Evidence
[C1] S1; ... disagreement=passed; ... Evidence: ...
```

What it means:

- `[S1]` is a visible source label.
- `support` is how strongly that source supports the answer.
- `text_match` is observable text overlap with the registered source.
- `allocation` is a candidate share in the synthetic creator pool, not a payment.
- `Claim Evidence` shows which source supports each claim.
- `disagreement=passed` means the visible sources did not plainly contradict the
  claim.
- `settlement` explains whether the candidate is held, escrowed, or eligible for
  an externally attested processor. RDLLM never executes a payment itself.

## 4. Try The CLI Directly

```bash
rdllm answer "How should AI prove attribution?"
```

This prints the same kind of sourced answer. Change the prompt later; first make
sure the default path works.

## 5. Run The Self-Test

```bash
rdllm-operator-doctor
```

Expected line:

```text
operator_doctor status: passed
```

This proves the installed package can load schemas, sample data, verifier logic,
and runtime readiness checks.

## 6. When You Want HTTP API Calls

Start the local service:

```bash
export RDLLM_SERVICE_TOKEN="${RDLLM_SERVICE_TOKEN:-rdllm-local-dev-token}"
export RDLLM_SERVICE_TOKEN_SHA256="$(python - <<'PY'
import hashlib
import os
print(hashlib.sha256(os.environ["RDLLM_SERVICE_TOKEN"].encode()).hexdigest())
PY
)"
rdllm-service --config examples/service_config.json
```

Then use [API client examples](../examples/api_clients/README.md).

## Common Problems

### `rdllm-first-run: command not found`

Run the install command again from the repository root:

```bash
python -m pip install .
```

If you are inside a virtual environment, activate it before installing.

### `ModuleNotFoundError: rdllm`

You are running from a checkout without installing. Either install with
`python -m pip install .` or run commands with `PYTHONPATH=src`.

### The output has no `Sources`

Use the default first-run prompt first:

```bash
rdllm-first-run
```

Custom prompts can retrieve fewer registered sources depending on the sample
corpus.

## Where To Go Next

- [GitHub Start Here](github_start_here.md)
- [Public explainer](public_explainer.md)
- [Live use cases](../examples/live_use_cases/README.md)
- [API client examples](../examples/api_clients/README.md)
- [Project attribution map](project_attribution.md)
