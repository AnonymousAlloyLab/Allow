# Private AI assistance in the workbench

Allow now connects the React assistant to Spring and the existing LangGraph
workflow. The first integration supports complete models in the block grammar,
source proposals and explanations. It is a private pilot: AI defaults to `OFF`,
and anonymous installations cannot enable it. RAG, partial-slot completion,
public paid assistance and commercial release remain separate work.

The [JSON supplement](../spec/ai-system-integration.json) received six exact-hash
reviews before implementation. Its [24-theorem Lean model](../formal/Allow/AiSystemIntegration.lean)
passed two matching clean builds. The model checks finite protocol rules; it does
not prove the implementation, model intent, anonymization secrecy or deployment.

## Using the assistant

Open a saved model in an AI-enabled private installation. Enter an intent and
choose **Prepare payload**. Spring validates the current draft, replaces its
declaration and binder names with anonymous slots, and presents the exact request
that would be sent. Comments and display names are excluded from model context;
the intent is shown verbatim and can itself contain identifying information.

Choose **Send this exact payload** to approve that attempt. The model has no tools,
SQL client or file/network action authority. Generated source is checked using
the existing scoped Java worker capacity. If deterministic verification fails,
the graph prepares one repair with a closed diagnostic code. That second attempt
requires another explicit approval. Authentication, timeout, stale context,
worker unavailability and uncertain dispatches stop instead of retrying.

Review the named source and its validation result. **Apply to draft** obtains a
short-lived receipt and rechecks the current browser draft before one local edit.
**Undo AI edit** restores the prior draft, including comments, if no intervening
edit/save/navigation invalidates it. **Save version** is a separate action through
the existing commit path. AI never saves an accepted revision automatically.

Reprinted proposals omit comments, which the review states explicitly. Unsupported
source, partial models, new declaration inventories and unsafe name restoration
are rejected instead of being disclosed or guessed. Explanations remain labeled
AI suggestions and have no Apply action. Successful type checking does not prove
that an edit meets the user's intent.

## Configuration and deployment

The transfer package uses the existing IIS frontend/reverse proxy and Linux/WSL
Spring backend. The AI process is a private child with framed stdin/stdout IPC;
there is no additional public port or database connection. All document SQL still
passes through SQLeanParser. The [operator guide](../deploy/README.md#optional-private-ai-runtime)
describes the offline hash-locked optional runtime and private configuration.

Modes are `OFF`, `FIXTURE` and `REMOTE_ASSISTED`. FIXTURE deliberately returns an
invalid candidate followed by the original valid model, so the real verification
and fresh-consent repair flow can be tested without paying a provider. Its UI is
explicitly labeled and its accounting is isolated from remote accounting.
REMOTE_ASSISTED fixes `https://api.openai.com/v1/responses` and `gpt-6.1-sol`.
The operator must supply reviewed terms/tariff identifiers and a credential outside
the installation; the archive never contains a key. Core dumps are disabled for
credential-bearing launch. Neither model content nor credentials enter the budget
journal, and external tracing/checkpoints are disabled.

The lifetime journal ceiling defaults to 100000 micro-USD and may be configured up
to 10000000 before journal initialization. Each call reserves 50000 conservatively.
The ceiling and FIXTURE/REMOTE profile are bound into durable state; restarting or
changing configuration cannot reset them. An uncertain dispatch retains its
reservation. These are tariff-dependent reservations, not observed provider bills.

One job may run at a time. Each job has at most two calls and expires 60 seconds
after creation, including disclosure waits. Receipts last at most 10 seconds and
cannot outlive the job. Cancellation, expiry and terminal states clear retained
provider buffers; intentional editor drafts and their local undo state follow the
editor's lifecycle. Mandatory process cleanup can exceed the return deadline,
but ownership is held until cleanup completes. Manual document operations preempt
conflicting assistant work without opening a second validator lane.

## API and implementation map

Authenticated private routes live under `/api/ai/v1`: `GET /config`, `POST /jobs`,
`GET /jobs/{id}`, and `POST /jobs/{id}/disclosure`, `/cancel`, `/approve`.
Closed input fields are specified in the JSON contract. The job view additionally
includes `beforeSource`, the checked source for the exact submitted candidate, so
block edits never compare against a stale textarea preview. GET does not dispatch.
Unknown fields, noncanonical IDs, query parameters, stale bindings and duplicate
disclosure identities cannot broaden authority.

- Spring `AiService`, `AiJob`, `AiProcess` and `AiConfiguration` own authority,
  job lifecycle, credentials, IPC and apply receipts.
- `AnonymousModel` performs structural slot/name mapping after validation.
- `services/ai/` supplies strict IPC, immutable-ceiling accounting and isolated
  runtime checks around the tested `retrieval/allow_ai` LangGraph library.
- `frontend/src/document/ai/` owns preview, polling, review and atomic local apply/undo.

No private corpus or embedding pipeline is changed by this integration. A future
retrieval mode still needs its separate purpose/disclosure rights and provenance
checks. A delivered receipt cannot instantly observe later remote revocation;
known invalidation denies local apply, and every later server action/Save checks
current authority and head.

## Acceptance and reproduction

The [integration report](../gates/ai-system-v1/report.json) binds final source,
test, browser and package evidence. The isolated component's successful live
GPT-6.1 Sol test remains recorded separately; fixture/browser tests do not count
as paid model quality or performance evaluation.

```bash
# Existing provisioned retrieval environment; no live provider credential.
.tools/retrieval-venv/bin/python -B -W error -m unittest discover -s services/ai/tests -v
/usr/bin/python3 -B -m unittest discover -s deploy/linux -p 'test_ai_runtime.py' -v

# Against an explicitly disposable PRIVATE/FIXTURE installation only:
/usr/bin/python3 -B scripts/test_ai_http.py \
  --base http://127.0.0.1:54415 --token-file /private/test-token \
  --report /private/ai-http-result.json
```

The HTTP test creates an authored document and retains its ordinary immutable
history. It checks exact create replay, anonymous payloads, two distinct approvals,
real scoped Java verification, restored names, idempotent receipts and unchanged
accepted revision after approval. Native Windows/WSL/IIS deployment, public abuse
controls, constrained-host performance and commercial acceptance remain open.
