# Builder → Intelligent Contracts — paste-ready text

Fill the portal form after you deploy in Studio with your own wallet. Replace the placeholders at the bottom. Do not submit until the contract address and explorer transaction are real.

---

## Contribution type

Builder → Intelligent Contracts (Contract Deployed)

## Title

Public Source Oracle: reusable Intelligent Contract with independent leader/validator web consensus

## Description (portal, keep under 1,000 characters)

```
Public Source Oracle is a reusable GenLayer Intelligent Contract. It attests values from public HTTPS JSON sources through leader/validator consensus, then stores the agreed result on-chain.

Anyone registers a named feed (URL, JSON path, value kind, numeric tolerance). Anyone can call settle(feed_id). The leader fetches the URL and extracts the path. Each validator independently fetches the same URL, walks the same path, and compares the extracted decision value. Number feeds allow basis-point tolerance for source drift. Text is whitespace-normalized. Booleans must match exactly. HTTP 4xx, 5xx, parse failures, and missing paths are classified so validators can agree or disagree correctly. State is written only after consensus.

This is not a hello-world contract, not an “AI decides” demo, and not a frontend product. Other callers read attested state through get_feed / get_last_value.

Source: contracts/public_source_oracle.py
Tests: pytest tests/direct/ -v
```

Character count of the block above is under 1,000. If the form is tighter, use the short version:

```
Reusable GenLayer Intelligent Contract that attests public JSON sources. settle() runs gl.vm.run_nondet_unsafe: leader and validators each fetch the same HTTPS URL, extract the same JSON path, and compare the value (numeric bps tolerance, exact text/bool). Typed Feed state is updated only after consensus. No UI, no LLM judgement demo, no other chain.
```

## Longer note (if the form has a free-text / context field)

Public Source Oracle exists because GenLayer can fetch the web inside consensus, and ordinary VMs cannot.

The non-deterministic block is explicit:

- `leader_fn` calls `gl.nondet.web.get`, parses JSON, walks a dotted path (`data.price`, `rates.0.usd`), and returns a canonical record `{kind, number, text, boolean, http_status}`.
- `validator_fn` does not inspect only the leader’s shape. If the leader returned a value, the validator re-runs the same extraction against a fresh fetch and calls `_results_equivalent`. If the leader errored, the validator re-runs and compares classified error prefixes (`[EXPECTED]`, `[EXTERNAL]`, `[TRANSIENT]`, `[PARSE]`).
- Storage is copied to locals before the nondet block. `self.feeds[id]` is mutated only after `run_nondet_unsafe` returns.

That is the Equivalence Principle used as a reusable oracle, not as a chatbot.

On-chain state is a `TreeMap[u256, Feed]` plus a name index. Each feed has creator, URL, path, kind, tolerance, pause flag, last attested value, last HTTP status, and settlement count. Numbers are stored as micro-units (`value * 1_000_000`) so storage never depends on floats.

Access control is narrow: anyone registers, anyone settles an active feed, only the creator or contract owner can pause/resume.

## Evidence items

Add each as Description + URL. File uploads are not supported.

1. **Source contract**
   - Description: Intelligent Contract source (`contracts/public_source_oracle.py`) with custom `run_nondet_unsafe` leader/validator pair.
   - URL: `<public repository URL>`

2. **README**
   - Description: State layout, consensus rule, Studio deploy steps, and how to run tests.
   - URL: `<public repository URL>/blob/<branch>/README.md`

3. **Tests**
   - Description: Direct-mode tests for registration, settlement, and validator agreement/disagreement (`direct_vm.run_validator()`).
   - URL: `<public repository URL>/tree/<branch>/tests/direct`

4. **Deployed contract**
   - Description: Contract deployed to GenLayer from Studio with my wallet.
   - URL: `<GenLayer explorer contract URL>`

5. **Settle transaction**
   - Description: `settle` transaction that ran leader/validator consensus and wrote attested state.
   - URL: `<GenLayer explorer transaction URL>`

## After you deploy, paste these locally before submitting

```
Network: <GenLayer testnet name shown in Studio>
Contract address: <0x...>
Deploy transaction: <explorer URL>
Settle transaction: <explorer URL>
Public repository: <URL>
```

## Reviewer walkthrough (optional, if asked)

1. Deploy `contracts/public_source_oracle.py` (no constructor args).
2. Call `register_feed("btc-usd", "https://<json-api>", "data.price", "number", 200)`.
3. Call `get_feed_id("btc-usd")` then `get_feed(id)`: status `active`, `settlement_count` 0.
4. Call `settle(id)`.
5. Call `get_last_value(id)`: `kind=number`, `value` in micro-units, `http_status=200`, `settlement_count=1`.
6. Pause as a second wallet → revert `not authorized`. Pause as creator → `settle` reverts `feed is paused`.

## What not to claim

Do not describe this as a dApp, dashboard, or AI judge. The submission is one Intelligent Contract plus tests.
