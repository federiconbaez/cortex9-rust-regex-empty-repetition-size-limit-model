# cortex9-rust-regex-empty-repetition-size-limit-model

[Español](README.es.md) · [Practice guide](PRACTICE.md) · [CI](https://github.com/federiconbaez/cortex9-rust-regex-empty-repetition-size-limit-model/actions/workflows/ci.yml)

A Python model of how the Rust `regex` crate 1.5.4 accounts for compiled
program size, **before and after the CVE-2022-24713 fix** (commit
`ae70b41`; the GHSA lists 1.5.5 as the first patched release). Before the fix, an empty sub-expression
compiled to no instruction and added nothing to the size, so `(?:){4294967295}`
never reached the size limit and the compiler simply iterated. The fix
charges `size_of::<Inst>()` bytes for every empty sub-expression.

**All counts are computed by running the ported compiler logic. No verdict
is hard-coded.** Every call to `c()` is counted against an external budget;
when it runs out the status is `MODEL_LIMIT`. No Rust code and no `regex`
crate run, there are no services, and patterns are at most 256 characters.
See [LIMITATIONS.md](LIMITATIONS.md).

## What is ported

| Piece | Source | Module |
|---|---|---|
| `compile_one` (forward, NFA, one expression), `c`, `c_capture`, `c_char`, `c_empty_look`, `c_concat`, `c_alternate`, `c_repeat`, `c_repeat_zero_or_one/zero_or_more/one_or_more/range_min_or_more/range`, `push_hole`, `push_split_hole`, `pop_split_hole`, `check_size` | `src/compile.rs` at b92ffd5 (1.5.4, parent of the fix) | `compiler.py` |
| `c_empty()` and its two call sites (`Empty`, empty `c_concat`) | `src/compile.rs` at ae70b41 | `compiler.py` (`fix`) |
| default `size_limit` = 10 × 2²⁰ | `src/re_builder.rs` l.22 | `DEFAULT_SIZE_LIMIT` |
| HIR shapes: Group kept for `(?:…)`, `concat`/`alternation` of 0 or 1 items simplified | regex-syntax 0.6.25 `translate.rs` l.775, `hir/mod.rs` l.394/487 | `hir.py` (own parser, not a port) |

`size_of::<Inst>()` is taken as **32**. That value comes from compiling
`tools/inst_size.rs`, a standalone copy of the `Inst` type definitions from
`src/prog.rs` with no `regex` dependency, with rustc 1.99.1 on x86_64. Rust
does not guarantee enum layout, and the 2022 compiler was not used.

## Counters

`c_calls` (= `check_size` calls), `insts` (`insts.len()` at the end or at the
stop), `extra_inst_bytes`, `empty_hits` (empty sub-expressions reached, in
both versions), `empty_accounted` (those that added bytes; fix only),
`size_at_stop`. `status` is `OK`, `COMPILED_TOO_BIG` or `MODEL_LIMIT`.

## Hand-derived cases (`fixtures/cases.json`)

| Pattern, limit | pre | fix |
|---|---|---|
| `(?:){3}`, 4096 | OK, 7 calls, 3 insts, 0 extra | OK, 7 calls, 3 insts, **128 extra** (3 Empty + 1 empty concat) |
| `(?:){4294967295}`, 4096 | MODEL_LIMIT after 100000 calls, size stuck at 32 | COMPILED_TOO_BIG after 258 calls, 128 empties |
| `x{0}{4294967295}`, 4096 | MODEL_LIMIT | COMPILED_TOO_BIG after 130 calls |
| `(?:\|){4294967295}`, 4096 | COMPILED_TOO_BIG, 129 insts (the Split instructions grow) | COMPILED_TOO_BIG, 44 insts + 2720 extra |
| `(?:){4294967295}`, 10 MiB | MODEL_LIMIT after 2,000,000 calls | COMPILED_TOO_BIG after 655,362 calls, 327,680 empties |

The four upstream patterns come from the tests added in ae70b41
(`big_empty_regex_fails`, `big_empty_reps_chain_regex_fails`,
`big_zero_reps_regex_fails`, `empty_alt_regex_fails`). With the default
limit, the fix stops after exactly `limit / 32 = 327,680` accounted
empties for the first three.

## Progression (`results/progression.csv`)

For `(?:){N}` with the default 10 MiB limit and N from 10 to 10⁶:

- `pre` compiles (`OK`) with `c_calls = 2N + 1`, and its size stays at
  96 bytes. Work grows linearly with N, and the size limit never fires.
- For N = 4294967295, `pre` stops at the model budget (`MODEL_LIMIT`).
- `fix` charges 32 bytes per empty. It compiles up to N = 100000, and above
  the threshold it stops after a constant 655,362 calls.

## Model observation that is NOT validated

In this model, `(?:|){N}` already hits `COMPILED_TOO_BIG` **before** the
fix, because each repetition pushes a Split instruction. If that holds for
the real crate, the upstream test `empty_alt_regex_fails` would pass on
1.5.4 too; its own comment calls it "another case for completeness". This
was not run against the real crate, and is listed only for study.

## Usage

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m regex_size_model '(?:){4294967295}' --size-limit 4096 --budget 100000
python3 scripts/gen_results.py /tmp/out && diff -r results /tmp/out
```

Python ≥ 3.10, standard library only. License: Apache-2.0.
