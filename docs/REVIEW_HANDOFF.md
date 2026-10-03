# AccessDelta independent-review handoff

Implementation scope: one strict internal finite authorization language, complete-model effective-set delta/evidence, nonmonotone minimum-cost deletion repair, real local JSON application/recheck and independently implemented small optimum/tie certification. No publication, revenue or adoption is claimed. The repository is MIT, has bilingual installation/use/why explanations and does not change accounts.

Frozen code correction chain: initial `e445bbc72b3b6b8f6e428f7b834d24d6fbba5168`; correction children `76aa7d2cce61f579c29d8b5ac0753e427cafa2a1`, `35656c47f32a06a05db83008c780ea7493cde72a`, `f24cd5c6e7ea07a6aebd0d5934d963e3339058b6`. See [iteration log](ITERATIONS.md) for direct parent relations, exact frozen probe hashes, actual failing/passing outputs, per-SHA full suite counts and Git/archive/wheel/site association. The third round fixes a measured computational deficiency rather than falsely claiming a semantic defect.

The old `00c207aec0836c5f1f53f6fb0cc6827600a9a2f6` independently failed a Unicode registered-console probe and received frozen FAIL/HOLD scores 60/60/71. They are not inherited here. Fourth direct correction child `4f53c5b908d72205bc3dd40e8bddc7b44457f0e5` fixes product JSON serialization, with the exact same independent probe failing on the old ordinary wheel and passing on the new one (hash `fbcd865c9cded52ee28890623c734928c3c4fc3f19198fcf43839129714bb830`). Fresh child suite: 25 passing tests, including actual UTF8=0/1 console workflows/errors. This remains builder evidence pending independent review; the first three historical cycles also need the reviewer's runtime replay.

```sh
python -m pip install .
python -m unittest discover -s tests -v
python scripts/run_probes.py
python scripts/demo.py
python scripts/contrast.py
python scripts/verify_revision.py HEAD --output artifacts/reviewer-wheel.json
python scripts/audit_tracked.py
```

The final command creates a canonical Git ZIP archive, builds an ordinary wheel, installs into a fresh environment, verifies every core module's bytes against Git/archive/wheel/site, and runs that exact revision's complete suite, frozen probes, registered CLI demo and fair contrast. Build and installation failures stop verification. The JSON report includes exact SHA and full outputs; do not infer success solely from the tool process ending normally—inspect every component's returncode.

Specific exercised decisions: removing a deny membership/edge creates forbidden secret access; exact repair instead chooses the allow grant deletion of cost 4. A different inherited-edge case costs 3 exactly vs 4 under cheapest-improving greedy. Baseline-equivalent simple and deny cases are included. A zero-cost tie case emits four concrete optimal deletion subsets. UNKNOWN with an incumbent never certifies an optimum; an impossible protected deletion returns INFEASIBLE only after completion; wholly empty universes return cost-0 empty repair.

Independent oracle uses Boolean fixed-point role closure and bitmask subset enumeration, not production BFS/set aggregation/combinations. The schema parser is shared and is not independently certified. `check` deliberately proves only source-bound feasibility; a cost-4 feasible repair in the cost-3 case passes `check` but fails `certify`. All forbid/require obligations concern explicitly declared requests. Required/forbidden lists are supplied by the user, not automatically inferred organizational policy.

Current official comparison sources reopened 2026-10-03: [AWS custom new-access checks](https://docs.aws.amazon.com/IAM/latest/UserGuide/access-analyzer-custom-policy-checks.html), [AWS simulator](https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_testing-policies.html). Existing new-access detection/simulation receive explicit credit. Incumbent software was not executed; absence of a documented feature is not evidence that it is missing.

Local observed environment: Windows, Python 3.14.3. Remote CI four-way matrix is configured but unverified at this local handoff. To call the overall twenty-project goal complete, root still needs independent criterion scores, publication and actual remote CI evidence. Do not inherit a reviewed code SHA silently after later edits.

Current receipt paths are portable markers; original seven raw receipts were byte-backed-up outside Git before sanitation, with original/current hashes and lexical nonstring preservation checked in [sanitation evidence](evidence/sanitation.json). Old Git history remains unredacted. No independent frozen report/ZIP/receipt was changed, and private review scratch was not removed. The tracked filename-only path/credential scan is a finite-pattern current-tree check, not a comprehensive secret-free or historical guarantee.
