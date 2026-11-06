"""Port of the size accounting in regex 1.5.4's `Compiler` (src/compile.rs).

* "pre" - compile.rs at b92ffd5 (parent of fix ae70b41);
* "fix" - compile.rs at ae70b41 (CVE-2022-24713): `Empty` and an empty
  `c_concat` go through `c_empty()`, which adds size_of::<Inst>() to
  `extra_inst_bytes`.

Ported: compile_one (forward, not DFA, Unicode chars, one expression), c,
c_capture, c_char, c_empty_look, c_concat, c_alternate, c_repeat and all
c_repeat_* functions, push_hole / push_split_hole / pop_split_hole and
check_size. Back-patching (fill, fill_split, dup_one) is not ported because it
never changes `insts.len()` or `extra_inst_bytes`; holes are kept only as
placeholders. Line numbers are for the pre file.

Every call to `c()` is counted and checked against an external budget.
When the budget runs out the status is MODEL_LIMIT.
"""
from dataclasses import dataclass, field

from . import hir as H

VERSIONS = ("pre", "fix")
INST_SIZE = 32          # size_of::<Inst>() on 64-bit; see tools/inst_size.rs
DEFAULT_SIZE_LIMIT = 10 * (1 << 20)   # re_builder.rs l.22
DEFAULT_BUDGET = 2_000_000


class CompiledTooBig(Exception):
    pass


class _Budget(Exception):
    pass


@dataclass
class Stats:
    version: str
    status: str = ""              # OK, COMPILED_TOO_BIG, MODEL_LIMIT
    c_calls: int = 0              # calls to c() == calls to check_size()
    insts: int = 0                # insts.len() at the end or at the stop
    extra_inst_bytes: int = 0
    empty_hits: int = 0           # Empty / empty concat reached (both versions)
    empty_accounted: int = 0      # of those, how many added bytes (fix only)
    size_at_stop: int = 0
    size_limit: int = DEFAULT_SIZE_LIMIT
    budget: int = DEFAULT_BUDGET
    trace: list = field(default_factory=list)

    def as_dict(self):
        d = {k: getattr(self, k) for k in self.__dataclass_fields__}
        d.pop("trace")
        return d


@dataclass
class Patch:
    entry: int


