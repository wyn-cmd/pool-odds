# Parsing for the compact dice expressions the tool accepts, such as
# 4d6kh3+2 or 2d20kl1 or 3d8!.
import re
from dataclasses import dataclass

# Pool size, die faces, optional explode marker, optional keep clause and an
# optional flat modifier. The pool size defaults to 1 when it is left out.
PATTERN = re.compile(
    r"^(?P<n>\d{0,3})d(?P<faces>\d{1,4})(?P<explode>!?)"
    r"(?:(?P<mode>kh|kl|k)(?P<keep>\d{1,3}))?"
    r"(?P<mod>[+-]\d{1,4})?$",
    re.IGNORECASE,
)


class ParseError(ValueError):
    # Raised for anything the grammar will not accept. Kept separate from the
    # generic ValueError so the CLI can print usage instead of a traceback.
    pass


@dataclass(frozen=True)
class Spec:
    # A parsed pool description, already validated.
    n: int
    faces: int
    explode: bool
    keep: int
    highest: bool
    mod: int

    def label(self):
        # Canonical spelling of the expression, useful in JSON output.
        parts = ["%dd%d" % (self.n, self.faces)]
        if self.explode:
            parts.append("!")
        if self.keep != self.n:
            parts.append(("kh" if self.highest else "kl") + str(self.keep))
        if self.mod:
            parts.append("%+d" % self.mod)
        return "".join(parts)


def parse(text):
    # Turn an expression into a Spec or raise ParseError with a plain reason.
    if text is None:
        raise ParseError("empty expression")
    cleaned = "".join(text.split()).lower()
    if not cleaned:
        raise ParseError("empty expression")
    match = PATTERN.match(cleaned)
    if not match:
        raise ParseError("cannot read %r, expected something like 4d6kh3+2" % text)
    n = int(match.group("n")) if match.group("n") else 1
    faces = int(match.group("faces"))
    explode = match.group("explode") == "!"
    mode = (match.group("mode") or "").lower()
    mod = int(match.group("mod")) if match.group("mod") else 0
    if n < 1:
        raise ParseError("a pool needs at least one die")
    if faces < 2:
        raise ParseError("a die needs at least two faces")
    keep = n
    highest = True
    if mode:
        keep = int(match.group("keep"))
        if keep < 1 or keep > n:
            raise ParseError("keep must be between 1 and %d dice" % n)
        # A bare k means keep highest, matching the usual shorthand.
        highest = mode != "kl"
    return Spec(n=n, faces=faces, explode=explode, keep=keep, highest=highest, mod=mod)
