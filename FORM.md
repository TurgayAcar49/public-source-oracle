# Builder → Intelligent Contracts — paste-ready text

Copy the blocks below into the GenLayer portal. Evidence must be URLs.

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

If the form is tighter, use this short version:

```
Reusable GenLayer Intelligent Contract that attests public JSON sources. settle() runs gl.vm.run_nondet_unsafe: leader and validators each fetch the same HTTPS URL, extract the same JSON path, and compare the value (numeric bps tolerance, exact text/bool). Typed Feed state is updated only after consensus. No UI, no LLM judgement demo, no other chain.
```

## Longer note (if the form has a free-text / context field)

Public Source Oracle exists because GenLayer can fetch the web inside consensus, and ordinary VMs cannot.

The non-deterministic block is explicit:

- `leader_fn` calls `gl.nondet.web.get`, parses JSON, walks a dotted path (`data.price`, `rates.0.usd`, or `full_name`), and returns a canonical record `{kind, number, text, boolean, http_status}`.
- `validator_fn` does not inspect only the leader’s shape. If the leader returned a value, the validator re-runs the same extraction against a fresh fetch and calls `_results_equivalent`. If the leader errored, the validator re-runs and compares classified error prefixes (`[EXPECTED]`, `[EXTERNAL]`, `[TRANSIENT]`, `[PARSE]`).
- Storage is copied to locals before the nondet block. `self.feeds[id]` is mutated only after `run_nondet_unsafe` returns.

On-chain state is a `TreeMap[u256, Feed]` plus a name index. Each feed has creator, URL, path, kind, tolerance, pause flag, last attested value, last HTTP status, and settlement count. Numbers are stored as micro-units (`value * 1_000_000`) so storage never depends on floats.

Access control is narrow: anyone registers, anyone settles an active feed, only the creator or contract owner can pause/resume.

Studio deployment on Studionet:

- Contract: `0x12e8fFbe898b84Aad0E336120B3Bad443207a445`
- First feed: `oracle-repo` → `https://api.github.com/repos/TurgayAcar49/public-source-oracle` → path `full_name` → kind `text`
- `settle(0)` finalized with consensus Accepted

## Evidence items

Add each as Description + URL.

1. **Source contract**
   - Description: Intelligent Contract source (`contracts/public_source_oracle.py`) with custom `run_nondet_unsafe` leader/validator pair.
   - URL: https://github.com/TurgayAcar49/public-source-oracle/blob/main/contracts/public_source_oracle.py

2. **README**
   - Description: State layout, consensus rule, Studio deploy steps, and how to run tests.
   - URL: https://github.com/TurgayAcar49/public-source-oracle/blob/main/README.md

3. **Tests**
   - Description: Direct-mode tests for registration, settlement, and validator agreement/disagreement (`direct_vm.run_validator()`).
   - URL: https://github.com/TurgayAcar49/public-source-oracle/tree/main/tests/direct

4. **Deployed contract**
   - Description: Public Source Oracle deployed to GenLayer Studionet from Studio with my wallet. Address 0x12e8fFbe898b84Aad0E336120B3Bad443207a445.
   - URL: https://explorer-studio.genlayer.com/address/0x12e8fFbe898b84Aad0E336120B3Bad443207a445

5. **Deploy transaction**
   - Description: Constructor deploy, GenVM SUCCESS, consensus Accepted / FINALIZED.
   - URL: https://explorer-studio.genlayer.com/tx/0x00dea042736f602ba2ec7dfcac92382490c5019939dffb4b82b6eccb00a1fef9

6. **Settle transaction**
   - Description: `settle(0)` ran leader/validator web consensus and wrote attested state. GenVM SUCCESS, consensus Accepted / FINALIZED.
   - URL: https://explorer-studio.genlayer.com/tx/0x7e06f28a3f90942bfe0d37127668c8592913abc0470e462b9da8ab94959ac99c

## Deployment record

```
Network: Studionet (studio.genlayer.com)
Contract address: 0x12e8fFbe898b84Aad0E336120B3Bad443207a445
Deploy transaction: 0x00dea042736f602ba2ec7dfcac92382490c5019939dffb4b82b6eccb00a1fef9
Settle transaction: 0x7e06f28a3f90942bfe0d37127668c8592913abc0470e462b9da8ab94959ac99c
Public repository: https://github.com/TurgayAcar49/public-source-oracle
Explorer (contract): https://explorer-studio.genlayer.com/address/0x12e8fFbe898b84Aad0E336120B3Bad443207a445
Explorer (deploy): https://explorer-studio.genlayer.com/tx/0x00dea042736f602ba2ec7dfcac92382490c5019939dffb4b82b6eccb00a1fef9
Explorer (settle): https://explorer-studio.genlayer.com/tx/0x7e06f28a3f90942bfe0d37127668c8592913abc0470e462b9da8ab94959ac99c
```

## Reviewer walkthrough

1. Deploy `contracts/public_source_oracle.py` (no constructor args).
2. `register_feed("oracle-repo", "https://api.github.com/repos/TurgayAcar49/public-source-oracle", "full_name", "text", 0)`.
3. `get_feed(0)`: status `active`.
4. `settle(0)`.
5. `get_last_value(0)`: `kind=text`, `value=TurgayAcar49/public-source-oracle`.

## What not to claim

Do not describe this as a dApp, dashboard, or AI judge. The submission is one Intelligent Contract plus tests.