class Compiler:
    def __init__(self, version: str, size_limit: int = DEFAULT_SIZE_LIMIT,
                 budget: int = DEFAULT_BUDGET, inst_size: int = INST_SIZE):
        if version not in VERSIONS:
            raise ValueError(version)
        self.v = version
        self.insts = 0
        self.extra = 0
        self.size_limit = size_limit
        self.inst_size = inst_size
        self.S = Stats(version, size_limit=size_limit, budget=budget)
        self.budget = budget

    def size(self):
        return self.extra + self.insts * self.inst_size

    # l.810-820
    def check_size(self):
        if self.size() > self.size_limit:
            raise CompiledTooBig

    def push_hole(self):
        self.insts += 1
        return self.insts - 1

    push_split_hole = push_hole

    def pop_split_hole(self):
        self.insts -= 1
        return None

    def next_inst(self):
        return Patch(self.insts)

    def c_empty(self):
        """ae70b41: the "fake" size increase; pre returns Ok(None) directly."""
        self.S.empty_hits += 1
        if self.v == "fix":
            self.extra += self.inst_size
            self.S.empty_accounted += 1
        return None

    # l.257-379 (only the HIR kinds of the subset)
    def c(self, e):
        self.S.c_calls += 1
        if self.S.c_calls > self.budget:
            raise _Budget
        self.check_size()
        if isinstance(e, H.Empty):
            return self.c_empty()
        if isinstance(e, H.Literal):
            return Patch(self.push_hole())          # c_char, l.428
        if isinstance(e, H.Anchor):
            return Patch(self.push_hole())          # c_empty_look, l.487
        if isinstance(e, H.Group):
            if e.capture is None:
                return self.c(e.hir)
            return self.c_capture(e.hir)
        if isinstance(e, H.Concat):
            return self.c_concat(iter(e.items))
        if isinstance(e, H.Alternation):
            return self.c_alternate(e.items)
        if isinstance(e, H.Repetition):
            return self.c_repeat(e)
        raise TypeError(e)

    # l.381-396 (num_exprs == 1, not DFA)
    def c_capture(self, e):
        entry = self.insts
        self.push_hole()
        self.c(e)
        self.push_hole()
        return Patch(entry)

    # l.492-514
    def c_concat(self, exprs):
        first = None
        for e in exprs:
            p = self.c(e)
            if p is not None:
                first = p
                break
        else:
            return self.c_empty() if self.v == "fix" else self._pre_empty_concat()
        for e in exprs:
            self.c(e)
        return first

    def _pre_empty_concat(self):
        self.S.empty_hits += 1
        return None

    # l.516-563
    def c_alternate(self, exprs):
        first_split_entry = self.insts
        for e in exprs[:-1]:
            self.push_split_hole()
            self.c(e)
        self.c(exprs[-1])
        return Patch(first_split_entry)

    # l.565-581
    def c_repeat(self, r):
        if r.kind == "ZeroOrOne":
            return self.c_repeat_zero_or_one(r.hir)
        if r.kind == "ZeroOrMore":
            return self.c_repeat_zero_or_more(r.hir)
        if r.kind == "OneOrMore":
            return self.c_repeat_one_or_more(r.hir)
        if r.kind == "Exactly":
            return self.c_repeat_range(r.hir, r.min, r.min)
        if r.kind == "AtLeast":
            return self.c_repeat_range_min_or_more(r.hir, r.min)
        return self.c_repeat_range(r.hir, r.min, r.max)

    def c_repeat_zero_or_one(self, e):          # l.583-601
        entry = self.insts
        self.push_split_hole()
        if self.c(e) is None:
            return self.pop_split_hole()
        return Patch(entry)

    def c_repeat_zero_or_more(self, e):         # l.603-622
        entry = self.insts
        self.push_split_hole()
        if self.c(e) is None:
            return self.pop_split_hole()
        return Patch(entry)

    def c_repeat_one_or_more(self, e):          # l.624-642
        p = self.c(e)
        if p is None:
            return None
        self.push_split_hole()
        return p

    def c_repeat_range_min_or_more(self, e, lo):  # l.644-663
        pc = self.c_concat(_repeat(e, lo))
        if pc is None:
            pc = self.next_inst()
        if self.c_repeat_zero_or_more(e) is not None:
            return Patch(pc.entry)
        return None

    def c_repeat_range(self, e, lo, hi):        # l.665-719
        pc = self.c_concat(_repeat(e, lo))
        if lo == hi:
            return pc
        if pc is None:
            pc = self.next_inst()
        for _ in range(lo, hi):
            self.push_split_hole()
            if self.c(e) is None:
                return self.pop_split_hole()
        return Patch(pc.entry)

    # l.129-152
    def compile_one(self, e):
        try:
            self.c_capture(e)
            self.push_hole()                        # Match(0)
            self.S.status = "OK"
        except CompiledTooBig:
            self.S.status = "COMPILED_TOO_BIG"
        except _Budget:
            self.S.status = "MODEL_LIMIT"
            self.S.c_calls = self.budget
        self.S.insts = self.insts
        self.S.extra_inst_bytes = self.extra
        self.S.size_at_stop = self.size()
        return self.S


def _repeat(e, n):
    """iter::repeat(expr).take(n) without materialising n items."""
    for _ in range(n):
        yield e


def compile_pattern(pattern: str, version: str, size_limit: int = DEFAULT_SIZE_LIMIT,
                    budget: int = DEFAULT_BUDGET) -> Stats:
    return Compiler(version, size_limit, budget).compile_one(H.parse(pattern))
