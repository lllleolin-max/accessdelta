# AccessDelta

Review a **fully enumerated internal authorization model**, explain effective-access changes, and choose costed deletions that preserve required access without leaving any declared forbidden access. Runs locally; never changes an account.

内部应用角色变更审查工具：比较完整有效权限、查看允许/拒绝及继承证据，给出保留必要权限的最小成本删除方案，再检查实际输出的新 JSON。它只认识声明的 principal/action/resource 有限模型。

Use it when an internal application's principals, roles, grants, actions and resources can be fully enumerated and a reviewer needs to compare effective access or choose deletions under explicit constraints. It is not an AWS/IAM importer or a general cloud-permission auditor. See [the model contract](docs/ARCHITECTURE.md) before mapping a real application.

An inherited DENY can disappear when a membership or role edge is removed. An independent ALLOW then becomes effective. AccessDelta therefore reevaluates every entire candidate model instead of treating repair as monotone grant-path cutting.

## Install and run / 安装与使用

Python 3.11+ and Git. Clone and create a virtual environment:

```sh
git clone https://github.com/lllleolin-max/accessdelta.git
cd accessdelta
python -m venv .venv
```

Activate it with `.venv\Scripts\Activate.ps1` on Windows PowerShell or `source .venv/bin/activate` on Linux/macOS. From the repository root:

```sh
python -m pip install .
python scripts/demo.py
```

`demo.py` discovers the **installed, registered** `accessdelta` entry point through `sysconfig.get_path('scripts')`, then actually compares, inspects, proposes, applies into a new temporary local JSON, rechecks it, and independently certifies the small optimum. It prints each machine-readable result. Installation is ordinary wheel installation; no `PYTHONPATH` or source import injection.

Expected demo (exit 0): `secret_evidence.decision` is `DENY`; `proposal.selected` is `["grant:bad-write"]` with cost **4**; `check.feasible` and `certify.certified` are `true`. The temporary proposal/repaired files are deleted after the run. To retain artifacts, follow the workflow below with new destinations.

## Your workflow / 接入自己的权限模型

| Step | Input → output | Next action |
|---|---|---|
| Compare | Before/after model JSON → effective request delta | Review changed access and inheritance evidence |
| Propose | After model + required/forbidden access + edit costs → proposal | Inspect `status`, `selected`, `cost`, bounds and tied alternatives |
| Apply/check | Source model + constraints + proposal → new repaired model | Check the actual emitted JSON for feasibility |
| Certify, for small cases | Same source/constraints/proposal → independent optimum result | Hand the reviewed model to your application's own approval process |

`apply` writes a local JSON model only; your application's deployment and identity authenticity remain separate responsibilities.

For retained files, run the same workflow. Preserve proposal stdout bytes exactly: an extra BOM, newline or shell text conversion can push a near-limit report above the 4 MiB reader cap. The installed-console demo captures bytes directly and is portable across supported shells.

The following redirection example assumes a shell that preserves native stdout bytes.

```sh
accessdelta compare examples/deny-diamond/before.json examples/deny-diamond/after.json
accessdelta inspect examples/deny-diamond/after.json alice read secret
accessdelta propose examples/deny-diamond/after.json examples/deny-diamond/constraints.json > proposal.json
accessdelta apply examples/deny-diamond/after.json examples/deny-diamond/constraints.json proposal.json repaired.json
accessdelta check examples/deny-diamond/after.json examples/deny-diamond/constraints.json proposal.json repaired.json
accessdelta certify examples/deny-diamond/after.json examples/deny-diamond/constraints.json proposal.json
```

The synthetic diamond prints `DENY / EXPLICIT_DENY` for secret read even though two ALLOW grants match. Removing the zero-cost deny membership or inheritance edge creates forbidden secret access. The exact proposal instead deletes `grant:bad-write`, costs **4**, and retains required report reading. `apply` refuses to overwrite any existing file.

中文用途：内部应用负责人在部署前检查权限回归；安全审核员核对继承拒绝是否会被删除；平台工程师用 JSON 与 SDK 集成审批。为什么做：只看新增 grant 会漏掉继承边导致的新访问，而删除拒绝分支可能制造另一种泄漏。如何做：运行以上完整本地流程，检查 evidence 和 constraints，然后把输出模型交给应用自身流程审阅。这里没有云账号动作。

## SDK

