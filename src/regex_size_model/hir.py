"""A small parser for a regex subset, producing the HIR shapes of
regex-syntax 0.6.25 (the version in regex 1.5.4's tree at b92ffd5).

This is NOT a port of regex-syntax. It only builds the node kinds the
compiler model needs, with the same simplifications as regex-syntax:
`Hir::concat` and `Hir::alternation` return Empty for 0 items and the item
itself for 1 (hir/mod.rs l.394, l.487), and non-capturing groups stay as
Group nodes (translate.rs l.775-789).

Subset: ASCII letters and digits, `(?:...)`, `(...)`, `|`, `^`, `$`,
`*`, `+`, `?`, `{n}`, `{n,}`, `{n,m}` (each optionally lazy with `?`), and
stacked repetitions such as `(?:){64}{64}`. Counts are u32 as in
regex-syntax.
"""
from dataclasses import dataclass

U32_MAX = 4294967295
MAX_PATTERN_LEN = 256
MAX_NEST = 64


class ParseError(ValueError):
    pass


@dataclass(frozen=True)
class Empty:
    pass


@dataclass(frozen=True)
class Literal:
    c: str


@dataclass(frozen=True)
class Anchor:
    kind: str  # StartText / EndText


@dataclass(frozen=True)
class Group:
    capture: int | None   # None = NonCapturing
    hir: object


@dataclass(frozen=True)
class Concat:
    items: tuple


@dataclass(frozen=True)
class Alternation:
    items: tuple


@dataclass(frozen=True)
class Repetition:
    kind: str           # ZeroOrOne, ZeroOrMore, OneOrMore, Exactly, AtLeast, Bounded
    min: int
    max: int | None
    greedy: bool
    hir: object


def _concat(items):
    return Empty() if not items else items[0] if len(items) == 1 else Concat(tuple(items))


def _alt(items):
    return Empty() if not items else items[0] if len(items) == 1 else Alternation(tuple(items))


class _P:
    def __init__(self, s: str):
        if len(s) > MAX_PATTERN_LEN:
            raise ParseError(f"pattern longer than {MAX_PATTERN_LEN}")
        self.s, self.i, self.caps, self.depth = s, 0, 0, 0

    def peek(self):
        return self.s[self.i] if self.i < len(self.s) else None

    def eat(self, t):
        if self.s.startswith(t, self.i):
            self.i += len(t)
            return True
        return False

    def alt(self):
        branches = [self.concat()]
        while self.eat("|"):
            branches.append(self.concat())
        return _alt(branches)

    def concat(self):
        items = []
        while self.peek() is not None and self.peek() not in "|)":
            items.append(self.repeat())
        return _concat(items)

    def number(self):
        j = self.i
        while self.peek() is not None and self.peek().isdigit():
            self.i += 1
        if j == self.i:
            raise ParseError(f"expected number at {j}")
        n = int(self.s[j:self.i])
        if n > U32_MAX:
            raise ParseError("repetition count exceeds u32")
        return n

    def repeat(self):
        node = self.atom()
        while True:
            c = self.peek()
            if c == "*":
                self.i += 1
                kind, lo, hi = "ZeroOrMore", 0, None
            elif c == "+":
                self.i += 1
                kind, lo, hi = "OneOrMore", 1, None
            elif c == "?":
                self.i += 1
                kind, lo, hi = "ZeroOrOne", 0, 1
            elif c == "{":
                self.i += 1
                lo = self.number()
                if self.eat("}"):
                    kind, hi = "Exactly", lo
                elif self.eat(","):
                    if self.eat("}"):
                        kind, hi = "AtLeast", None
                    else:
                        hi = self.number()
                        if not self.eat("}"):
                            raise ParseError("unclosed counted repetition")
                        if hi < lo:
                            raise ParseError("invalid repetition range")
                        kind = "Bounded"
                else:
                    raise ParseError("bad counted repetition")
            else:
                return node
            greedy = not self.eat("?")
            node = Repetition(kind, lo, hi, greedy, node)

    def atom(self):
        c = self.peek()
        if c is None:
            raise ParseError("unexpected end")
        if c.isascii() and c.isalnum():
            self.i += 1
            return Literal(c)
        if c == "^":
            self.i += 1
            return Anchor("StartText")
        if c == "$":
            self.i += 1
            return Anchor("EndText")
        if c == "(":
            self.depth += 1
            if self.depth > MAX_NEST:
                raise ParseError("nesting too deep")
            if self.eat("(?:"):
                cap = None
            else:
                self.i += 1
                self.caps += 1
                cap = self.caps
            inner = self.alt()
            if not self.eat(")"):
                raise ParseError("unclosed group")
            self.depth -= 1
            return Group(cap, inner)
        raise ParseError(f"unsupported character {c!r} at {self.i}")


def parse(pattern: str):
    p = _P(pattern)
    h = p.alt()
    if p.i != len(pattern):
        raise ParseError(f"unexpected {pattern[p.i]!r} at {p.i}")
    return h
