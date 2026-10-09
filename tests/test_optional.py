# coding: utf-8
"""An agent whose extra is missing: one line naming the package and the extra, from load, the CLI and the MCP listing."""

from __future__ import annotations

import asyncio
import contextlib
import io
import os
import sys
from unittest import TestCase
from unittest.mock import patch

from s1a import cli, mcp_server
from s1a import run as agents

MESSAGE = "agent 'blackjack' needs the rlcard package: uv sync --extra blackjack"


@contextlib.contextmanager
def without_rlcard():
    """``import rlcard`` raises ModuleNotFoundError inside; the blackjack module is re-imported on the way in and out."""
    with patch.dict(sys.modules, {"rlcard": None}):
        sys.modules.pop("s1a.agents.blackjack", None)
        yield


class TestMissingPackage(TestCase):
    def test_load_names_the_package_and_the_extra(self) -> None:
        with without_rlcard(), self.assertRaises(agents.MissingPackage) as caught:
            agents.load("blackjack")
        self.assertEqual(str(caught.exception), MESSAGE)

    def test_the_cli_prints_the_line_on_stderr_and_exits_1(self) -> None:
        out, err = io.StringIO(), io.StringIO()
        with without_rlcard(), patch.dict(os.environ), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cli.main(["run", "blackjack", "--help"])
        self.assertEqual((code, out.getvalue(), err.getvalue()), (1, "", MESSAGE + "\n"))

    def test_the_mcp_listing_keeps_the_agent_with_the_line_as_its_description(self) -> None:
        with without_rlcard():
            rows = {row["name"]: row for row in asyncio.run(mcp_server.list_agents())}
        self.assertEqual(rows["blackjack"], {"name": "blackjack", "front": "unavailable", "description": MESSAGE})
        self.assertEqual(rows["flights"]["front"], "browser")
