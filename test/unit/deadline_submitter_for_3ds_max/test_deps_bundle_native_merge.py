# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""Guards which compiled artifact the dependency bundle ships for each interpreter.

The bundle is one flat directory on ``PYTHONPATH``, so it holds a single file per name no
matter how many Python versions 3ds Max might embed. When two versions install the same
filename, the surviving copy is the only one any interpreter gets to load, and one built
for a newer Python fails to import on an older one.

The synthetic trees below reproduce the naming schemes, not the literal filenames: they use
POSIX-style names for readability, while the win_amd64 bundle actually ships an untagged
``_awscrt.pyd`` for abi3 and ``_awscrt.cp39-win_amd64.pyd`` for the version-specific wheels.
The merge is name-agnostic, so the scheme is what matters; the ``network``-marked tests pin
the scheme itself against the real wheels of every NATIVE_DEPENDENCIES entry, and are the
only ones here that leave the machine (deselected by default, run with
``hatch run test-network``). These tests assert which artifact is selected, not that it
loads -- that needs the target interpreter.
"""

import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import NamedTuple, NoReturn

import pytest

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

# awscrt's abi3 wheels all install this one name, whatever Python they were built for.
ABI3_ARTIFACT = "_awscrt.abi3.so"

# awscrt publishes version-specific (non-abi3) wheels below this and abi3 wheels from here up.
# Shapes the fixtures only; deps_bundle.py never reads it. test_lowest_abi3_python_matches_awscrt
# keeps it honest against the real wheel matrix.
LOWEST_ABI3_PYTHON = (3, 11)

# Resolved to tell an unreachable index apart from a missing awscrt wheel. Any pure-Python
# wheel works: py3-none-any is compatible with every tag, so it fails only on connectivity.
CONNECTIVITY_PROBE = "packaging"

# Set by the workflow jobs that gate the installer build on these tests, where a skip would
# pass the gate without verifying anything.
REQUIRE_NETWORK_TESTS_VAR = "DEADLINE_REQUIRE_NETWORK_TESTS"

PYPROJECT = Path(__file__).parents[3] / "pyproject.toml"


def _version_key(version: str) -> tuple:
    return tuple(int(part) for part in version.split("."))


def _tag(version: str) -> str:
    """The interpreter tag a wheel puts in a version-specific extension module name."""
    return version.replace(".", "")


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


@pytest.fixture
def supported_versions() -> list:
    versions = sorted(deps_bundle.SUPPORTED_PYTHON_VERSIONS, key=_version_key)
    abi3_versions = [v for v in versions if _version_key(v) >= LOWEST_ABI3_PYTHON]
    assert len(abi3_versions) >= 2, "a filename collision needs at least two abi3 versions"
    return versions


@pytest.fixture
def merged_bundle(tmp_path, supported_versions) -> Path:
    """Run the merge over trees that reproduce the real wheels' naming schemes.

    Each file's content records the version whose install produced it, so the merged tree
    reports where its contents came from. The base environment is seeded with the newest
    version, standing in for a build host newer than the interpreters the bundle serves.
    """
    base_env = tmp_path / "base_env"
    _write(base_env / ABI3_ARTIFACT, supported_versions[-1])

    native_paths = []
    for version in supported_versions:
        tree = tmp_path / "native" / _tag(version)
        native_paths.append(tree)
        if _version_key(version) < LOWEST_ABI3_PYTHON:
            _write(tree / f"_awscrt.cpython-{_tag(version)}-darwin.so", version)
        else:
            _write(tree / ABI3_ARTIFACT, version)
        _write(tree / "xxhash" / f"_xxhash.cpython-{_tag(version)}-darwin.so", version)
        _write(tree / "yaml" / f"_yaml.cpython-{_tag(version)}-darwin.so", version)
        _write(tree / "psutil" / "_psutil_osx.abi3.so", "shared")

    deps_bundle._copy_native_to_base_env(base_env, native_paths)
    return base_env


def test_colliding_abi3_artifact_comes_from_the_lowest_supported_abi(
    merged_bundle, supported_versions
):
    """abi3 is forward compatible only, so the lowest copy is the one that loads everywhere.

    A copy built for a newer Python fails to import on an older one; botocore then leaves its
    crypto binding unset and console sign-in reports sign-in needed indefinitely.
    """
    lowest_abi3_version = next(
        v for v in supported_versions if _version_key(v) >= LOWEST_ABI3_PYTHON
    )
    shipped = (merged_bundle / ABI3_ARTIFACT).read_text()

    assert shipped == lowest_abi3_version, (
        f"{ABI3_ARTIFACT} was built for Python {shipped}, so it cannot be imported by "
        f"Python {lowest_abi3_version}; the copy built for the lowest supported abi3 "
        f"version is the one every supported interpreter can load"
    )


def test_version_specific_artifacts_are_kept_for_every_supported_version(
    merged_bundle, supported_versions
):
    """Interpreter-tagged names do not collide, so every supported version keeps its own."""
    for version in supported_versions:
        for package, module in (("xxhash", "_xxhash"), ("yaml", "_yaml")):
            artifact = merged_bundle / package / f"{module}.cpython-{_tag(version)}-darwin.so"
            assert (
                artifact.exists()
            ), f"the bundle carries no {package} artifact for Python {version}"
            assert artifact.read_text() == version

    for version in supported_versions:
        if _version_key(version) >= LOWEST_ABI3_PYTHON:
            continue
        awscrt_non_abi3 = merged_bundle / f"_awscrt.cpython-{_tag(version)}-darwin.so"
        assert (
            awscrt_non_abi3.exists()
        ), f"the bundle carries no awscrt artifact for Python {version}"


def test_native_trees_are_merged_lowest_python_version_first(tmp_path, monkeypatch):
    """Download order picks the collision winner, so it must sort numerically.

    Sorted as text, "3.9" lands after "3.10". The versions here are chosen to expose that,
    not to describe what is supported.
    """
    monkeypatch.setattr(deps_bundle, "SUPPORTED_PYTHON_VERSIONS", ["3.13", "3.9", "3.11", "3.10"])
    monkeypatch.setattr(deps_bundle, "_get_package_version", lambda package, install_path: "1.2.3")

    requested_versions: list = []

    def record(args, **kwargs):
        requested_versions.append(args[args.index("--python-version") + 1])
        return subprocess.CompletedProcess(args, 0)

    monkeypatch.setattr(deps_bundle.subprocess, "run", record)

    tree_paths = deps_bundle._download_native_dependencies(tmp_path, tmp_path / "base_env")

    assert requested_versions == ["3.9", "3.10", "3.11", "3.13"]
    assert [path.name for path in tree_paths] == ["3_9", "3_10", "3_11", "3_13"]


def test_get_package_version_matches_pip_list_casing(monkeypatch):
    """NATIVE_DEPENDENCIES spells `pyyaml`, but `pip list` reports it as `PyYAML`.

    A case-sensitive match would fail the per-version downloads for an installed package.
    """
    output = b"Package  Version\n-------- -------\nPyYAML   6.0.3\nxxhash   3.6.0\n"
    monkeypatch.setattr(
        deps_bundle.subprocess,
        "run",
        lambda args, **kwargs: subprocess.CompletedProcess(args, 0, stdout=output),
    )

    assert deps_bundle._get_package_version("pyyaml", Path("/unused")) == "6.0.3"


class _Wheel(NamedTuple):
    """A downloaded wheel's ABI tag and the extension modules it installs.

    The ABI tag is what decides whether a shared filename is safe to collapse, and an
    untagged member name does not imply it: a version-specific wheel could ship one too,
    and collapsing that would hand the lowest version's binary to every later interpreter.
    Only the wheel's own tag distinguishes them.
    """

    abi_tag: str
    members: list


def _inspect_wheel(wheel: Path) -> _Wheel:
    # awscrt-0.36.0-cp311-abi3-win_amd64.whl -> abi3; awscrt-0.36.0-cp39-cp39-win_amd64.whl -> cp39
    abi_tag = wheel.stem.split("-")[-2]
    with zipfile.ZipFile(wheel) as archive:
        members = [
            name.rsplit("/", 1)[-1]
            for name in archive.namelist()
            if name.endswith((".pyd", ".so", ".dll"))
        ]
    return _Wheel(abi_tag=abi_tag, members=members)


def _unavailable(reason: str) -> NoReturn:
    """Skip, or fail when the caller has declared the checks mandatory.

    The release and installer builds gate on these tests, and pytest exits 0 when every
    selected test skips, so an index blip there would pass the gate without verifying
    anything. Those jobs set REQUIRE_NETWORK_TESTS_VAR to make that outcome a failure,
    while a developer running them locally still gets a skip.
    """
    if os.environ.get(REQUIRE_NETWORK_TESTS_VAR):
        pytest.fail(f"{reason} (required because {REQUIRE_NETWORK_TESTS_VAR} is set)")
    pytest.skip(reason)


def _declared_dependencies() -> list:
    """The requirements `_build_base_environment` installs, rewritten the way it rewrites them."""
    project = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    return [deps_bundle._add_console_extra(dep) for dep in deps_bundle._get_dependencies(project)]


def _base_env_resolution(platform: str, working_directory: Path) -> dict:
    """``{package: version}`` for a real resolution of what the base environment installs.

    Resolving rather than reading installed metadata matters because this environment is not
    the base environment: it also holds requirements-testing.txt, which can constrain a
    native package to a version the bundle would not pick.

    ``--python-version`` is deliberately absent. pip does not evaluate ``python_version``
    markers against it, so pinning one makes deadline's conditional click requirement
    unsatisfiable; the base environment likewise resolves once under the build host's
    interpreter, so omitting it is also the faithful comparison.
    """
    report = working_directory / "resolution.json"
    working_directory.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--dry-run",
                "--report",
                str(report),
                "--target",
                str(working_directory / "target"),
                "--only-binary=:all:",
                "--platform",
                platform,
                *_declared_dependencies(),
            ],
            check=True,
            capture_output=True,
        )
    except (subprocess.CalledProcessError, OSError) as error:
        _unavailable(f"cannot resolve what the base environment installs for {platform}: {error}")
    resolved = json.loads(report.read_text(encoding="utf-8"))
    return {
        entry["metadata"]["name"].lower(): entry["metadata"]["version"]
        for entry in resolved["install"]
    }


def _pip_download(package: str, version: str, platform: str, target: Path):
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "download",
            package,
            "--no-deps",
            "--only-binary=:all:",
            "--python-version",
            version,
            "--platform",
            platform,
            "--dest",
            str(target),
        ],
        check=True,
        capture_output=True,
    )


def _download_wheels(package: str, pinned_version: str, platform: str, root: Path) -> dict:
    """``{python version: _Wheel}`` for one package, at the version the bundle resolves.

    A download failure is only allowed to skip when the index is unreachable, which is
    established by resolving a pure-Python wheel for the same tags -- it is compatible with
    every tag, so it fails only on connectivity. If that succeeds while the package does
    not, the package has stopped publishing a wheel for a version SUPPORTED_PYTHON_VERSIONS
    still lists, which would break the bundle, so it fails rather than skipping.
    """
    wheels = {}
    for version in sorted(deps_bundle.SUPPORTED_PYTHON_VERSIONS, key=_version_key):
        target = root / package / _tag(version)
        try:
            _pip_download(f"{package}=={pinned_version}", version, platform, target)
        except OSError as error:
            _unavailable(f"cannot run pip: {error}")
        except subprocess.CalledProcessError as download_error:
            try:
                _pip_download(CONNECTIVITY_PROBE, version, platform, target / "probe")
            except (subprocess.CalledProcessError, OSError):
                _unavailable(f"cannot reach the package index: {download_error}")
            raise AssertionError(
                f"{package} {pinned_version} publishes no {platform} wheel for Python "
                f"{version}, which SUPPORTED_PYTHON_VERSIONS still lists; the bundle "
                f"would carry no loadable {package} there"
            ) from download_error
        found = list(target.glob("*.whl"))
        assert len(found) == 1, f"expected one {package} wheel for Python {version}, got {found}"
        wheels[version] = _inspect_wheel(found[0])
    return wheels


@pytest.fixture(scope="module")
def wheels_for(tmp_path_factory):
    """Returns ``package -> {python version: _Wheel}``, resolved as the base environment would.

    A callable rather than a mapping so an unresolvable package only affects its own
    parametrization: building all four eagerly would let one of them skip the checks for the
    other three. Results are cached, so the shared resolution runs once per module.
    """
    platform = deps_bundle.SUPPORTED_PLATFORMS[0]
    download_root = tmp_path_factory.mktemp("native_wheels")
    resolution: dict = {}
    cache: dict = {}

    def load(package: str) -> dict:
        if package not in cache:
            if not resolution:
                resolution.update(_base_env_resolution(platform, download_root / "resolve"))
            pinned_version = resolution.get(package.lower())
            if pinned_version is None:
                _unavailable(
                    f"{package} is in NATIVE_DEPENDENCIES but the base environment's "
                    f"resolution for {platform} does not install it"
                )
            cache[package] = _download_wheels(package, pinned_version, platform, download_root)
        return cache[package]

    return load


@pytest.mark.network
@pytest.mark.parametrize("package", deps_bundle.NATIVE_DEPENDENCIES)
def test_real_wheels_collide_only_on_abi3_names(wheels_for, package):
    """Pins the naming premise the merge rests on to the wheels actually resolved.

    Ascending-first-wins is only safe while every name installed by more than one version
    comes from an abi3 wheel. A version-specific wheel sharing a name would hand the lowest
    version's binary to every later interpreter, and that is invisible in the member name --
    an untagged name proves nothing on Windows -- so discriminate on the wheel's ABI tag.

    psutil is why this covers every package rather than awscrt alone: it installs an
    untagged ``_psutil_windows.pyd``, safe only while it ships one abi3 wheel for all of
    them.
    """
    abi_tags_by_artifact: dict = {}
    for version, wheel in wheels_for(package).items():
        for artifact in wheel.members:
            abi_tags_by_artifact.setdefault(artifact, {})[version] = wheel.abi_tag

    for artifact, abi_tag_by_version in abi_tags_by_artifact.items():
        if len(abi_tag_by_version) == 1:
            continue
        non_abi3 = sorted(
            version for version, abi_tag in abi_tag_by_version.items() if abi_tag != "abi3"
        )
        assert not non_abi3, (
            f"{package}'s {artifact} is installed by Python {sorted(abi_tag_by_version)} but "
            f"Python {non_abi3} gets it from a version-specific wheel, so only that copy "
            f"would ship and the later interpreters could not import it"
        )


@pytest.mark.network
def test_lowest_abi3_python_matches_awscrt(wheels_for):
    """Keeps the fixtures' abi3 floor honest against awscrt's real wheel matrix."""
    awscrt_wheels_by_version = wheels_for("awscrt")
    abi3_versions = {
        version for version, wheel in awscrt_wheels_by_version.items() if wheel.abi_tag == "abi3"
    }
    assert abi3_versions, "awscrt published no abi3 win_amd64 wheel for any version"

    lowest_abi3 = min(abi3_versions, key=_version_key)
    assert _version_key(lowest_abi3) == LOWEST_ABI3_PYTHON, (
        f"awscrt now publishes abi3 wheels from Python {lowest_abi3}, not "
        f"{'.'.join(str(part) for part in LOWEST_ABI3_PYTHON)}; update LOWEST_ABI3_PYTHON"
    )
