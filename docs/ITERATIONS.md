# Review and correction log

Builder model: GPT-6.1 SOL / Ultra. Initial implementation and subsequent substantive corrections are recorded separately. This file is evidence, not independent scoring; all axes remain subject to an independent review. Historical verification installs ordinary wheels from exact Git archives, compares source/wheel/site module bytes, executes that revision's actual full unittest suite and runs the same unchanged frozen probe against parent and child.

Initial full implementation: `e445bbc72b3b6b8f6e428f7b834d24d6fbba5168`. Its actual historical suite has **16 tests**, installed SDK/registered CLI demo and fair contrast all return 0. Each correction below has the immediately preceding implementation SHA as its direct parent. Evidence files contain actual commands, captured outputs, archive/wheel SHA256 and each core module's matching Git/archive/wheel/site bytes. The two evaluators share parsing, so parser validation is tested separately.

| Round | Before → direct child | Frozen probe SHA256 | Actual parent/child suite | Probe result |
|---|---|---|---|---|
| 1 | `e445bbc72b3b6b8f6e428f7b834d24d6fbba5168` → `76aa7d2cce61f579c29d8b5ac0753e427cafa2a1` | `632a705c4045d498a48c740f3c2d64d5b9a98397337b9192ab9a85f6d018a109` | 16 / 17 passed | old FAIL / new PASS |
| 2 | `76aa7d2cce61f579c29d8b5ac0753e427cafa2a1` → `35656c47f32a06a05db83008c780ea7493cde72a` | `cab448139f2779f8be31f0f1ebd82c566dcdd8c96a3e9956e874e8e72effcab1` | 17 / 20 passed | old FAIL / new PASS |
| 3 | `35656c47f32a06a05db83008c780ea7493cde72a` → `f24cd5c6e7ea07a6aebd0d5934d963e3339058b6` | `6e620ec94d24c23f7c22e18c46c8d3deaf3a9680667c97887bf30a325b5b5f85` | 20 / 21 passed | old FAIL / new PASS |

All six full historical suites, demos and contrasts returned 0. Historical test counts are per archive, not replaced with the latest count. A later supplemental test/evidence commit `84c59e5088b649f930cd7817613a769c999d5d57` has 23 passing tests and all three frozen probes passing; it is not a fourth correction round.

## 1 — optimum certificate accepted a different claimed source

Review finding: `certify` independently solved the provided model but compared only status/cost/edit lists. It accepted proposals with a tampered source digest, a tampered constraints digest or false `ties_complete`. This made the certificate's source binding materially wrong even though the edit list happened to be optimal for the current source. Initial `apply` already checked bindings; the independent certification path did not.

Substantive code fix: `oracle.py` validates model/normalized-constraint bindings and requires completed tie enumeration. The unchanged [certificate probe](../tests/probes/certificate_binding.py) prints all three tampered variants as accepted on the parent and rejected on the child. [Before evidence](evidence/round1-before.json) / [after evidence](evidence/round1-after.json).

```sh
python scripts/verify_revision.py e445bbc72b3b6b8f6e428f7b834d24d6fbba5168 --probe tests/probes/certificate_binding.py --output artifacts/replay-r1-before.json
python scripts/verify_revision.py 76aa7d2cce61f579c29d8b5ac0753e427cafa2a1 --probe tests/probes/certificate_binding.py --output artifacts/replay-r1-after.json
```

The first archive verification exposed a **validation harness** Windows stderr decoding failure: Python's traceback used the default code page for the Chinese workspace path. [That original report is retained](evidence/round1-before-decoding-failure.json), including its null stderr. The harness was corrected to set subprocess UTF-8 and the parent rerun; its complete stdout/stderr are in the primary before report. This setup correction is not counted as an iteration.

## 2 — false-like restrictions silently became unconditional

Review finding: grant condition validation used truthiness. JSON `[]`, `false`, `0`, `""` and `null` were accepted as unconditional grants. `version: true` also matched integer version 1. The CLI parser accepted duplicate JSON keys, so a duplicated `effect` replaced an earlier DENY with ALLOW. The frozen [strict-wire probe](../tests/probes/strict_wire.py) reproduces seven accepted ambiguous inputs on the direct parent; all seven are rejected on the child.

Substantive fixes: `model.py` accepts only absent/empty-object conditions, requires the exact integer version and rejects nonprintable/surrogate identifiers. `cli.py` rejects duplicate keys, nonfinite constants, over-4-MiB files, malformed UTF-8/JSON and excessive JSON nesting; optional UTF-8 BOM is accepted for Windows interoperability. `repair.py` validates proposal shape, exact integer accounting/costs, source bindings and completeness consistency before application. Independent certification returns false for invalid proposals. [Before evidence](evidence/round2-before.json) / [after evidence](evidence/round2-after.json).

```sh
python scripts/verify_revision.py 76aa7d2cce61f579c29d8b5ac0753e427cafa2a1 --probe tests/probes/strict_wire.py --output artifacts/replay-r2-before.json
python scripts/verify_revision.py 35656c47f32a06a05db83008c780ea7493cde72a --probe tests/probes/strict_wire.py --output artifacts/replay-r2-after.json
```

These are strict internal-language parser corrections, not additional supported cloud policy features. Unsupported restriction semantics remain UNKNOWN and must not be discarded automatically.

## 3 — repeated graph work for the same principal

Review finding: complete effective-set evaluation called the single-request explainer for every principal/action/resource triple, retraversing identical role inheritance repeatedly. The [unchanged dense-grid probe](../tests/probes/evaluation_work.py), within the declared 25,000-request cap, observed **16,000** traversals for only **8** principals. The old result still matched the independent closure (12,800 allowed requests); this is an actual measured performance deficiency, not a claimed authorization correctness bug.

Substantive fix: `engine.py` reuses one role traversal per principal, aggregates attached ALLOW/DENY pairs and subtracts DENY pairs before returning the full effective set. Default-denied pairs need not be materialized. `repair.py` constructs its constraint universe set once instead of rebuilding the Cartesian product per requested constraint. Expanded mixed grant/member/inheritance random DAG oracle comparisons preserve semantic checks.

The child prints 8 traversals, the same 12,800 independently verified allowed requests, and PASS. Single local timings were 0.1561084 seconds before and 0.0035380 after, under probe instrumentation; these are synthetic observations, not a general speed guarantee or a competitor benchmark. [Before evidence](evidence/round3-before.json) / [after evidence](evidence/round3-after.json).

```sh
python scripts/verify_revision.py 35656c47f32a06a05db83008c780ea7493cde72a --probe tests/probes/evaluation_work.py --output artifacts/replay-r3-before.json
python scripts/verify_revision.py f24cd5c6e7ea07a6aebd0d5934d963e3339058b6 --probe tests/probes/evaluation_work.py --output artifacts/replay-r3-after.json
```

Remaining boundaries: finite declared identities/actions/resources only; deletion-only edits; exhaustive search remains exponential; caps bound work counts rather than runtime; tied zero-cost output can be large; optimum oracle is small-instance only; local Windows Python 3.14 verification does not prove remote Ubuntu/Windows Python 3.11/3.14 CI passed. Independent review may veto the artifact and no builder scores are asserted.
