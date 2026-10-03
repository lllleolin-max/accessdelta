# Changelog

## 0.1.1

- Bound proposal wire bytes as well as candidate enumeration. Excess tied output produces UNKNOWN with incomplete alternatives and any retained feasible incumbent, preserving complete ties on completed results. The CLI budget cannot exceed the unchanged 4 MiB reader cap; SDK callers may explicitly opt into unbounded output with `max_report_bytes=None`.
- Emit ASCII-safe console JSON through binary streams with exactly one LF, including on legacy Windows pipes. Budget accounting measures those actual bytes.
- Write repaired models as compact canonical UTF-8 without an added LF. Check the size before exclusive creation, preserving existing files and missing parent directories on refusal.
- Bound JSON integer tokens and SDK source costs to 4,300 decimal digits with exact local chunked encoding/parsing and unchanged interpreter settings. Default proposals return honest UNKNOWN/MAX_INTEGER_DIGITS when a newly feasible exact sum exceeds that wire budget. Unbounded-output SDK dictionaries preserve exact sums, application/checking and small optimum certification; oversized JSON input and output are typed refusals.
- Add exact-byte/integer, over-limit, real registered-console and source/destination preservation regressions. Preserve three new independent frozen failure probes and all previous correction probes and receipts.

Source bindings, full-model feasibility, the small independent optimum oracle and the distinction between `check` and `certify` retain their existing scope. Root controls corrected publication; existing 0.1.0 tags/assets and rejected historical evidence remain intact.
