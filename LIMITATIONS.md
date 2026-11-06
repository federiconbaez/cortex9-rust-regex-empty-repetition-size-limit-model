# Limitations

- **One compile only.** `Regex::new` builds more than one program in the
  crate's exec layer. The model runs one `compile_one` (forward, NFA,
  Unicode chars, one expression, captures on). The DFA, reverse and
  byte-oriented compiles, literal extraction and the lazy DFA are not
  modelled.
- **Own parser, small subset.** `hir.py` is not regex-syntax. It covers ASCII
  letters/digits, groups, `|`, `^`, `$` and repetitions (stacked
  repetitions allowed, as the upstream tests imply). Classes, `.`, flags,
  escapes and Unicode are rejected. regex-syntax's own nest limit and its
  handling of stacked repetitions were not ported.
- **Back-patching not ported.** `fill`, `fill_split` and `dup_one` never
  change `insts.len()` or `extra_inst_bytes`, so holes are placeholders and
  the instruction graph is not built. The model cannot match text.
- **`size_of::<Inst>()` = 32 is measured on a standalone copy** of the
  type with rustc 1.99.1 on x86_64, not with the 2022 toolchain and not
  from the crate. Results scale with it.
- **`c_calls` is a work measure, not time.** No CPU time or memory is
  measured. `MODEL_LIMIT` means the model's budget ran out, nothing more.
- **Observation not validated.** The README notes that the model makes
  `(?:|){N}` fail before the fix too. It was not checked against the real
  crate.
- **CI** runs the tests on Python 3.10–3.13 and checks that `results/`
  regenerates byte for byte. It does not run Rust; `tools/inst_size.rs` is
  documentation.
