# coding: utf-8
"""Regressions for the snake client: multi-grid raster stability, warmup terminal states,
prompt forwarding, and backend captions derived from recorded provenance."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "evals" / "snake"))

from snake.game import DIRECTIONS, SnakeGame  # noqa: E402
from snake.multi import run_multi  # noqa: E402
from snake.multi_replay import backend_caption  # noqa: E402
from snake.multi_ui import CELL_H, CELL_W, TOP_BAR, compose_multi  # noqa: E402
from snake.replay import TerminalRaster  # noqa: E402
from snake.warmup import warm_up  # noqa: E402


def a_frame(seed, at=0.0):
    game = SnakeGame(24, 16, seed, 6)
    return {
        "type": "frame",
        "at": at,
        "seed": seed,
        "round": 1,
        "game": game.snapshot(),
        "decision": {},
        "steps": 0,
        "deaths": 0,
        "interventions": 0,
    }


def pending(seed):
    return {"seed": seed, "pending": True, "width": 24, "height": 16}


def stats(**overrides):
    base = {"alive": 1, "waiting": 15, "dps": 0, "mean_ms": 0, "score": 0, "clock": "00:00"}
    base.update(overrides)
    return base


class ExplodingPolicy:
    def decide(self, game):  # pragma: no cover - must never run
        raise AssertionError("decide called on a game with no moves")


class CountingPolicy:
    def __init__(self):
        self.calls = 0

    def decide(self, game):
        self.calls += 1
        moves = [m for m in game.moves() if m.legal]
        return SimpleNamespace(executed=(moves or game.moves())[0].direction)


class TestWarmup(unittest.TestCase):
    def test_warmup_stops_when_the_warm_game_wins(self):
        # 4x4 board, length 15, seed 0, RIGHT: eating the last cell wins in one step,
        # and a won game stays "alive" while its move list is empty.
        game = SnakeGame(4, 4, 0, 15)
        self.assertEqual(game.legal_reason("RIGHT"), "legal")
        self.assertEqual(game.target("RIGHT"), game.food)
        game.step("RIGHT")
        self.assertTrue(game.won)
        self.assertTrue(game.alive)
        self.assertEqual(game.moves(), [])
        warm_up(ExplodingPolicy(), game)

    def test_warmup_respects_the_step_budget(self):
        policy = CountingPolicy()
        warm_up(policy, SnakeGame(24, 16, 7, 6), steps=3)
        self.assertEqual(policy.calls, 3)

    def test_warmup_runs_on_a_normal_board(self):
        policy = CountingPolicy()
        warm_up(policy, SnakeGame(24, 16, 7, 6))
        self.assertEqual(policy.calls, 6)


class TestMultiGridRaster(unittest.TestCase):
    def test_canvas_size_is_constant_with_pending_slots(self):
        frame = a_frame(1000)
        partial = compose_multi([frame] + [pending(s) for s in range(1, 16)], stats(), 4, "C")
        full = compose_multi([frame] * 16, stats(waiting=0), 4, "C")
        self.assertEqual((partial.width, partial.height), (full.width, full.height))
        self.assertEqual(full.height, TOP_BAR + 4 * CELL_H + 2)

    def test_raster_keeps_every_row_inside_the_image(self):
        canvas = compose_multi([a_frame(1000 + i) for i in range(16)], stats(waiting=0), 4, "C")
        raster = TerminalRaster(canvas.width, canvas.height, width=1920, height=1080)
        self.assertLessEqual(raster.y + canvas.height * raster.ch, 1080)

    def test_pending_slots_render_a_placeholder(self):
        canvas = compose_multi([a_frame(1000), pending(1001)], stats(waiting=1), 2, "C")
        text = "".join("".join(row) for row in canvas.chars)
        self.assertIn("pending", text)
        self.assertIn("#1001", text)

    def test_width_matches_the_grid(self):
        canvas = compose_multi([pending(s) for s in range(4)], stats(), 4, "C")
        self.assertEqual(canvas.width, 6 + 4 * CELL_W)


class TestPromptForwarding(unittest.TestCase):
    def test_multi_forwards_the_selected_prompt(self):
        captured = {}

        class FakePolicy:
            def __init__(self, *args, **kwargs):
                captured.update(kwargs)
                self.metadata = {}

            def decide(self, game):
                moves = [m for m in game.moves() if m.legal]
                return SimpleNamespace(
                    executed=(moves or game.moves())[0].direction,
                    to_dict=lambda: {},
                    inference_ms=0.1,
                    intervened=False,
                )

        with tempfile.TemporaryDirectory() as tmp:
            record = Path(tmp) / "rec.jsonl"
            with mock.patch("snake.multi.LayaPolicy", FakePolicy):
                run_multi(
                    [
                        "--games", "1", "--steps", "1", "--fps", "100",
                        "--prompt", "detailed", "--record", str(record),
                    ]
                )
            first = json.loads(record.read_text().splitlines()[0])
            self.assertEqual(first["settings"]["prompt"], "detailed")

        self.assertEqual(captured.get("prompt"), "detailed")


class TestBackendCaption(unittest.TestCase):
    def test_caption_follows_the_recorded_engine(self):
        caption = backend_caption({"model": {"engine_label": "torch cpu · float32"}})
        self.assertIn("TORCH CPU", caption)
        self.assertNotIn("NATIVE", caption)
        self.assertNotIn("H800", caption)

    def test_unknown_engine_stays_unknown(self):
        for metadata in ({}, {"model": {}}, {"model": {"engine_label": "unknown"}}):
            self.assertIn("UNKNOWN ENGINE", backend_caption(metadata))

    def test_native_recording_does_not_claim_hardware_it_did_not_record(self):
        caption = backend_caption({"model": {"engine_label": "native CUDA sm_90a · BF16"}})
        self.assertIn("NATIVE CUDA SM_90A · BF16", caption)
        self.assertNotIn("H800", caption)


if __name__ == "__main__":
    unittest.main()
