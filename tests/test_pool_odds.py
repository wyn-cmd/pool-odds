# Tests for the exact dice pool math and the command line wrapper.
# The keep-highest case is checked against brute force enumeration over every
# possible roll, so the dynamic program cannot quietly agree with itself.
import itertools
import json
import os
import subprocess
import sys
import unittest
from fractions import Fraction

from pool_odds import dist as d
from pool_odds.cli import build_distribution, render_table
from pool_odds.parse import ParseError, parse

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def brute_force(n, faces, keep=None, highest=True):
    # Enumerate every ordered roll and tabulate the sum of the kept dice.
    counts = {}
    for roll in itertools.product(range(1, faces + 1), repeat=n):
        chosen = sorted(roll, reverse=highest)[: (keep or n)]
        s = sum(chosen)
        counts[s] = counts.get(s, 0) + 1
    total = faces ** n
    return {k: Fraction(v, total) for k, v in counts.items()}


class SumTests(unittest.TestCase):
    def test_single_die_is_uniform(self):
        table = d.pool(1, 6)
        self.assertEqual([table[f] for f in range(1, 7)], [Fraction(1, 6)] * 6)

    def test_two_d6_matches_known_counts(self):
        table = d.pool(2, 6)
        self.assertEqual(table[2], Fraction(1, 36))
        self.assertEqual(table[7], Fraction(6, 36))
        self.assertEqual(table[12], Fraction(1, 36))
        self.assertEqual(d.total(table), 1)

    def test_convolution_matches_pool(self):
        table = d.convolve(d.uniform_die(6), d.uniform_die(6))
        self.assertEqual(table, d.pool(2, 6))


class KeepTests(unittest.TestCase):
    def test_keep_highest_three_of_four(self):
        table = d.pool(4, 6, keep=3)
        self.assertEqual(table, brute_force(4, 6, keep=3))
        self.assertEqual(table[18], Fraction(21, 1296))
        self.assertEqual(d.total(table), 1)

    def test_keep_lowest_three_of_four(self):
        table = d.pool(4, 6, keep=3, highest=False)
        self.assertEqual(table, brute_force(4, 6, keep=3, highest=False))

    def test_advantage_on_a_d20(self):
        table = d.pool(2, 20, keep=1)
        self.assertEqual(table, brute_force(2, 20, keep=1))
        self.assertTrue(abs(float(d.mean(table)) - 13.825) < 1e-9)

    def test_disadvantage_mean(self):
        table = d.pool(2, 20, keep=1, highest=False)
        self.assertTrue(abs(float(d.mean(table)) - 7.175) < 1e-9)

    def test_keep_all_equals_plain_sum(self):
        self.assertEqual(d.pool(3, 8, keep=3), d.pool(3, 8))

    def test_bad_keep_size_rejected(self):
        with self.assertRaises(ValueError):
            d.pool(2, 6, keep=3)


class ExplodeTests(unittest.TestCase):
    def test_mass_is_exactly_one(self):
        self.assertEqual(d.total(d.explode(6)), 1)

    def test_mean_matches_geometric_series(self):
        # A d6 that rerolls and adds on a six has a mean of 3.5 / (1 - 1/6).
        got = float(d.mean(d.explode(6)))
        self.assertTrue(abs(got - 4.2) < 1e-9)

    def test_pool_with_exploding_dice_is_sane(self):
        table = d.pool(3, 6, exploding=True)
        self.assertEqual(d.total(table), 1)
        self.assertGreater(float(d.mean(table)), 3 * 3.5)


class ParserTests(unittest.TestCase):
    def test_plain_pool(self):
        spec = parse("4d6")
        self.assertEqual((spec.n, spec.faces, spec.keep, spec.mod), (4, 6, 4, 0))

    def test_keep_highest_and_modifier(self):
        spec = parse(" 4d6 kh3 +2 ")
        self.assertEqual((spec.n, spec.faces, spec.keep, spec.highest, spec.mod), (4, 6, 3, True, 2))

    def test_bare_k_is_highest(self):
        self.assertTrue(parse("4d6k3").highest)

    def test_keep_lowest(self):
        spec = parse("2d20kl1")
        self.assertFalse(spec.highest)
        self.assertEqual(spec.keep, 1)

    def test_explode_flag(self):
        self.assertTrue(parse("3d8!").explode)

    def test_leading_pool_size_defaults_to_one(self):
        self.assertEqual(parse("d20").n, 1)

    def test_label_round_trip(self):
        for text in ("4d6kh3+2", "2d20kl1", "3d8!", "1d20"):
            self.assertEqual(parse(parse(text).label()).label(), parse(text).label())

    def test_rejects_garbage(self):
        for bad in ("", "banana", "4x6", "1d1", "0d6", "4d6kh9", "4d6kh0"):
            with self.assertRaises(ParseError, msg="accepted %r" % bad):
                parse(bad)


class CliTests(unittest.TestCase):
    def run_cli(self, *args):
        # Run the real entry point so the printed numbers come from the tool.
        proc = subprocess.run(
            [sys.executable, "-m", "pool_odds"] + list(args),
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        return proc

    def test_json_mean_matches_library(self):
        proc = self.run_cli("4d6kh3", "--json")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        expected = float(d.mean(d.pool(4, 6, keep=3)))
        self.assertAlmostEqual(payload["mean"], expected, places=12)
        self.assertEqual(payload["min"], 3)
        self.assertEqual(payload["max"], 18)

    def test_json_carries_exact_fractions(self):
        proc = self.run_cli("2d6", "--json")
        payload = json.loads(proc.stdout)
        # Fractions are reduced, so the six in thirty six is shown as one in six.
        self.assertEqual(payload["exact"]["7"], "1/6")

    def test_modifier_shifts_range(self):
        proc = self.run_cli("1d6+2", "--json")
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["min"], 3)
        self.assertEqual(payload["max"], 8)

    def test_single_target_output(self):
        proc = self.run_cli("4d6kh3", "--at-least", "15")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        expected = float(d.at_least(d.pool(4, 6, keep=3), 15)) * 100.0
        self.assertIn("%.4f%%" % expected, proc.stdout)

    def test_bad_expression_exits_two(self):
        proc = self.run_cli("4d6kh9")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("keep must be between", proc.stderr)

    def test_table_matches_library(self):
        spec = parse("3d6kl2")
        text = render_table(spec, build_distribution(spec))
        self.assertIn("range: 2 to 12", text)

    def test_explode_output_states_the_chain_limit(self):
        proc = self.run_cli("2d6!", "--json")
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["explode_limit"], 20)
        table = self.run_cli("2d6!").stdout
        self.assertIn("reroll chains stop after 20", table)


if __name__ == "__main__":
    unittest.main()
