"""Regenerate results/. Usage: gen_results.py <out_dir>"""
import csv
import hashlib
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from regex_size_model.cases import load, progression, run_case  # noqa: E402

FILES = ("cases.json", "cases.csv", "progression.csv")
COLS = ("status", "c_calls", "insts", "extra_inst_bytes", "empty_hits", "empty_accounted", "size_at_stop")


def _csv(rows) -> str:
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\n").writerows(rows)
    return buf.getvalue()


def main(out: str) -> int:
    o = Path(out)
    o.mkdir(parents=True, exist_ok=True)
    allr, rows = {}, [["case", "pattern", "size_limit", "budget", "version", *COLS]]
    for c in load(ROOT / "fixtures/cases.json"):
        r = run_case(c)
        allr[c["name"]] = {"pattern": c["pattern"], **r}
        for v, d in r.items():
            rows.append([c["name"], c["pattern"], c["size_limit"], c["budget"], v, *(d[k] for k in COLS)])
    prog = [["n", "version", *COLS]]
    for n, r in progression():
        for v, s in r.items():
            d = s.as_dict()
            prog.append([n, v, *(d[k] for k in COLS)])
    (o / "cases.json").write_text(json.dumps(allr, indent=1) + "\n")
    (o / "cases.csv").write_text(_csv(rows))
    (o / "progression.csv").write_text(_csv(prog))
    (o / "SHA256SUMS").write_text("".join(
        f"{hashlib.sha256((o / n).read_bytes()).hexdigest()}  {n}\n" for n in FILES))
    print(f"wrote {len(allr)} cases and {len(prog) - 1} progression rows to {o}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
