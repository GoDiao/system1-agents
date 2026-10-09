# coding: utf-8
"""The Millionaire page's answer order: a function of the question text, the same for the same text."""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from unittest import TestCase, skipUnless

from s1a.agents.millionaire import PAGE_DIR

HARNESS = r"""
const fs = require("fs");
const src = fs.readFileSync(process.argv[2], "utf8");
const fn = (name) => { const m = src.match(new RegExp(`^function ${name}\\(.*$`, "m")); if (!m) throw new Error(`no function ${name}`); return m[0]; };
const seed = src.match(/shuffle\(\[q\.correct, \.\.\.q\.incorrect\], (.+?)\);/)[1];
const keyOf = new Function("S", "level", "q", `${fn("shuffle")}\n${fn("hash")}\nreturn shuffle([q.correct, ...q.incorrect], ${seed}).indexOf(q.correct) + 1;`);
const q = (question) => ({ question, correct: "yes", incorrect: ["a", "b", "c"] });
const keys = (question) => Array.from({ length: 15 }, (_, level) => keyOf({ ladder: 0 }, level, q(question)));
console.log(JSON.stringify({ a: keys("Which?"), again: keys("Which?"), b: keys("What?") }));
"""


@skipUnless(shutil.which("node"), "node is not installed")
class TestAnswerOrder(TestCase):
    def test_the_correct_key_sequence_follows_the_question_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            harness = Path(tmp) / "harness.js"
            harness.write_text(HARNESS, encoding="utf-8")
            out = subprocess.run(
                ["node", str(harness), str(PAGE_DIR / "index.html")], capture_output=True, text=True, check=True
            )
        keys = json.loads(out.stdout)
        self.assertEqual(keys["a"], keys["again"], "the same questions file gives the same layout")
        self.assertNotEqual(keys["a"], keys["b"], "another question at the same ladder and level moves the answer")
