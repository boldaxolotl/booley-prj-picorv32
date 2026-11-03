"""Checks on the Project's Goalsets in goalsets/.

The static checks need only the standard library and run in the unit job.
With Booley importable (inside the demo container, see codespaces-smoke/smoke.sh)
the Goal arguments also go through Booley's own parser and Criteria
translation, the same validation Goal Mode entry applies. Set
GOALSET_CHECK_REQUIRE_BOOLEY=1 to fail instead of skip when Booley is missing.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
GOALSETS = REPO_ROOT / "goalsets"
GOALSET_NAMES = sorted(path.stem for path in GOALSETS.glob("*.md"))

_JSON_BLOCK = re.compile(r"```json\n(.*?)\n```", re.DOTALL)
_FAMILIES = {"LINT", "SIM", "ELAB", "SYNTH", "FPGA", "CYCLE_COUNT", "COVERAGE", "MUTATION", "REVIEW"}

# Targets a Goalset's change creates; every other named Target must exist now.
GOAL_CREATED_TARGETS = {"zbb": {"sim_zbb_disabled"}}

# Values the agent substitutes for the generic Goalsets' placeholders.
_PLACEHOLDERS = {"<rtl-file>": "picorv32.v", "<tb-file>": "testbench.v"}
_SAMPLE_TARGETS = ["sim_core", "lint_core"]

# The reviewer inlines at most this many spec characters (Booley's
# specialists/reviewer.py _SPEC_MAX_SIZE); a longer spec is silently cut.
_SPEC_MAX_CHARS = 30_000

# The fixed Goals of the demo's headline Zbb change (issue #2531).
ZBB_EXPECTED = [
    {"family": "LINT", "target": "lint_core", "origin": "zbb"},
    {"family": "SIM", "target": "sim_core", "origin": "zbb"},
    {"family": "SIM", "target": "sim_wb", "origin": "zbb"},
    {"family": "SIM", "target": "sim_zbb_disabled", "origin": "zbb"},
    {"family": "REVIEW", "review": "rtl_bugs", "verdict": "clean", "paths": ["picorv32.v"], "origin": "zbb"},
    {
        "family": "REVIEW",
        "review": "tb_quality",
        "verdict": "clean",
        "paths": ["testbench.v", "testbench_wb.v", "testbench_zbb_disabled.v"],
        "origin": "zbb",
    },
    {
        "family": "REVIEW",
        "review": "rtl_spec",
        "verdict": "clean",
        "spec": ".booley/specs/zbb.md",
        "paths": ["picorv32.v"],
        "origin": "zbb",
    },
    {
        "family": "SYNTH",
        "target": "synth_core",
        "thresholds": {"cell_count_increase_at_most": "11%", "critical_path_ps_increase_at_most": "3%"},
        "origin": "zbb",
    },
]


def goal_arguments(name: str) -> list[dict[str, Any]]:
    """The raw Goal arguments of one Goalset: its single JSON block."""
    blocks = _JSON_BLOCK.findall((GOALSETS / f"{name}.md").read_text(encoding="utf-8"))
    assert len(blocks) == 1, f"{name}: a Goalset carries exactly one Goal argument block"
    goals = json.loads(blocks[0])
    assert isinstance(goals, list) and goals, f"{name}: the Goal argument block is an empty or non-list value"
    return goals


def expanded_goal_arguments(name: str) -> list[dict[str, Any]]:
    """Goal arguments with placeholders replaced, as the agent would."""
    expanded: list[dict[str, Any]] = []
    for goal in goal_arguments(name):
        if "paths" in goal:
            goal = {**goal, "paths": [_PLACEHOLDERS.get(path, path) for path in goal["paths"]]}
        if goal.get("target") == "<target>":
            expanded.extend({**goal, "target": target} for target in _SAMPLE_TARGETS)
        else:
            expanded.append(goal)
    return expanded


def defined_targets() -> set[str]:
    """Target names declared under `targets:` in the Project's .core files."""
    names: set[str] = set()
    for core in (REPO_ROOT / "cores").glob("*.core"):
        in_targets = False
        for line in core.read_text(encoding="utf-8").splitlines():
            if re.match(r"^\S", line):  # a top-level key starts or ends the section
                in_targets = line.rstrip() == "targets:"
            elif in_targets and (match := re.match(r"^  ([A-Za-z_][\w-]*):", line)):
                names.add(match.group(1))
    return names


def named_targets(goals: list[dict[str, Any]]) -> set[str]:
    return {goal[key] for goal in goals for key in ("target", "baseline") if key in goal}


@pytest.mark.parametrize("name", GOALSET_NAMES)
def test_goalset_families_are_known(name: str) -> None:
    families = {goal.get("family") for goal in goal_arguments(name)}
    assert families <= _FAMILIES, f"{name}: unknown families {sorted(map(str, families - _FAMILIES))}"


