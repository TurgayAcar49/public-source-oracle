# Public Source Oracle

A single reusable [GenLayer](https://docs.genlayer.com/) Intelligent Contract. It attests values from public HTTPS JSON sources through **leader/validator consensus**, then stores the agreed result on-chain.

This repository is the contract, tests, and the English text for a Builder → Intelligent Contracts submission. There is no app UI. Deploy it yourself in [GenLayer Studio](https://studio.genlayer.com/) with your own wallet.

## Why this contract

Ordinary smart contracts cannot fetch the web. A backend can fetch the web, but a single server is not consensus.

`PublicSourceOracle` keeps the non-deterministic step on-chain:

1. Anyone registers a named feed: URL, JSON path, value kind, numeric tolerance.
2. Anyone calls `settle(feed_id)`.
3. The leader fetches the URL and extracts the path.
4. Each validator independently fetches the **same URL**, walks the **same path**, and compares the extracted value.
5. State updates only if a majority accepts the leader result.

Validators do not trust the leader’s JSON shape. They re-run the fetch and compare the decision value.

## State

Each feed is a `Feed` record in `feeds: TreeMap[u256, Feed]`:

| Field | Meaning |
| --- | --- |
| `creator` | Address that registered the feed |
| `name` | Unique feed name |
| `source_url` | HTTPS JSON endpoint |
| `json_path` | Dotted path, for example `data.price` or `rates.0.usd` |
| `value_kind` | `number`, `text`, or `boolean` |
| `tolerance_bps` | Number feeds only. `200` = 2% relative drift |
| `status` | `active` or `paused` |
| `last_number` | Last attested number in micro-units (`value * 1_000_000`) |
| `last_text` | Last attested text |
| `last_bool` | Last attested boolean |
| `last_http_status` | HTTP status from the accepted leader fetch |
| `settlement_count` | Successful settlements |
| `last_error` | Reserved; successful settles clear it |

`feed_ids_by_name` is the O(1) name index. `next_feed_id` is the monotonic id counter. Numeric values are stored as integers so storage stays deterministic.

## Consensus rule

`settle` uses `gl.vm.run_nondet_unsafe(leader_fn, validator_fn)`.

- Leader and validator both call `gl.nondet.web.get(url)` inside the non-deterministic block.
- Storage is not read or written inside that block. URL, path, kind, and tolerance are copied to locals first. Writes happen after consensus.
- **Number:** relative tolerance in basis points. `0` means exact micro-unit match.
- **Text:** whitespace-normalized exact match.
- **Boolean:** exact match.
- HTTP 4xx is `[EXTERNAL]` and must match exactly.
- HTTP 5xx / status `0` is `[TRANSIENT]`; both transient → agree, transaction still reverts so state does not change.
- Invalid JSON is `[PARSE]`.
- Missing path or wrong type is `[EXPECTED]`.

A validator that only checked “the leader returned a number” would not be consensus. This validator produces its own extraction and compares it.

## Public methods

Write:

- `register_feed(name, source_url, json_path, value_kind, tolerance_bps)`
- `pause_feed(feed_id)` / `resume_feed(feed_id)` — creator or contract owner
- `settle(feed_id)` — anyone, active feeds only

View:

- `get_owner()`, `get_feed_count()`, `has_feed(name)`, `get_feed_id(name)`
- `get_feed(feed_id)`, `get_last_value(feed_id)`

## Run tests

Python 3.12+:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
genvm-lint check contracts/public_source_oracle.py
pytest tests/direct/ -v
```

Direct-mode tests run in-memory. They mock `gl.nondet.web.get` and exercise `direct_vm.run_validator()` so agreement, in-tolerance drift, and disagreement are all checked without Studio.

## Deploy in Studio

1. Open [studio.genlayer.com](https://studio.genlayer.com/) and connect your wallet.
2. New contract → paste `contracts/public_source_oracle.py` (or Add From File).
3. Constructor has no arguments. Deploy.
4. `register_feed` with an HTTPS JSON URL you control or a public API.
5. `settle` that feed id.
6. Read `get_feed` / `get_last_value`.

Constructor detection: `__init__(self)` takes no parameters.

Example number feed:

- name: `btc-usd`
- source_url: a public HTTPS JSON price endpoint
- json_path: `data.price` (adjust to the payload)
- value_kind: `number`
- tolerance_bps: `200`

Example exact text feed:

- json_path: `state`
- value_kind: `text`
- tolerance_bps: `0`

Keep `json_path` on **stable** fields. Do not attest timestamps, request ids, or counters that change between leader and validator fetches unless the tolerance is meant to absorb that.

## Portal form

Paste-ready English copy lives in [`FORM.md`](FORM.md). Add the Studio contract address and explorer transaction after you deploy.

## What this is not

- Not a hello-world storage contract
- Not an “the AI decides” LLM demo
- Not a frontend, dApp, or product shell
- Not a bridge, Arc, Handoff, USDC, or other-chain integration
