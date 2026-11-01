# Public surface of the package. The CLI imports the modules directly, but
# anyone using the library only needs these names.
from .dist import (
    DEFAULT_EXPLODE_LIMIT,
    at_least,
    at_most,
    convolve,
    explode,
    mean,
    pool,
    shift,
    stddev,
    uniform_die,
    variance,
)
from .parse import ParseError, Spec, parse

__all__ = [
    "DEFAULT_EXPLODE_LIMIT",
    "ParseError",
    "Spec",
    "at_least",
    "at_most",
    "convolve",
    "explode",
    "mean",
    "parse",
    "pool",
    "shift",
    "stddev",
    "uniform_die",
    "variance",
]

__version__ = "0.1.0"
