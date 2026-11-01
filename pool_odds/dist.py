# Exact distributions over integer outcomes.
# Every probability is a Fraction, so a pool result is exact rather than a
# floating point estimate. That matters for keep-highest pools, which are the
# ones people usually end up guessing at a table.
from fractions import Fraction

# Longest chain of exploding rerolls that is modelled exactly before the
# remaining mass is folded onto the final value. See explode() for why.
DEFAULT_EXPLODE_LIMIT = 20


def point(value):
    # A distribution with all of its mass on a single outcome.
    return {value: Fraction(1)}


def shift(dist, amount):
    # Move every outcome by a constant without touching the probabilities.
    return {v + amount: p for v, p in dist.items()}


def convolve(left, right):
    # Distribution of the sum of two independent variables.
    out = {}
    for va, pa in left.items():
        for vb, pb in right.items():
            key = va + vb
            out[key] = out.get(key, 0) + pa * pb
    return out


def scaled(dist, factor):
    # Multiply every probability by a constant. Used when mixing branches.
    return {v: p * factor for v, p in dist.items()}


def total(dist):
    # Sum of all probability mass, used by the tests to catch leaks.
    return sum(dist.values(), Fraction(0))


def uniform_die(faces):
    # A single fair die with faces 1..faces.
    if faces < 2:
        raise ValueError("a die needs at least two faces")
    return {f: Fraction(1, faces) for f in range(1, faces + 1)}


def explode(faces, limit=DEFAULT_EXPLODE_LIMIT):
    # A single die that rolls again and adds whenever it shows its top face.
    # A chain of j top faces followed by a normal face has probability
    # (1/faces)^(j+1), so the chain length is truncated at `limit` and the
    # leftover mass is parked on limit*faces. For a d6 the chance of even ten
    # straight sixes is about 1.7e-8, so the tail is folded rather than dropped
    # and the total still sums to exactly 1.
    if faces < 2:
        raise ValueError("a die needs at least two faces")
    if limit < 1:
        raise ValueError("explode limit must be positive")
    out = {}
    chain = Fraction(1)
    for j in range(limit):
        for face in range(1, faces):
            value = j * faces + face
            out[value] = out.get(value, 0) + chain * Fraction(1, faces)
        chain *= Fraction(1, faces)
    out[limit * faces] = out.get(limit * faces, 0) + chain
    return out


def _merge(state, value, keep, highest):
    # Insert a new die into the kept set and keep only the best (or worst)
    # `keep` values. The state is sorted so identical sets collapse in the DP.
    seq = list(state)
    seq.append(value)
    seq.sort(reverse=highest)
    return tuple(seq[:keep])


def pool(n, faces, keep=None, highest=True, exploding=False, limit=DEFAULT_EXPLODE_LIMIT):
    # Distribution of the sum of the kept dice from a pool of n dice.
    # The dynamic program carries only the values currently worth keeping, so
    # a 10d6 keep 3 pool stays small instead of enumerating 6**10 outcomes.
    if n < 1:
        raise ValueError("a pool needs at least one die")
    die = explode(faces, limit) if exploding else uniform_die(faces)
    size = n if keep is None else keep
    if size < 1 or size > n:
        raise ValueError("keep must be between 1 and the pool size")
    states = {(): Fraction(1)}
    for _ in range(n):
        nxt = {}
        for state, prob in states.items():
            for value, pv in die.items():
                merged = _merge(state, value, size, highest)
                nxt[merged] = nxt.get(merged, 0) + prob * pv
        states = nxt
    out = {}
    for state, prob in states.items():
        key = sum(state)
        out[key] = out.get(key, 0) + prob
    return out


def mean(dist):
    # Exact expected value as a Fraction.
    return sum((v * p for v, p in dist.items()), Fraction(0))


def variance(dist):
    # Exact second central moment as a Fraction.
    mu = mean(dist)
    return sum((p * (v - mu) ** 2 for v, p in dist.items()), Fraction(0))


def stddev(dist):
    # Square root of the variance, rounded to a float at the very end.
    return float(variance(dist)) ** 0.5


def at_least(dist, target):
    # Probability that the outcome is target or higher.
    return sum((p for v, p in dist.items() if v >= target), Fraction(0))


def at_most(dist, target):
    # Probability that the outcome is target or lower.
    return sum((p for v, p in dist.items() if v <= target), Fraction(0))


def min_value(dist):
    return min(dist)


def max_value(dist):
    return max(dist)
