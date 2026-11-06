"""Check the model against the real crates (needs cargo + network for the
first build; not run in CI).

1. HIR: regex-syntax 0.6.25 (tools/upstream_check/hir_dump) vs hir.py.
2. Status: real regex 1.5.4 (pre) and 1.5.5 (fix) `RegexBuilder::size_limit`
   build vs the model status. The real 1.5.4 build is skipped for cases where
   the model reports MODEL_LIMIT, i.e. the long loop the CVE is about.
Nothing is matched against any input. Usage: upstream_check.py <out_dir>

Tool output is validated before anything is compared: the HIR dump must
return exactly one 2-field row per pattern, in order, echoing the pattern;
each compile run must return exactly one 3-field row per case it was given,
echoing the pattern and the size limit, with a known status. Every
(case, version) pair must be either compiled or skipped as MODEL_LIMIT.
Any violation raises UpstreamError and no file is written.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from regex_size_model import hir as H  # noqa: E402
from regex_size_model.cases import load, run_case  # noqa: E402

U = ROOT / "tools/upstream_check"


def sexp(h):
    if isinstance(h, H.Empty):
        return "Empty"
    if isinstance(h, H.Literal):
        return f"Lit({h.c})"
    if isinstance(h, H.Anchor):
        return f"Anchor({h.kind})"
    if isinstance(h, H.Group):
        return f"Group({'NC' if h.capture is None else 'Cap%d' % h.capture},{sexp(h.hir)})"
    if isinstance(h, H.Repetition):
        mx = "inf" if h.max is None else h.max
        return f"Rep({h.kind},{h.min},{mx},{'g' if h.greedy else 'l'},{sexp(h.hir)})"
    if isinstance(h, H.Concat):
        return "Concat(" + ",".join(map(sexp, h.items)) + ")"
    if isinstance(h, H.Alternation):
        return "Alt(" + ",".join(map(sexp, h.items)) + ")"
    raise TypeError(h)


def tool(name, stdin):
    d = U / name
    subprocess.run(["cargo", "build", "-q", "--release", "--locked"], cwd=d, check=True)
    exe = d / "target/release" / ("hir_dump" if name == "hir_dump" else "ocomp")
    out = subprocess.run([str(exe)], input=stdin, capture_output=True, text=True, check=True,
                         timeout=300).stdout
    return [line.split("\t") for line in out.splitlines()]


class UpstreamError(Exception):
    pass


STATUSES = ("OK", "COMPILED_TOO_BIG")


def check_rows(what, sent, got, width, echo):
    """sent: list of requests; got: parsed rows; echo(req) -> fields to echo."""
    if len(got) != len(sent):
        raise UpstreamError(f"{what}: {len(got)} rows for {len(sent)} inputs")
    for i, (q, row) in enumerate(zip(sent, got)):
        if len(row) != width:
            raise UpstreamError(f"{what}: row {i} has {len(row)} fields, expected {width}")
        exp = echo(q)
        if list(row[:len(exp)]) != exp:
            raise UpstreamError(f"{what}: row {i} echoes {row[:len(exp)]!r}, expected {exp!r}")


def main(out, tool=tool):
    cases = load(ROOT / "fixtures/cases.json")
    pats = list(dict.fromkeys([c["pattern"] for c in cases] +
                              (U / "patterns.txt").read_text().split("\n")[:-1]))
    if not pats or any(p == "" or "\n" in p or "\t" in p for p in pats):
        raise UpstreamError("empty pattern list or a pattern with a tab/newline")
    real = tool("hir_dump", "".join(p + "\n" for p in pats))
    check_rows("hir_dump", pats, real, 2, lambda p: [p])
    lines, bad = ["pattern\tregex_syntax_0_6_25\tmodel\tsame"], 0
    for (p, r), q in zip(real, pats):
        m = sexp(H.parse(p))
        bad += m != r
        lines.append(f"{p}\t{r}\t{m}\t{m == r}")
    model = {c["name"]: run_case(c) for c in cases}
    rows, cbad, skipped = ["case\tversion\tsize_limit\treal\tmodel\tsame"], 0, 0
    covered = set()
    for ver, crate in (("pre", "compile_1_5_4"), ("fix", "compile_1_5_5")):
        todo = [c for c in cases if model[c["name"]][ver]["status"] != "MODEL_LIMIT"]
        for c in cases:
            if c not in todo:
                covered.add((c["name"], ver))
        skipped += len(cases) - len(todo)
        for c in todo:
            if not isinstance(c["size_limit"], int) or c["size_limit"] < 0:
                raise UpstreamError(f"{c['name']}: invalid size_limit {c['size_limit']!r}")
        res = tool(crate, "".join(f"{c['pattern']}\t{c['size_limit']}\n" for c in todo))
        check_rows(crate, todo, res, 3, lambda c: [c["pattern"], str(c["size_limit"])])
        for c, (p, lim, st) in zip(todo, res):
            st = st.split("(")[0]
            if st not in STATUSES:
                raise UpstreamError(f"{crate}: {c['name']} unknown status {st!r}")
            covered.add((c["name"], ver))
            ms = model[c["name"]][ver]["status"]
            cbad += st != ms
            rows.append(f"{c['name']}\t{ver}\t{lim}\t{st}\t{ms}\t{st == ms}")
    if covered != {(c["name"], v) for c in cases for v in ("pre", "fix")}:
        raise UpstreamError("not every (case, version) was compiled or skipped")
    if len(rows) - 1 + skipped != 2 * len(cases):
        raise UpstreamError("compile checks + skipped != 2 x cases")
    o = Path(out)
    o.mkdir(parents=True, exist_ok=True)
    (o / "hir.tsv").write_text("\n".join(lines) + "\n")
    (o / "compile.tsv").write_text("\n".join(rows) + "\n")
    summary = {"cases": len(cases), "hir_patterns": len(pats), "hir_mismatches": bad,
               "compile_checks": len(rows) - 1, "compile_mismatches": cbad,
               "compile_skipped_model_limit": skipped}
    (o / "summary.json").write_text(json.dumps(summary, indent=1) + "\n")
    print(json.dumps(summary))
    return 1 if bad or cbad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
