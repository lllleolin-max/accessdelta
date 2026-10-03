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

## 4 — independently rejected Unicode console encoding

The immutable independent review at `00c207aec0836c5f1f53f6fb0cc6827600a9a2f6` was FAIL/HOLD (60/60/71), after its registered CLI crashed for the admitted principal `user-😀` on Windows legacy GBK pipes. That failure and independent review assets remain frozen; those scores do not describe or certify any corrected commit. The first three rounds above still await the reviewer's own runtime replay.

Builder replay used the original unchanged independent `cli_unicode_probe.py`, SHA256 `fbcd865c9cded52ee28890623c734928c3c4fc3f19198fcf43839129714bb830`. A fresh ordinary archive wheel of the old exact SHA matched all six Git/archive/wheel/site modules and reproduced probe exit 1, product exit 1, UnicodeEncodeError and no JSON. Its actual full suite still had 23 passing tests. [Old failure receipt](evidence/round4-before.json).

Direct parent → substantive product fix child: `00c207aec0836c5f1f53f6fb0cc6827600a9a2f6` → `4f53c5b908d72205bc3dd40e8bddc7b44457f0e5`. `cli.py` now serializes all stdout/stderr JSON with ASCII escaping, preserving decoded values and SDK/model identity. Argument errors are structured INVALID JSON and help is JSON. No user UTF-8 environment setting is needed. The new real registered-console tests run compare/inspect/propose/apply/check/certify, unsupported and bounded statuses, Unicode errors/filenames and argument errors under both forced legacy and UTF-8 modes.

The same original probe on the direct child wheel returns 0, ALLOW JSON, no UnicodeEncodeError and PASS. The actual child suite has 25 passing tests; full demo, contrast and original three frozen probes also pass. [Child receipt](evidence/round4-after.json). Later supplementary Unicode error assertions and the byte-identical public probe copy do not count as another application correction round.

```sh
python scripts/verify_revision.py 00c207aec0836c5f1f53f6fb0cc6827600a9a2f6 --probe tests/probes/cli_unicode_probe.py --output artifacts/replay-r4-before.json
python scripts/verify_revision.py 4f53c5b908d72205bc3dd40e8bddc7b44457f0e5 --probe tests/probes/cli_unicode_probe.py --output artifacts/replay-r4-after.json
```

The public probe copy preserves the original frozen bytes/hash and attribution; independent assets outside this repository were never modified. Helper UTF-8 capture only encodes the harness; the probe removes encoding overrides and explicitly resets its product subprocess to `PYTHONUTF8=0`. Helper improvements and current-document path sanitation are not counted as code iterations. [Sanitation evidence and history boundary](SANITATION.md).

## 5 — independently rejected CLI producer/consumer byte closure

The public 0.1.0 commit `65ff88e8d8e7ded68bd0e98758396c3245a92871` was independently placed on HOLD after two supported CLI workflows failed. Mathematical feasibility was correct in both cases. Frozen independent reports, probe sources and release assets remain unchanged. These are two actual findings fixed in one direct product correction, not two invented implementation rounds.

The unchanged tie-cap probe has SHA256 `1685fac6fcfa243efbb919cbc560542fb27a45b618753986039035025027367b`. Its 12-edit control has 4,096 independently known zero-cost feasible subsets; 0.1.0 emits a consumable 2,687,366-byte OPTIMAL report. Its 14-edit case has 16,384 such subsets: 0.1.0 emits 12,534,152 bytes and exits 0, then its own `apply` and `check` each reject that exact stdout with exit 2 at the unchanged 4 MiB input cap. SDK feasibility remains true. A fresh canonical archive/ordinary wheel reproduces probe exit 1. [Original parent failure](evidence/round5-before.json).

The unchanged repaired-file probe has SHA256 `26a14f25c47ebd14d4010792aa808be10e79017e247217c5b57d49a35b94f9b8`. A valid compact 4,106,118-byte source declares one principal, 500 actions, one resource, 1,000 grants, no edits and a protected required grant. The parent produces OPTIMAL, applies successfully, then pretty-printing expands its repaired file to 8,708,674 bytes and `check` exits 2. The original source bytes stay intact. Its separate fresh ordinary wheel reproduces probe exit 1. [Original parent failure](evidence/round5-model-before.json).

Direct parent → substantive fix child: `65ff88e8d8e7ded68bd0e98758396c3245a92871` → `0b94b427d96dc61635f85ed7690c0a49fed21c46`, version 0.1.1. `repair.py` accounts for exact encoded tied-subset bytes before retention, reserves result metadata and returns honest UNKNOWN when the proposal budget would be exceeded. `model.py` defines the shared 4 MiB limit and actual ASCII wire encoder. `cli.py` emits binary console bytes with one LF, preventing Windows CRLF growth, and writes compact canonical UTF-8 repaired models without an added LF. It guards output size before exclusive creation. The ingress limit is not increased. Small complete reports still include every optimal tie; bounded reports cannot claim OPTIMAL or complete ties. Source bindings, effective-model rechecks and small independent certification keep their existing boundaries.

