# coding: utf-8
"""Environment-driven configuration: env loading and aliases, the chat model, the browser launch flags."""

from __future__ import annotations

import os
from unittest import TestCase
from unittest.mock import patch

from s1a import config


class TestLoadEnv(TestCase):
    def test_openrouter_stands_in_for_the_chat_model_without_overriding(self) -> None:
        env = {"OPENROUTER_API_KEY": "r", "OPENROUTER_BASE_URL": "https://or.test/v1"}
        with patch.dict(os.environ, env, clear=True):
            with (
                patch.object(config, "load_dotenv", lambda *a, **k: False),
                patch.object(config, "load_repo_dotenv", lambda: False),
            ):
                config.load_env()
            self.assertEqual((os.environ["LLM_API_KEY"], os.environ["LLM_BASE_URL"]), ("r", "https://or.test/v1"))

    def test_the_jev_keys_are_stripped_before_the_aliases_read_them(self) -> None:
        env = {"TYPESAFE_API_KEY": " ", "OPENROUTER_API_KEY": " r ", "TYPESAFE_API_URL": " https://d.test "}
        with patch.dict(os.environ, env, clear=True):
            with (
                patch.object(config, "load_dotenv", lambda *a, **k: False),
                patch.object(config, "load_repo_dotenv", lambda: False),
            ):
                config.load_env()
            self.assertEqual(
                (os.environ["TYPESAFE_API_KEY"], os.environ["OPENROUTER_API_KEY"], os.environ["LLM_API_KEY"]),
                ("", "r", "r"),
            )
            self.assertEqual(os.environ["TYPESAFE_API_URL"], "https://d.test")


class TestChatModel(TestCase):
    def test_chat_model_needs_a_key_and_a_model_name(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError):
                config.chat_model_from_env()
        with patch.dict(os.environ, {"LLM_API_KEY": "k"}, clear=True):
            with self.assertRaises(RuntimeError):
                config.chat_model_from_env()
            self.assertIsNone(config.optional_chat_model())

    def test_an_org_level_anthropic_key_names_its_workspace_in_a_header(self) -> None:
        env = {
            "OPENAI_API_KEY": "k",
            "OPENAI_BASE_URL": "https://api.anthropic.com",
            "MODEL_PROVIDER": "anthropic",
            "MODEL_NAME": "claude-fable-5-1",
            "ANTHROPIC_WORKSPACE_ID": "wrkspc_1",
        }
        with patch.dict(os.environ, env, clear=True):
            client_config = config.chat_model_from_env().model_client_config
        self.assertEqual(client_config.client_provider, "Anthropic")  # openjiuwen normalises the provider name
        self.assertEqual(client_config.custom_headers["anthropic-workspace-id"], "wrkspc_1")

    def test_claude_may_drop_thinking_blocks_whose_prefix_the_harness_rewrote(self) -> None:
        env = {"OPENAI_API_KEY": "k", "MODEL_PROVIDER": "anthropic", "MODEL_NAME": "claude-fable-5-1"}
        with patch.dict(os.environ, env, clear=True):
            model = config.chat_model_from_env()
        self.assertEqual(
            model.model_client_config.custom_headers, {"anthropic-beta": "thinking-binding-controls-2026-08-01"}
        )
        self.assertEqual(
            model.model_config.extra_body["thinking"]["block_binding"], {"prefix_mismatch_behavior": "drop_block"}
        )
        with patch.dict(os.environ, {"LLM_API_KEY": "k", "MODEL_NAME": "m"}, clear=True):
            openai_model = config.chat_model_from_env()
        self.assertIsNone(openai_model.model_client_config.custom_headers)
        self.assertNotIn("extra_body", openai_model.model_config.model_fields_set)


class TestLaunchArgs(TestCase):
    def test_launch_args_isolate_the_profile_and_follow_headless(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            headless = config.browser_launch_args(True)
            headed = config.browser_launch_args(False)
        self.assertIn("--isolated", headless)
        self.assertIn("--headless", headless)
        self.assertNotIn("--headless", headed)
        with patch.dict(os.environ, {"PLAYWRIGHT_MCP_ARGS": "-y @playwright/mcp@0.0.78 --cdp-endpoint x"}, clear=True):
            self.assertEqual(config.browser_launch_args(True), "-y @playwright/mcp@0.0.78 --cdp-endpoint x")

    def test_a_configured_server_still_gets_the_profile_and_headless_flags_once(self) -> None:
        with patch.dict(os.environ, {"PLAYWRIGHT_MCP_ARGS": "/x/cli.js"}, clear=True):
            self.assertEqual(config.browser_launch_args(True), "/x/cli.js --isolated --headless")
        with patch.dict(os.environ, {"PLAYWRIGHT_MCP_ARGS": "/x/cli.js --isolated --headless"}, clear=True):
            self.assertEqual(config.browser_launch_args(False), "/x/cli.js --isolated")