@pytest.mark.parametrize("name", GOALSET_NAMES)
def test_goalset_names_only_existing_or_created_targets(name: str) -> None:
    allowed = defined_targets() | GOAL_CREATED_TARGETS.get(name, set()) | {"<target>"}
    unknown = named_targets(goal_arguments(name)) - allowed
    assert not unknown, f"{name}: names Targets the Project does not define: {sorted(unknown)}"


def test_goal_created_targets_do_not_exist_yet() -> None:
    # A created Target that already exists means main carries the change.
    for name, created in GOAL_CREATED_TARGETS.items():
        assert not created & defined_targets(), f"{name}: main already defines {sorted(created)}"


def test_zbb_goalset_has_exactly_the_headline_goals() -> None:
    assert goal_arguments("zbb") == ZBB_EXPECTED


def test_zbb_spec_is_committed_and_fits_the_reviewer() -> None:
    # Goal paths are relative to the Goal worktree, where this repo is `.booley`.
    for goal in goal_arguments("zbb"):
        if "spec" not in goal:
            continue
        relative = Path(goal["spec"]).relative_to(".booley")
        spec = REPO_ROOT / relative
        assert spec.is_file() and not spec.is_symlink(), f"{goal['spec']} must be a regular committed file"
        assert len(spec.read_text(encoding="utf-8")) < _SPEC_MAX_CHARS


def test_zbb_prompts_name_the_committed_design() -> None:
    # The Goalset holds only Goals; the visitor's prompt points the agent at the design.
    design = REPO_ROOT / "specs" / "zbb-design.md"
    assert design.is_file() and not design.is_symlink()
    assert "## The change" in design.read_text(encoding="utf-8")
    assert "## The change" not in (GOALSETS / "zbb.md").read_text(encoding="utf-8")
    for doc in ("START-HERE.md", "README.md"):
        prose = " ".join((REPO_ROOT / doc).read_text(encoding="utf-8").replace(">", " ").split())
        assert "the design described in .booley/specs/zbb-design.md" in prose, doc


def test_main_carries_no_zbb_implementation() -> None:
    # The visitor's agent builds Zbb; this repo ships only the Goal and its spec.
    hits = [
        path.relative_to(REPO_ROOT).as_posix()
        for top in ("cores", "hooks", "selftest")
        for path in (REPO_ROOT / top).rglob("*")
        if path.is_file() and re.search(r"zbb", path.read_text(encoding="utf-8", errors="ignore"), re.IGNORECASE)
    ]
    hits += ["tests.toml"] if "zbb" in (REPO_ROOT / "tests.toml").read_text(encoding="utf-8").lower() else []
    assert not hits, f"Zbb implementation found on main: {hits}"


# ---------------------------------------------------------------------------
# Booley-backed validation
# ---------------------------------------------------------------------------


def _booley_goal_api() -> tuple[Any, Any]:
    required = os.environ.get("GOALSET_CHECK_REQUIRE_BOOLEY") == "1"
    try:
        from booley.goals.model import ReviewGoalArg, parse_goal_args
        from booley.goals.translate import translate_goals
    except ImportError:
        if required:
            raise
        pytest.skip("Booley is not importable here; the Codespaces smoke runs this check")
    # Scoped Review Goals (`paths`) postdate the published 0.3.0 package; this
    # Project needs a later build, like the one in the pinned Sandbox image.
    if "paths" not in ReviewGoalArg.__dataclass_fields__:
        if required:
            pytest.fail("this Booley predates scoped Review Goals; the Goalsets need a newer one")
        pytest.skip("the importable Booley predates scoped Review Goals; the Codespaces smoke runs this check")
    return parse_goal_args, translate_goals


@pytest.mark.parametrize("name", GOALSET_NAMES)
def test_goalset_parses_and_translates_with_booley(name: str) -> None:
    parse_goal_args, translate_goals = _booley_goal_api()
    goals = parse_goal_args(expanded_goal_arguments(name), where=name)
    translate_goals(goals)


def test_zbb_goals_pass_booley_entry_checks() -> None:
    """Goal Mode entry accepts the zbb Goals in a real Project checkout.

    Entry refuses a missing spec file or synthesis baseline Target and only
    warns about what the change creates. Needs the upstream checkout with this
    repo as its `.booley`; smoke.sh sets PICORV32_ROOT.
    """
    root = os.environ.get("PICORV32_ROOT")
    if not root:
        if os.environ.get("GOALSET_CHECK_REQUIRE_BOOLEY") == "1":
            pytest.fail("GOALSET_CHECK_REQUIRE_BOOLEY=1 needs PICORV32_ROOT, the upstream checkout")
        pytest.skip("PICORV32_ROOT is not set; the Codespaces smoke runs this check")
    parse_goal_args, translate_goals = _booley_goal_api()
    from booley.goals.entry import check_goal_targets

    translation = translate_goals(parse_goal_args(goal_arguments("zbb"), where="zbb"))
    warnings = check_goal_targets(Path(root), translation.goals)
    created = ("sim_zbb_disabled", "testbench_zbb_disabled.v")
    unexpected = [warning for warning in warnings if not any(name in warning for name in created)]
    assert not unexpected, unexpected
