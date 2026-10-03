# AccessDelta

Review a **fully enumerated internal authorization model**, explain effective-access changes, and choose costed deletions that preserve required access without leaving any declared forbidden access. Runs locally; never changes an account.

内部应用角色变更审查工具：比较完整有效权限、查看允许/拒绝及继承证据，给出保留必要权限的最小成本删除方案，再检查实际输出的新 JSON。它只认识声明的 principal/action/resource 有限模型。

An inherited DENY can disappear when a membership or role edge is removed. An independent ALLOW then becomes effective. AccessDelta therefore reevaluates every entire candidate model instead of treating repair as monotone grant-path cutting.

## Install and run / 安装与使用

Python 3.11+. From a clone:

```sh
python -m pip install .
python scripts/demo.py
python scripts/contrast.py
python -m unittest discover -s tests -v
```

`demo.py` discovers the **installed, registered** `accessdelta` entry point through `sysconfig.get_path('scripts')`, then actually compares, inspects, proposes, applies into a new temporary local JSON, rechecks it, and independently certifies the small optimum. It prints each machine-readable result. Installation is ordinary wheel installation; no `PYTHONPATH` or source import injection.

For retained files, run the same workflow (write CLI output as UTF-8 JSON; PowerShell users should use `Set-Content -Encoding utf8`):

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
plan = propose(source, rules, max_candidates=65536)
if plan['selected'] is not None:
    repaired = apply(source, rules, plan)
    assert check(source, rules, plan, repaired)['feasible']
    # Small-only independent optimum certification. UNKNOWN is never certified.
    certificate = certify(source, rules, plan)
```

Use `Model.from_dict` to construct validated immutable models. `check` certifies source-bound **feasibility only**, even if a proposal says OPTIMAL; use the separately implemented exhaustive `certify` for a small-domain optimum. Neither is permission authenticity or outside-universe safety.

## Demonstrated decision / 合成实测对比

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

- Exact enumerated identifiers only. No wildcard or nonempty condition semantics, cloud IAM language, sessions, groups, resource policies, dynamic attributes, external identity discovery or real-account guarantees.
- Explicit DENY wins; otherwise any applicable ALLOW wins; otherwise default DENY. Child-role inheritance flows toward its named `inherits` parent. All cycles and unknown references are invalid, even when unreachable.
- Request universe: Cartesian product of supplied principals/actions/resources, at most 25,000 triples. Each declared list has at most 1,000 items. Comparison requires the same request universe on both sides.
- Editable universe: at most 20 declared grant/membership/inheritance deletions with exact nonnegative integer costs; protected items cannot be deleted. Constraints apply to **every** declared forbidden request, including access created by removal. Required access must be effective afterward.
- Enumeration stops at `max_candidates` (default 65,536). Exhaustion returns **UNKNOWN**, with a feasible incumbent when found, lower bound 0 and incomplete alternatives. Only complete enumeration returns OPTIMAL or INFEASIBLE. A valid incumbent can be applied and checked without proving optimality.
- All minimum-cost subsets are reported in deterministic lexical order. Zero-cost redundant edits remain legitimate tied solutions; selected is a presentation choice, never a uniqueness claim.
- Independent closure/bitmask oracle: at most 12 edits, 24 roles, 256 requests. It recomputes feasibility, optimum and ties without the production evaluator or subset iteration. Parsing is shared, so its independence does not certify the parser.

CLI: exit 0 for completed reports/valid operation, 2 INVALID input or I/O, 3 UNKNOWN unsupported semantics or exhausted search, 4 proven INFEASIBLE or failed optimum certification. JSON goes to stdout; errors to stderr. No timestamps are used to fake verification dates.

See [architecture](docs/ARCHITECTURE.md), [bounded commercial rationale](docs/COMMERCIAL.md), [iteration evidence](docs/ITERATIONS.md), [security](SECURITY.md), and [contributing](CONTRIBUTING.md). GitHub Actions declares Ubuntu/Windows × Python 3.11/3.14; a checked-in matrix is not evidence of remote execution.
