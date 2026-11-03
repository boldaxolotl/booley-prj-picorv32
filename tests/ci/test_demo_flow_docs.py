"""START-HERE.md (Codespace) and README.md (local install) set Booley up
differently, but the demo itself is the same: run Flows one at a time, run
the prepared Zbb Goal, then experiment. Both files carry that part as marked
blocks; this test keeps the copies identical so they cannot drift apart.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BLOCK = re.compile(r"<!-- demo-flow:([a-z-]+) .*?-->\n(.*?)<!-- /demo-flow -->", re.S)
EXPECTED = ["run-things", "goal-mode", "experiment"]


def _blocks(name: str) -> dict[str, str]:
    text = (REPO_ROOT / name).read_text(encoding="utf-8")
    found = BLOCK.findall(text)
    assert [key for key, _ in found] == EXPECTED, f"{name}: demo-flow blocks out of order or missing"
    return dict(found)


def test_demo_flow_is_identical_in_start_here_and_readme() -> None:
    start_here, readme = _blocks("START-HERE.md"), _blocks("README.md")
    for key in EXPECTED:
        assert start_here[key] == readme[key], f"demo-flow:{key} differs; copy START-HERE.md's block into README.md"


def test_shared_blocks_link_nowhere_file_local() -> None:
    # A relative link or bare anchor resolves differently in each file.
    for key, body in _blocks("START-HERE.md").items():
        assert not re.search(r"\]\((#|[A-Za-z0-9_.-]+\.md)", body), f"demo-flow:{key} has a file-relative link"
