import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orchestrator import db, market_data, trading_engine


class TestTradingMath(unittest.TestCase):
    def test_sma_is_correct(self):
        closes = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        self.assertEqual(trading_engine._sma(closes, 5), 8.0)  # (6+7+8+9+10)/5

    def test_sma_raises_on_insufficient_data(self):
        with self.assertRaises(trading_engine.TradingEngineError):
            trading_engine._sma([1, 2, 3], 5)

    def test_rsi_is_correct(self):
        # deltas over last 4: +1,+1,+1,-1 -> avg_gain=0.75, avg_loss=0.25
        # RS=3 -> RSI = 100 - 100/(1+3) = 75.0
        closes = [10, 11, 12, 13, 12]
        self.assertAlmostEqual(trading_engine._rsi(closes, 4), 75.0)

    def test_rsi_is_100_when_no_losses(self):
        closes = [10, 11, 12, 13, 14]
        self.assertEqual(trading_engine._rsi(closes, 4), 100.0)


class TestTradingEngine(unittest.TestCase):
    def setUp(self):
        self._orig_db_path = db.config.DB_PATH
        self._tmp_dir = tempfile.mkdtemp(prefix="shakthi_trading_test_")
        db.config.DB_PATH = f"{self._tmp_dir}/test.db"
        db.init_db()

    def tearDown(self):
        import shutil
        db.config.DB_PATH = self._orig_db_path
        shutil.rmtree(self._tmp_dir, ignore_errors=True)

    def test_create_strategy_requires_sma_params(self):
        with self.assertRaises(trading_engine.TradingEngineError):
            trading_engine.create_strategy("Test", "BTCUSDT", "sma_crossover", {"fast_period": 10})

    def test_create_strategy_requires_rsi_params(self):
        with self.assertRaises(trading_engine.TradingEngineError):
            trading_engine.create_strategy("Test", "BTCUSDT", "rsi_threshold", {"period": 14})

    def test_create_strategy_rejects_unknown_rule_type(self):
        with self.assertRaises(trading_engine.TradingEngineError):
            trading_engine.create_strategy("Test", "BTCUSDT", "not_a_real_rule", {})

    def test_bullish_signal_opens_real_position_and_journals_entry(self):
        trading_engine.create_strategy("Test SMA", "BTCUSDT", "sma_crossover",
                                        {"fast_period": 2, "slow_period": 4, "trade_quantity": 0.01})
        # Rising closes -> fast SMA > slow SMA -> bullish
        with patch.object(market_data, "closing_prices", return_value=[10, 20, 30, 40, 50]), \
             patch.object(market_data, "current_price", return_value=51.0):
            results = trading_engine.run_signal_check()

        self.assertEqual(results[0]["action"], "entry")
        positions = trading_engine.list_positions(status="open")
        self.assertEqual(len(positions), 1)
        self.assertEqual(positions[0]["entry_price"], 51.0)
        journal = trading_engine.list_journal()
        self.assertEqual(len(journal), 1)
        self.assertEqual(journal[0]["action"], "entry")

    def test_running_check_twice_does_not_duplicate_open_position(self):
        trading_engine.create_strategy("Test SMA", "BTCUSDT", "sma_crossover",
                                        {"fast_period": 2, "slow_period": 4, "trade_quantity": 0.01})
        with patch.object(market_data, "closing_prices", return_value=[10, 20, 30, 40, 50]), \
             patch.object(market_data, "current_price", return_value=51.0):
            trading_engine.run_signal_check()
            second = trading_engine.run_signal_check()

        self.assertEqual(second[0]["action"], "hold")
        self.assertEqual(len(trading_engine.list_positions(status="open")), 1)

    def test_bearish_signal_closes_position_with_correct_pnl(self):
        trading_engine.create_strategy("Test SMA", "BTCUSDT", "sma_crossover",
                                        {"fast_period": 2, "slow_period": 4, "trade_quantity": 2})
        with patch.object(market_data, "closing_prices", return_value=[10, 20, 30, 40, 50]), \
             patch.object(market_data, "current_price", return_value=50.0):
            trading_engine.run_signal_check()  # opens at 50.0, qty 2

        # Falling closes -> fast SMA < slow SMA -> bearish -> exit
        with patch.object(market_data, "closing_prices", return_value=[50, 40, 30, 20, 10]), \
             patch.object(market_data, "current_price", return_value=60.0):
            results = trading_engine.run_signal_check()

        self.assertEqual(results[0]["action"], "exit")
        self.assertEqual(results[0]["pnl"], 20.0)  # (60 - 50) * 2
        self.assertEqual(len(trading_engine.list_positions(status="open")), 0)
        closed = trading_engine.list_positions(status="closed")
        self.assertEqual(closed[0]["exit_price"], 60.0)

        journal = trading_engine.list_journal()
        exit_entry = [j for j in journal if j["action"] == "exit"][0]
        self.assertEqual(exit_entry["pnl"], 20.0)

    def test_paused_strategy_is_never_checked(self):
        strat = trading_engine.create_strategy("Test SMA", "BTCUSDT", "sma_crossover",
                                                 {"fast_period": 2, "slow_period": 4, "trade_quantity": 0.01})
        trading_engine.set_strategy_status(strat["id"], "paused")
        with patch.object(market_data, "closing_prices", return_value=[10, 20, 30, 40, 50]), \
             patch.object(market_data, "current_price", return_value=51.0):
            results = trading_engine.run_signal_check()

        self.assertEqual(results, [])

    def test_market_data_error_reported_not_crashed(self):
        trading_engine.create_strategy("Test SMA", "BTCUSDT", "sma_crossover",
                                        {"fast_period": 2, "slow_period": 4, "trade_quantity": 0.01})
        with patch.object(market_data, "closing_prices", side_effect=market_data.MarketDataError("network down")):
            results = trading_engine.run_signal_check()

        self.assertEqual(results[0]["action"], "error")


if __name__ == "__main__":
    unittest.main()
