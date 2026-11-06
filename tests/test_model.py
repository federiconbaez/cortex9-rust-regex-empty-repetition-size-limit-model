import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from regex_size_model import hir as H  # noqa: E402
from regex_size_model.cases import PROGRESSION_N, load, progression, run_case  # noqa: E402
from regex_size_model.compiler import INST_SIZE, compile_pattern  # noqa: E402


class Fixtures(unittest.TestCase):
    def test_hand_derived(self):
        for c in load(ROOT / "fixtures/cases.json"):
            r = run_case(c)
            for v, exp in c["expect"].items():
                for k, want in exp.items():
                    self.assertEqual(r[v][k], want, (c["name"], v, k))


class Parser(unittest.TestCase):
    def test_shapes_follow_regex_syntax_simplifications(self):
        self.assertEqual(H.parse(""), H.Empty())
        self.assertEqual(H.parse("a"), H.Literal("a"))
        self.assertEqual(H.parse("(?:)"), H.Group(None, H.Empty()))
        self.assertEqual(H.parse("(?:|)"), H.Group(None, H.Alternation((H.Empty(), H.Empty()))))
        r = H.parse("x{0}{7}")
        self.assertEqual((r.kind, r.min, r.hir.kind, r.hir.min), ("Exactly", 7, "Exactly", 0))

    def test_rejects_outside_subset(self):
        for bad in ("[a]", "a{5,2}", "a{4294967296}", "(a", "\\d", "a" * 300):
            with self.assertRaises(H.ParseError):
                H.parse(bad)


class Accounting(unittest.TestCase):
    def test_fix_differs_only_by_extra_bytes_when_both_finish(self):
        for pat in ("a{3}", "a{2,4}", "(?:){3}", "(a|b|)c*", "^(?:a?){5}$", "(?:){0,3}x+"):
            p, f = compile_pattern(pat, "pre"), compile_pattern(pat, "fix")
            self.assertEqual((p.status, f.status), ("OK", "OK"), pat)
            self.assertEqual((p.c_calls, p.insts), (f.c_calls, f.insts), pat)
            self.assertEqual(f.extra_inst_bytes - p.extra_inst_bytes, INST_SIZE * f.empty_accounted, pat)
            self.assertEqual(p.empty_hits, f.empty_hits, pat)

    def test_empty_threshold_is_limit_over_inst_size(self):
        # With one instruction on the stack and only empties growing the
        # size, the fix stops after exactly limit / 32 accounted empties.
        for limit in (1024, 4096, 65536):
            for pat in ("(?:){4294967295}", "x{0}{4294967295}", "(?:){64}{64}{64}{64}{64}{64}"):
                f = compile_pattern(pat, "fix", limit, 10**6)
                self.assertEqual((f.status, f.empty_accounted), ("COMPILED_TOO_BIG", limit // INST_SIZE), (pat, limit))


class Progression(unittest.TestCase):
    def test_pre_work_grows_with_n_and_size_stays_constant(self):
        rows = dict(progression())
        for n in PROGRESSION_N[:-1]:
            p = rows[n]["pre"]
            self.assertEqual((p.status, p.c_calls, p.size_at_stop), ("OK", 2 * n + 1, 3 * INST_SIZE), n)
        self.assertEqual(rows[PROGRESSION_N[-1]]["pre"].status, "MODEL_LIMIT")

    def test_fix_work_is_capped(self):
        rows = dict(progression())
        capped = {rows[n]["fix"].c_calls for n in PROGRESSION_N if rows[n]["fix"].status == "COMPILED_TOO_BIG"}
        self.assertEqual(capped, {655362})


class Cli(unittest.TestCase):
    def test_cli(self):
        env = dict(os.environ, PYTHONPATH=str(ROOT / "src"))
        out = subprocess.run([sys.executable, "-m", "regex_size_model", "(?:){4294967295}", "--size-limit",
                              "4096", "--budget", "1000"], capture_output=True, text=True, env=env,
                             check=True).stdout.splitlines()
        self.assertEqual([json.loads(x)["status"] for x in out], ["MODEL_LIMIT", "COMPILED_TOO_BIG"])


if __name__ == "__main__":
    unittest.main()
