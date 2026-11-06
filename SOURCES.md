# Sources

Local copies under `security-research-45/sources/next/` (not in this repo), read with `gh api` (read-only):

| Source | Used for | SHA-256 of copy |
|---|---|---|
| rust-lang/regex commit ae70b41d4f46 diff ("security: fix denial-of-service bug in compiler", 2022-03-03) | `c_empty()`, its two call sites, the four upstream test patterns | e5d1359ce39aed2cb95b0765f723c96531800bf2bf782c9039298f6a0d4b6a98 |
| `src/compile.rs` at b92ffd5 (parent of ae70b41) | the `pre` port; line numbers in `compiler.py` | 84251b11081db43b712a887d424b79bdcd4738865e7df4d8667250cec553bac3 |
| `src/compile.rs` at ae70b41 | the `fix` port (differs only by `c_empty`) | 5c834c2125abc10d0de3c377e34b1f2e2c10b837809631b1c688d3b536368cfd |
| `src/prog.rs` at b92ffd5 | `Inst` definitions copied into `tools/inst_size.rs` | 78a02dcc1fc7b1d4f37a4a4eeb075eb5cc84aea1736e4de3a2cc7449a9ce5103 |
| `src/re_builder.rs` at b92ffd5 | default `size_limit` (l.22) | 943344bf6e2fc90902ee04b11b741c32418ac6814b21b7982cc0a3a817713f3e |
| `Cargo.toml` at b92ffd5 | version 1.5.4 | 516e4767a164d7ccabcfbca3d43531fe76f8fbabd04b4b5ad38eda796306eb0a |
| `regex-syntax/Cargo.toml` at b92ffd5 | regex-syntax 0.6.25 | b6e1d5d7e2b20ea1b1b64ce1161008886e14fb60e38c7ecb34ef46cb3a85c0d1 |
| `regex-syntax/src/hir/translate.rs` at b92ffd5 | non-capturing groups kept as `Group` (l.775-789), repetition kinds | 4c595d2faee09aecfdafe5871e7b5b698159d846e3262cf694e6e0a59e8e6a5f |
| `regex-syntax/src/hir/mod.rs` at b92ffd5 | `Hir::concat` / `Hir::alternation` simplification (l.394, l.487) | 325dc1e42eb8fb9daeb7a8a5e7f967fdee745a7a7c5e26c20dec0b6c66109ad7 |
| GHSA-m5pq-gvj9-9vr8 (CVE-2022-24713) | description; affected < 1.5.5 | 703b528fbe2f7843ea2888aa1497cad0f99248a11a353b5ca548e05f1eef73ae |
| crates.io `regex` 1.5.4 and 1.5.5 (via Cargo, `tools/upstream_check/compile_*/Cargo.lock`) | real build status; their `src/compile.rs` hashes equal the b92ffd5 / ae70b41 rows above | 84251b11… / 5c834c21… (compile.rs) |
| crates.io `regex-syntax` 0.6.25 (`tools/upstream_check/hir_dump/Cargo.lock`) | real HIR; `src/hir/mod.rs` and `src/hir/translate.rs` equal the b92ffd5 copies | 325dc1e4… / 4c595d2f… |

The advisory says the crate "did not properly limit the complexity of the
regular expressions (regex) it parses". The fix itself is in the compiler
(`src/compile.rs`), not in the parser (`regex-syntax`), and that is what
this repo models.
