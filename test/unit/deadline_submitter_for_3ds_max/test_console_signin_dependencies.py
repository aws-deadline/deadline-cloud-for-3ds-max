# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""Guards the dependency declarations that AWS Console sign-in depends on.

The integration tests cannot cover this: console sign-in needs an interactive browser
handshake and Deadline Cloud Monitor, while CI authenticates by assuming a role.

These read ``pyproject.toml`` rather than installed metadata, because
``importlib.metadata`` reflects install time and "somebody edited that line" is the
regression being guarded.

Scope matters as much as the versions: the ``console`` extra belongs in
``scripts/deps_bundle.py``, not in ``project.dependencies``, which would put awscrt into
the published wheel's metadata -- and no awscrt wheel satisfying botocore's crt pin
exists for ``macosx_10_9_x86_64``.
"""

import sys
from pathlib import Path

import pytest
from packaging.requirements import Requirement

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover - exercised on Python 3.9 and 3.10 only
    import tomli as tomllib

SCRIPTS_DIR = Path(__file__).parents[3] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    # Appended rather than prepended: scripts/ holds generically named modules (common.py),
    # and prepending would shadow any same-named import for the rest of the pytest session.
    sys.path.append(str(SCRIPTS_DIR))

import deps_bundle  # noqa: E402

PYPROJECT = Path(__file__).parents[3] / "pyproject.toml"

# 0.60.1 through 0.60.3 have no AWS_CONSOLE_LOGIN credentials source and declare no
# `console` extra; sign-in landed in 0.60.4.
HIGHEST_DEADLINE_WITHOUT_CONSOLE_SIGNIN = "0.60.3"


@pytest.fixture
def base_dependencies() -> list:
    node = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    assert "dependencies" in node.get("project", {}), "pyproject.toml has no project.dependencies"
    return [Requirement(r) for r in node["project"]["dependencies"]]


def _named(requirements: list, name: str) -> list:
    return [r for r in requirements if r.name == name]


def test_deadline_floor_excludes_releases_without_console_signin(base_dependencies):
    """Guards the floor itself, not whatever a resolver happened to select.

    An installed-version check cannot: with a loosened ">= 0.60.1" requirement pip still
    resolves the newest 0.60.x, so the regression passes unnoticed.
    """
    deadline_reqs = _named(base_dependencies, "deadline")
    assert deadline_reqs, "pyproject.toml declares no requirement on deadline"
    for req in deadline_reqs:
        assert not req.specifier.contains(HIGHEST_DEADLINE_WITHOUT_CONSOLE_SIGNIN), (
            f"allows deadline {HIGHEST_DEADLINE_WITHOUT_CONSOLE_SIGNIN}, which has no "
            f"console sign-in support: {req}"
        )


def test_base_dependencies_do_not_request_the_console_extra(base_dependencies):
    """Keeps awscrt out of the published wheel's dependency metadata.

    Declaring it here would force awscrt onto every consumer resolving this package, and no
    awscrt wheel satisfies botocore's crt pin for macosx_10_9_x86_64. The bundle requests
    the extra at build time instead (deps_bundle._add_console_extra).
    """
    for req in _named(base_dependencies, "deadline"):
        assert (
            "console" not in req.extras
        ), f"console extra leaks into the published dependency metadata via: {req}"

    # Copying the requirement in directly is the likelier mistake, and has the same effect.
    assert not _named(
        base_dependencies, "awscrt"
    ), "awscrt must not be a base dependency; it would leak into the published wheel metadata"


def test_deps_bundle_requests_the_console_extra(base_dependencies):
    """The submitter resolves through the deps bundle, so console is added there.

    Applies the bundler's own rewrite to the declared requirement, so a rename or a
    pre-existing extras list cannot silently bypass it.
    """
    deadline_reqs = _named(base_dependencies, "deadline")
    assert deadline_reqs, "pyproject.toml declares no requirement on deadline"
    for req in deadline_reqs:
        rewritten = Requirement(deps_bundle._add_console_extra(str(req)))
        assert "console" in rewritten.extras, f"bundler does not add the console extra to: {req}"
        assert rewritten.specifier == req.specifier, "rewrite must preserve the specifier"