```python
import json
from accessdelta import Model, compare, explain, propose, apply, check, certify

source = Model.from_dict(json.load(open('examples/deny-diamond/after.json')))
rules = json.load(open('examples/deny-diamond/constraints.json'))
decision = explain(source, ('alice', 'read', 'secret'))
plan = propose(source, rules, max_candidates=65536, max_report_bytes=4 * 1024 * 1024)
if plan['selected'] is not None:
    repaired = apply(source, rules, plan)
    assert check(source, rules, plan, repaired)['feasible']
    # Small-only independent optimum certification. UNKNOWN is never certified.
    certificate = certify(source, rules, plan)
```

Use `Model.from_dict` to construct validated immutable models. `check` certifies source-bound **feasibility only**, even if a proposal says OPTIMAL; use the separately implemented exhaustive `certify` for a small-domain optimum. Neither is permission authenticity or outside-universe safety.

## Demonstrated decision / 合成实测对比

After the first demo, run `python scripts/contrast.py` to reproduce this comparison.

`scripts/contrast.py` executes raw grant-record diff, a fully reevaluating cheapest-improving-deletion greedy baseline, exact repair and the independent closure/bitmask oracle on identical data, costs, protected items and access constraints.

| Synthetic case | Raw grant diff | Greedy cost | Exact cost | Decision implication |
|---|---|---:|---:|---|
| cost-trap | no changed grants | 4 | 3 | inherited edge introduces two permissions; one edge edit is cheaper than two greedy grant edits |
| deny-diamond | bad-write added | 4 | 4 | both reject zero-cost deny-branch removal after full reevaluation |
| simple | unwanted added | 2 | 2 | baseline is already sufficient |
| ties | no changed grants | 2 | 2 | report four equally optimal subsets, including zero-cost redundant edits |

All data are synthetic. The raw baseline is intentionally named **grant-record diff**, not a full semantic policy checker. It cannot infer effective access from unchanged grants and changed membership/inheritance. The greedy implementation supports all declared deletion kinds and applies the same semantics and constraints; its limitation is local cheapest improvement. No AWS benchmark was run, and these examples establish no universal superiority.

