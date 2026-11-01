# pool-odds

Exact probabilities for dice pools, including the awkward ones: keep highest, keep lowest, advantage and disadvantage on a d20, and exploding dice that reroll and add. Every number is computed with fractions, so the tool gives the real answer instead of an estimate from a simulation, and no random seed ever enters the result.

## Why

A plain 3d6 is easy to look up. `4d6kh3`, `2d20kl1`, or `5d10kh2+3` are not, and they are the ones a table actually needs when someone is deciding whether a difficulty number is fair. This tool answers the question in one line and shows the whole distribution if you want it.

## Install

```
pip install .
```

Or run it straight from a checkout with no install step at all:

```
python3 -m pool_odds "4d6kh3"
```

## Usage

```
pool-odds EXPRESSION [--json] [--at-least N] [--at-most N]
```

```
$ pool-odds 4d6kh3
expression: 4d6kh3
mean: 12.2446   stddev: 2.8468   range: 3 to 18

  value      exactly     at least
      3      0.0772%    100.0000%
      4      0.3086%     99.9228%
      5      0.7716%     99.6142%
      6      1.6204%     98.8426%
      7      2.9321%     97.2222%
      8      4.7840%     94.2901%
      9      7.0216%     89.5062%
     10      9.4136%     82.4846%
     11     11.4198%     73.0710%
     12     12.8858%     61.6512%
     13     13.2716%     48.7654%
     14     12.3457%     35.4938%
     15     10.1080%     23.1481%
     16      7.2531%     13.0401%
     17      4.1667%      5.7870%
     18      1.6204%      1.6204%
```

Ask for one number when that is all you need:

```
$ pool-odds 2d20kh1 --at-least 15
at least 15: 51.0000%
```

`--json` prints the full distribution with floats for plotting and reduced fractions for anyone who wants the closed form:

```
$ pool-odds 2d6 --json
{
  "expression": "2d6",
  "mean": 7.0,
  "stddev": 2.41522945769824,
  "min": 2,
  "max": 12,
  "probabilities": {"2": 0.027777777777777776, ...},
  "exact": {"2": "1/36", "3": "1/18", "7": "1/6", ...}
}
```

From Python:

```python
from pool_odds import parse, pool, mean, at_least

spec = parse("4d6kh3+2")
table = pool(spec.n, spec.faces, keep=spec.keep, highest=spec.highest)
print(float(mean(table)))
print(float(at_least(table, 15)))
```

## Expressions

- `4d6` and `d20` roll the pool and sum every die. A missing count means one die.
- `4d6kh3` sums the three highest dice. `4d6k3` is the same thing.
- `4d6kl3` sums the three lowest dice, which is how a lot of roll under systems work.
- `2d20kh1` is advantage, `2d20kl1` is disadvantage.
- `3d6!` rerolls and adds whenever a die shows its top face.
- `+2` and `-1` shift the total by a flat amount.

## How it works

The pool is a dynamic program over the dice. The state is only the set of values that are still worth keeping, sorted, so a 10d6 keep 4 pool touches a few hundred states rather than enumerating 60466176 rolls. Probabilities are `fractions.Fraction` from the standard library, so there is no floating point drift and no Monte Carlo noise anywhere in the pipeline.

The test suite checks the dynamic program against brute force enumeration of every possible roll for the 4d6 keep 3 and 2d20 keep 1 cases, which is the only way to be sure the state merge is not quietly wrong.

## Limits

- One pool per expression. Mixed pools such as `2d6+1d8` are not supported.
- Keep clauses apply to the whole pool, not to subsets.
- Exploding dice model a chain of up to 20 straight top rolls. For a d6 that is a chance of about 3e-16, and the remaining mass is folded onto the top value rather than dropped, so the distribution still sums to exactly one. The CLI says so in the table whenever a pool explodes.
- At most 1000 dice in a pool, since the parser caps the count at three digits.

## Tests

```
python3 -m unittest discover -s tests
```

## License

MIT. See LICENSE.
