# coding: utf-8
"""The Blackjack adapter's observation: the dealer's hole card stays hidden until the hand is over."""

from __future__ import annotations

from unittest import IsolatedAsyncioTestCase, skipUnless

try:
    from s1a.agents.blackjack import BlackjackEnv, hand_total

    HAVE_RLCARD = True
except ModuleNotFoundError:  # the blackjack extra is not installed
    HAVE_RLCARD = False


@skipUnless(HAVE_RLCARD, "the blackjack extra (rlcard) is not installed")
class TestDealerReveal(IsolatedAsyncioTestCase):
    async def test_dealer_cards_appear_only_once_the_hand_is_over(self) -> None:
        env = BlackjackEnv(seed=3)
        await env.reset()
        before = await env.observe()
        self.assertNotIn("dealer_cards", before)
        self.assertEqual(len(before["dealer_showing"]), 1)
        while not env.done:
            await env.step("stand")
        after = await env.observe()
        self.assertGreaterEqual(len(after["dealer_cards"]), 2)
        self.assertIn(before["dealer_showing"][0], after["dealer_cards"])
        self.assertEqual(after["dealer_showing"], before["dealer_showing"])

    def test_hand_total_counts_a_soft_ace_once_it_would_bust(self) -> None:
        self.assertEqual(hand_total(["SA", "H7"]), (18, True))
        self.assertEqual(hand_total(["SA", "H7", "D9"]), (17, False))