AWS already provides [custom checks for new access](https://docs.aws.amazon.com/IAM/latest/UserGuide/access-analyzer-custom-policy-checks.html). Its [policy simulator](https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_testing-policies.html) provides allow/deny outcomes and policy attribution and documents limitations relative to live permissions. These official pages were opened on **2026-10-03**. The useful engineering combination here is finite effective-set comparison plus nonmonotone costed deletion search, concrete alternatives and independent small-instance verification. New-access detection, policy simulation and graph traversal are established foundations; absence of a feature from a page proves no competitor gap.

## Bounds and honest outcomes / 边界

The model uses exact finite identifiers, explicit DENY precedence and deletion-only repairs. Search is exponential and bounded; an `UNKNOWN` result may contain a feasible incumbent without proving an optimum. `check` establishes feasibility; the smaller independent `certify` establishes only a finite-model optimum. Neither establishes permission authenticity or safety outside the declared request universe.

CLI: exit 0 for completed reports/valid operation, 2 INVALID input or I/O, 3 UNKNOWN unsupported semantics or exhausted search, 4 proven INFEASIBLE or failed optimum certification. JSON goes to stdout; errors to stderr. No timestamps are used to fake verification dates.

<details>
<summary>Detailed model, search, JSON and Unicode limits / 完整协议与资源边界</summary>

- Exact enumerated identifiers only. Conditions must be omitted or `{}`; all other values return UNKNOWN. No wildcard semantics, cloud IAM language, sessions, groups, resource policies, dynamic attributes, external identity discovery or real-account guarantees.
- Explicit DENY wins; otherwise any applicable ALLOW wins; otherwise default DENY. Child-role inheritance flows toward its named `inherits` parent. All cycles and unknown references are invalid, even when unreachable.
- Request universe: Cartesian product of supplied principals/actions/resources, at most 25,000 triples. Each declared list has at most 1,000 items. Comparison requires the same request universe on both sides.
- CLI JSON inputs are UTF-8 (optional BOM), at most 4 MiB each, with at most 4,300 decimal digits per integer token (excluding a minus sign). This is a bounded interoperability protocol, not a claim about general JSON syntax. Local chunked codecs preserve exact integers without changing the interpreter's digit setting. Duplicate object keys, nonfinite constants, bad encoding and unpaired Unicode surrogates are rejected.
- Editable universe: at most 20 declared grant/membership/inheritance deletions with exact nonnegative integer costs of at most 4,300 decimal digits, in both CLI and SDK source constraints; protected items cannot be deleted. Constraints apply to **every** declared forbidden request, including access created by removal. Required access must be effective afterward.
- Search stops at `max_candidates` (default 65,536), the proposal wire budget (default 4 MiB, including its single LF), or the 4,300-digit result-integer budget. Any bound returns **UNKNOWN**, with a retained feasible incumbent when its exact cost is representable, lower bound 0 and incomplete alternatives. `termination` identifies COMPLETE, MAX_CANDIDATES, MAX_REPORT_BYTES or MAX_INTEGER_DIGITS. A newly found solution whose exact cost exceeds the integer budget is not emitted with a false cost or claimed incumbent. Checking every candidate alone does not make an output-limited certificate complete. Only complete usable enumeration returns OPTIMAL or INFEASIBLE. A valid incumbent can be applied and checked without proving optimality.
- Completed results report all minimum-cost subsets in deterministic lexical order. Bounded results report known tied incumbents with `ties_complete: false`; they never claim all optimal ties. Zero-cost redundant edits remain legitimate tied solutions; selected is a presentation choice, never a uniqueness claim.
- CLI `--max-report-bytes` may lower the proposal budget but cannot exceed the unchanged 4 MiB input cap. Encoded lengths are accounted before retaining another tie, conservatively reserving result metadata. SDK callers may explicitly choose `max_report_bytes=None` to remove both result-byte and result-integer wire bounds. Python dictionaries then retain exact derived costs, including sums up to 4,302 digits from the 20 allowed source costs; SDK `apply`, `check` and small `certify` keep exact arithmetic. Serializing those dictionaries through the bounded JSON codec may refuse them, and they have no CLI-consumption guarantee. Tied output can be exponential.
- `apply` writes compact canonical UTF-8 without a trailing newline. It checks the output byte cap before exclusive file creation; existing destinations are never overwritten and missing parent directories are never created. An exactly 4 MiB repaired model remains readable.
- Independent closure/bitmask oracle: at most 12 edits, 24 roles, 256 requests. It recomputes feasibility, optimum and ties without the production evaluator or subset iteration. Parsing is shared, so its independence does not certify the parser.

An output-integer resource refusal, including an independent certification result too wide for this JSON protocol, also returns typed UNKNOWN (exit 3) with `termination: MAX_INTEGER_DIGITS`; it delivers no certificate. An over-limit source/proposal integer is typed INVALID (exit 2) before output-file creation. 中文数字边界：单项成本最多 4,300 位，精确求和不截断；有界输出无法表示派生成本时返回 UNKNOWN，不伪造成本、可行方案或最优证书。无输出界的 SDK 可保留精确 Python 整数结果，但该字典不保证能通过有界 JSON CLI 传输。

All CLI reports, errors and help use **ASCII-safe JSON**, which is valid UTF-8 and works with legacy Windows pipes without `PYTHONUTF8` or `PYTHONIOENCODING`. Binary stdout/stderr emission appends exactly one LF, avoiding Windows CRLF expansion at the byte boundary. JSON decoding restores the original Unicode identifiers and values; model fingerprints and UTF-8 output files retain their existing semantics. Argument errors also return JSON with exit 2. Actual registered-console tests run every operation and Unicode error paths in both `PYTHONUTF8=0` and `1`, and consume exact near-cap stdout bytes in both modes.

</details>

## Validation and correction history / 验证与修订记录

For development checks, run `python -m unittest discover -s tests -v` and `python scripts/run_probes.py` after installation. They are optional after the quickstart.

Version 0.1.1 corrects independently reproduced CLI producer/consumer failures: oversized tied proposals, pretty-printed repaired files, and derived integer costs beyond the default JSON interoperability budget. Search stops honestly at output resource bounds; repaired models use compact UTF-8. The old failures and their review receipts remain recorded in [iteration evidence](docs/ITERATIONS.md).

The former `00c207a` build failed an independent frozen Unicode pipe probe and remains rejected; its scores do not transfer to this correction. The current tracked historical receipts replace local absolute path prefixes with portable markers after preserving original bytes in a private Git-external backup. Numeric representations, outcomes, timing observations, SHAs and probe hashes remain intact. **Old Git history still contains machine paths**; history and frozen independent review assets were not rewritten. See [sanitation boundaries](docs/SANITATION.md).

See [architecture](docs/ARCHITECTURE.md), [bounded commercial rationale](docs/COMMERCIAL.md), [iteration evidence](docs/ITERATIONS.md), [security](SECURITY.md), and [contributing](CONTRIBUTING.md). GitHub Actions declares Ubuntu/Windows × Python 3.11/3.14; a checked-in matrix is not evidence of remote execution.
