# Command line front end. The printed numbers come straight from dist.py, so
# what a user sees here is the same distribution the library returns.
import argparse
import json
import sys

from . import dist as d
from .parse import ParseError, parse


def build_distribution(spec):
    # Apply the pool and then the flat modifier on top of it.
    table = d.pool(
        spec.n,
        spec.faces,
        keep=spec.keep,
        highest=spec.highest,
        exploding=spec.explode,
    )
    if spec.mod:
        table = d.shift(table, spec.mod)
    return table


def as_dict(spec, table):
    # JSON friendly view. Probabilities appear as floats for plotting and as
    # exact fractions for anyone who wants the closed form.
    return {
        "expression": spec.label(),
        "dice": spec.n,
        "faces": spec.faces,
        "keep": spec.keep,
        "highest": spec.highest,
        "explode": spec.explode,
        "modifier": spec.mod,
        "mean": float(d.mean(table)),
        "stddev": d.stddev(table),
        "min": d.min_value(table),
        "max": d.max_value(table),
        "probabilities": {str(v): float(p) for v, p in sorted(table.items())},
        "exact": {str(v): "%d/%d" % (p.numerator, p.denominator) for v, p in sorted(table.items())},
        "explode_limit": d.DEFAULT_EXPLODE_LIMIT if spec.explode else None,
    }


def render_table(spec, table):
    # Human readable table of the mass and the tail at each outcome.
    lines = [
        "expression: %s" % spec.label(),
        "mean: %.4f   stddev: %.4f   range: %d to %d"
        % (float(d.mean(table)), d.stddev(table), d.min_value(table), d.max_value(table)),
        "",
        "  value      exactly     at least",
    ]
    if spec.explode:
        # Say plainly where the model stops, instead of letting a 360 on the
        # table look like a real ceiling.
        lines.append(
            "  (reroll chains stop after %d straight top rolls, so the top of the range is folded mass)"
            % d.DEFAULT_EXPLODE_LIMIT
        )
    for value in sorted(table):
        p = table[value]
        lines.append(
            "  %5d   %9.4f%%   %9.4f%%"
            % (value, float(p) * 100.0, float(d.at_least(table, value)) * 100.0)
        )
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="pool-odds",
        description="Exact odds for dice pools such as 4d6kh3 or 2d20kl1.",
    )
    parser.add_argument("expression", help="pool to evaluate, for example 4d6kh3+2")
    parser.add_argument("--json", action="store_true", help="print the distribution as JSON")
    parser.add_argument("--at-least", type=int, dest="at_least", help="only print the chance of reaching this target")
    parser.add_argument("--at-most", type=int, dest="at_most", help="only print the chance of staying at or below this target")
    args = parser.parse_args(argv)

    try:
        spec = parse(args.expression)
    except ParseError as err:
        sys.stderr.write("pool-odds: %s\n" % err)
        return 2

    table = build_distribution(spec)

    if args.at_least is not None or args.at_most is not None:
        # A single question deserves a single number, so the table is skipped.
        out = {"expression": spec.label()}
        if args.at_least is not None:
            out["at_least_%d" % args.at_least] = float(d.at_least(table, args.at_least))
        if args.at_most is not None:
            out["at_most_%d" % args.at_most] = float(d.at_most(table, args.at_most))
        if args.json:
            print(json.dumps(out, indent=2))
        else:
            for key, value in out.items():
                if key == "expression":
                    continue
                label, target = key.rsplit("_", 1)
                print("%s %s: %.4f%%" % (label.replace("_", " "), target, value * 100.0))
        return 0

    if args.json:
        print(json.dumps(as_dict(spec, table), indent=2))
    else:
        print(render_table(spec, table))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
