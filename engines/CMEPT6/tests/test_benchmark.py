"""Failure-oriented tests: reject invalid output instead of publishing a result."""
import queue
import unittest
from unittest.mock import Mock
from benchmark import BenchEngine, EngineFailure, parse_result, load_suite, DEFAULT_SUITE, summarize

START = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'
INFO = 'info depth 4 score cp 12 nodes 900 time 8 nps 112500 pv e2e4 e7e5'


class BenchmarkTests(unittest.TestCase):
    def test_suite(self):
        self.assertEqual(len(load_suite(DEFAULT_SUITE)), 6)

    def test_completed_iteration_is_not_node_budget(self):
        result = parse_result([INFO, 'bestmove e2e4'], START, .01)
        self.assertEqual(result['last_completed_nodes'], 900)
        self.assertNotIn('total_nodes', result)

    def test_reject_illegal_bestmove(self):
        for move in ('e2e5', '0000'):
            with self.assertRaises(EngineFailure):
                parse_result([INFO, 'bestmove ' + move], START, .01)

    def test_reject_missing_telemetry(self):
        with self.assertRaises(EngineFailure):
            parse_result(['bestmove e2e4'], START, .01)

    def test_terminal_position(self):
        result = parse_result(['bestmove 0000'], '7k/5K2/6Q1/8/8/8/8/8 b - - 0 1', .01)
        self.assertIsNone(result['completed_depth'])

    def test_incomplete_pairs_cannot_produce_summary(self):
        with self.assertRaises(ValueError):
            summarize([])
        with self.assertRaises(ValueError):
            summarize([{'repeat':0, 'position':'start', 'engine':'baseline'}])

    def test_crash_and_timeout(self):
        for crashed in (True, False):
            engine = BenchEngine.__new__(BenchEngine)
            engine.timeout = .002
            engine.new_game = Mock(); engine.send = Mock(); engine.ready = Mock()
            engine.lines = queue.Queue()
            if crashed:
                engine.lines.put(None)
            with self.assertRaises(EngineFailure):
                engine.measure(START, 'go depth 4')


if __name__ == '__main__':
    unittest.main()
