"""CLAUDE.md and AGENTS.md are one set of instructions kept as two files.

Claude Code reads CLAUDE.md and Codex reads AGENTS.md, so both exist; an edit to one that is not copied to
the other would give two agents two different rule books. Line endings are ignored, since a checkout may
convert them.
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def read(name):
    with open(os.path.join(ROOT, name), "rb") as f:
        return f.read().replace(b"\r\n", b"\n")


def test_agents_md_is_a_copy_of_claude_md():
    assert read("AGENTS.md") == read("CLAUDE.md"), \
        "AGENTS.md differs from CLAUDE.md: edit one, then copy it over the other"
