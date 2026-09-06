import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orchestrator import calculations as calc


class TestCalculations(unittest.TestCase):
    def test_profit(self):
        self.assertEqual(calc.profit(1000, 300, 50), 650)

    def test_operating_margin(self):
        self.assertAlmostEqual(calc.operating_margin(1000, 250), 0.25)

    def test_operating_margin_zero_revenue(self):
        self.assertEqual(calc.operating_margin(0, -50), 0.0)

    def test_cash_flow(self):
        self.assertEqual(calc.cash_flow(1000, 400), 600)

    def test_estimated_tax(self):
        self.assertAlmostEqual(calc.estimated_tax(1000, 0.18), 180.0)

    def test_estimated_tax_never_negative(self):
        # a loss-making period owes no estimated tax
        self.assertEqual(calc.estimated_tax(-500, 0.18), 0.0)

    def test_roi(self):
        self.assertAlmostEqual(calc.roi(1200, 1000), 0.2)

    def test_roi_zero_cost(self):
        self.assertEqual(calc.roi(500, 0), 0.0)

    def test_net_profit_after_tax(self):
        self.assertEqual(calc.net_profit_after_tax(1000, 180), 820)


if __name__ == "__main__":
    unittest.main()
