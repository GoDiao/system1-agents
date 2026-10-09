# coding: utf-8
"""Dollars per episode from Jev's list price and the chat model's catalogue price."""

from __future__ import annotations

import os
from typing import Any
from unittest import TestCase
from unittest.mock import patch

import httpx

from s1a import pricing
from s1a.pricing import ChatPrices, cost_usd, prices_from_rows

ROWS = [
    {
        "id": "google/gemini-2.5-flash",
        "pricing": {"prompt": "0.0000003", "completion": "0.0000025", "input_cache_read": "0.00000003"},
    },
    {"id": "openai/gpt-4o", "pricing": {"prompt": "0.0000025", "completion": "0.00001"}},
]


class TestPrices(TestCase):
    def test_catalogue_rows_match_the_full_id_or_the_bare_model_name(self) -> None:
        self.assertEqual(prices_from_rows(ROWS, "google/gemini-2.5-flash"), ChatPrices(3e-7, 2.5e-6, 3e-8))
        self.assertEqual(
            prices_from_rows(ROWS, "gpt-4o"), ChatPrices(2.5e-6, 1e-5, 2.5e-6), "no cache rate: the input rate"
        )
        self.assertIsNone(prices_from_rows(ROWS, "nobody/such-model"))

    def test_env_override_needs_no_catalogue(self) -> None:
        with patch.dict(os.environ, {"CHAT_USD_PER_M_INPUT": "0.30", "CHAT_USD_PER_M_OUTPUT": "2.50"}, clear=True):
            self.assertEqual(pricing.chat_prices("anything"), ChatPrices(3e-7, 2.5e-6, 3e-7))
        with patch.dict(
            os.environ,
            {"CHAT_USD_PER_M_INPUT": "0.30", "CHAT_USD_PER_M_OUTPUT": "2.50", "CHAT_USD_PER_M_CACHED_INPUT": "0.03"},
            clear=True,
        ):
            self.assertEqual(pricing.env_prices(), ChatPrices(3e-7, 2.5e-6, 3e-8))

    def test_a_catalogue_failure_is_retried_and_a_success_is_kept(self) -> None:
        calls: list[str] = []

        class _Response:
            def json(self) -> dict[str, Any]:
                return {"data": ROWS}

        def flaky_get(url: str, timeout: float) -> _Response:
            calls.append(url)
            if len(calls) == 1:
                raise httpx.ConnectError("catalogue down")
            return _Response()

        with (
            patch.dict(os.environ, {}, clear=True),
            patch.dict(pricing.PRICE_CACHE, clear=True),
            patch.object(pricing.httpx, "get", flaky_get),
        ):
            self.assertIsNone(pricing.chat_prices("gpt-4o"), "the failed fetch is reported as unknown")
            self.assertEqual(pricing.chat_prices("gpt-4o"), ChatPrices(2.5e-6, 1e-5, 2.5e-6), "and retried")
            self.assertEqual(pricing.chat_prices("gpt-4o"), ChatPrices(2.5e-6, 1e-5, 2.5e-6))
            self.assertEqual(len(calls), 2, "a success is kept; a failure is not")

    def test_a_lone_or_malformed_env_price_is_an_error(self) -> None:
        for env in (
            {"CHAT_USD_PER_M_INPUT": "0.30"},
            {"CHAT_USD_PER_M_OUTPUT": "2.50"},
            {"CHAT_USD_PER_M_CACHED_INPUT": "0.03"},
            {"CHAT_USD_PER_M_INPUT": "0,30", "CHAT_USD_PER_M_OUTPUT": "2.50"},
        ):
            with patch.dict(os.environ, env, clear=True), self.assertRaises(ValueError):
                pricing.env_prices()

    def test_cost_of_an_episode(self) -> None:
        prices = ChatPrices(3e-7, 2.5e-6, 3e-8)
        self.assertEqual(cost_usd(1_000_000, 0, 0, 0, None), 0.042)
        self.assertEqual(cost_usd(0, 1_000_000, 100_000, 0, prices), 0.55)
        self.assertAlmostEqual(cost_usd(100_000, 10_000, 1_000, 0, prices), 0.0042 + 0.003 + 0.0025)
        self.assertAlmostEqual(
            cost_usd(0, 1_000_000, 0, 500_000, prices), 0.15 + 0.015, msg="cached input at the cache rate"
        )
        self.assertIsNone(cost_usd(0, 10, 10, 0, None), "chat tokens without a price are an unknown cost")