On the unchanged tie probe, the direct child preserves all 4,096 control ties (2,687,392 bytes). The 14-edit case returns UNKNOWN with incomplete enumeration/ties and a usable empty incumbent: actual Windows stdout is 4,193,764 bytes, including its LF, with 7,193 retained known subsets. `propose` exits 3; both exact-byte consumers exit 0 and source bytes remain intact. [Direct child passing evidence](evidence/round5-after.json). On the unchanged model probe, the direct child writes 4,106,118 compact bytes and the propose/apply/check sequence is 0/0/0; the probe exits 0 and source bytes remain intact. [Direct child passing evidence](evidence/round5-model-after.json).

The direct child's fresh ordinary wheel actually ran its inherited **25** tests, full registered-console demo, fair contrast and four earlier frozen probes successfully. [Exact child suite and six Git/archive/wheel/site module associations](evidence/round5-code-suite.json). Later supplemental boundary tests and byte-identical probe copies are verification additions, not more correction cycles. The suite in supplemental commit `a528dd585f89ff812cb71e9ce4157a2d4d3914fc` actually ran **30** tests. Current verification adds a sixth byte-boundary test method; its final actual suite count is recorded in the final revision receipt, not retroactively assigned to earlier commits.

Boundary regressions include exact and one-byte-under report budgets (ASCII/Unicode), real registered stdout in legacy and UTF-8 modes, near-default-cap output without CRLF, raw-byte proposal consumption, exactly 4 MiB compact repaired bytes without LF, cap-plus-one source/proposal rejection, and unchanged source/existing destination/no directory creation on refusal. The six public probe copies preserve the original frozen hashes. The boundary driver was copied byte-for-byte into repository-private scratch before execution because its own scratch default is relative to its location; independent assets were read only. Local observations do not prove remote four-way CI, and root controls any corrected tag/release after independent review.

## 6 — independently rejected derived integer output interoperability

The unpublished 0.1.1 commit `9c19656cf00500e03654a56f4fd57b059c0df5ac` received frozen independent FAIL/HOLD (60/60/85) after a new output-resource counterexample. Its earlier 31 passing tests do not cancel that failure, and these scores do not transfer to corrected code. All independent reports/ZIPs/probes remain frozen. The defect is bounded JSON serialization and consumption, not incorrect permission or integer arithmetic.

The unchanged independent numeric probe has SHA256 `7acfe203ebe0ce47acec70786871b124101e59e0634f278d62d611d143361fc1`. A 377-byte model has two independent forbidden ALLOW grants; deleting both is the unique feasible repair. Two admitted 4,300-digit nonnegative costs in 8,777 constraint bytes sum exactly to a 4,301-digit result. The parent unbounded-output SDK computes that cost and successfully applies/checks it. Default bounded SDK instead raises raw ValueError while sizing the report; actual registered `propose` exits 1 with a traceback, no stdout and unchanged sources. Its 4,299-digit-per-cost control completes all three CLI commands with exit 0. A fresh canonical archive ordinary wheel reproduces probe exit 1 with all six module associations and unchanged global digit setting 4,300. [Parent failure](evidence/round6-before.json).

Direct parent → substantive product correction: `9c19656cf00500e03654a56f4fd57b059c0df5ac` → `ef2ef007890566c770920a2ba27c0ed70bbf6bfe`. The JSON protocol now explicitly admits at most 4,300 decimal digits per integer; SDK source costs share that finite bound. Local decimal-chunk encoding/parsing preserves exact JSON integers and existing canonical fingerprints without changing interpreter/global settings. Bound checks occur before numeric wire conversion and source costs beyond the declared bound receive typed ModelError. Bounded proposal retention stops at MAX_INTEGER_DIGITS when a newly feasible exact sum cannot be delivered within the protocol, returning UNKNOWN, incomplete ties/certificate, lower bound zero and no falsely costed incumbent. Exact unbounded-output SDK arithmetic/application/checking/certification remains available; twenty allowed source costs imply sums of at most 4,302 digits. This protocol is a resource/interoperability decision, not a claim that larger numbers violate general JSON syntax.

The original probe on the direct child's fresh wheel returns 0. Its 4,299-digit control remains OPTIMAL with the exact 4,300-digit sum, 9,034 stdout bytes and successful consumers. The 4,300-digit source remains admitted; default proposal returns 431-byte JSON, exit 3, UNKNOWN/MAX_INTEGER_DIGITS, no selected incumbent and no false cost. Although checked equals candidate_count (4), completeness remains false. The unbounded SDK result still matches the primitive exact-cost oracle and is feasible. Global setting remains 4,300 before/after. [Direct child pass](evidence/round6-after.json). That child actually runs its inherited **31** tests, six prior frozen probes, registered-console demo and fair contrast successfully. [Exact child suite and module association](evidence/round6-code-suite.json).

Supplemental commit `e186f1d9fa07ae76184b0125f597cd26bf04d74a` adds typed output-integer resource refusal for CLI certification, reserves the longest possible numeric termination envelope, five numeric boundary test methods and the original-byte seventh probe. Its fresh ordinary wheel actually passes **36** tests and all seven probes. These complete the same numeric correction; they are not another claimed independent cycle. Tests exercise exact/one-over source integers, all source-cost SDK paths/fingerprints, exact wide SDK application/checking/small certification, a primitive twenty-grant SDK feasible incumbent without claiming exhaustive enumeration, UNKNOWN with no fabricated incumbent, raw CLI bytes in legacy/UTF-8 modes, forged oversized fields, no file/directory mutations and unchanged global settings. Current final receipts retain actual per-SHA counts. Local Windows Python 3.14 tests do not establish remote four-way CI or independent acceptance.
