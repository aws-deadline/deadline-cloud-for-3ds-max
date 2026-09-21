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
the scheme itself against the real wheels, and are the only ones here that leave the
machine (``-m 'not network'`` deselects them). These tests assert which artifact is
selected, not that it loads -- that needs the target interpreter.
"""

import importlib.metadata
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import NamedTuple, Optional

import pytest
from packaging.requirements import Requirement

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


def _bundled_awscrt_version() -> Optional[str]:
    """The awscrt the bundle ships: whatever botocore's `crt` extra pins, or None.

    ``_download_native_dependencies`` pins awscrt to the version resolved into the base
    environment, which gets it transitively from ``deadline[console]`` -> ``botocore[crt]``.
    Reading that pin out of the installed botocore's metadata tracks the same chain, so
    these tests follow a botocore bump instead of validating whatever awscrt is newest.
    """
    for requirement in importlib.metadata.requires("botocore") or []:
        parsed = Requirement(requirement)
        if parsed.name == "awscrt":
            pinned = [spec.version for spec in parsed.specifier if spec.operator in ("==", "===")]
            if pinned:
                return pinned[0]
    return None


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


@pytest.fixture(scope="module")
def awscrt_wheels_by_version(tmp_path_factory) -> dict:
    """The real win_amd64 awscrt wheel for each supported version, with its ABI tag.

    Downloads rather than asserting a filename list, so a change to awscrt's wheel matrix
    surfaces here instead of in a silently unloadable bundle.

    A download failure is only allowed to skip when the index is unreachable, which is
    established by resolving a pure-Python wheel for the same tags -- it is compatible with
    every tag, so it fails only on connectivity. If that succeeds while awscrt does not,
    awscrt has stopped publishing a wheel for a version SUPPORTED_PYTHON_VERSIONS still
    lists, which would break the bundle, so it fails rather than skipping.
    """
    platform = deps_bundle.SUPPORTED_PLATFORMS[0]
    awscrt_version = _bundled_awscrt_version()
    if awscrt_version is None:
        pytest.skip("installed botocore declares no pinned awscrt in its crt extra")
    download_root = tmp_path_factory.mktemp("awscrt_wheels")
    artifacts = {}
    for version in sorted(deps_bundle.SUPPORTED_PYTHON_VERSIONS, key=_version_key):
        target = download_root / _tag(version)
        try:
            _pip_download(f"awscrt=={awscrt_version}", version, platform, target)
        except OSError as error:
            pytest.skip(f"cannot run pip: {error}")
        except subprocess.CalledProcessError as awscrt_error:
            try:
                _pip_download(CONNECTIVITY_PROBE, version, platform, target / "probe")
            except (subprocess.CalledProcessError, OSError):
                pytest.skip(f"cannot reach the package index: {awscrt_error}")
            raise AssertionError(
                f"awscrt {awscrt_version} publishes no {platform} wheel for Python "
                f"{version}, which SUPPORTED_PYTHON_VERSIONS still lists; the bundle "
                f"would carry no loadable awscrt there"
            ) from awscrt_error
        wheels = list(target.glob("*.whl"))
        assert len(wheels) == 1, f"expected one awscrt wheel for Python {version}, got {wheels}"
        artifacts[version] = _inspect_wheel(wheels[0])
    return artifacts


@pytest.mark.network
def test_real_awscrt_wheels_collide_only_on_abi3_names(awscrt_wheels_by_version):
    """Pins the naming premise the merge rests on to the wheels actually resolved.

    Ascending-first-wins is only safe while every name installed by more than one version
    comes from an abi3 wheel. A version-specific wheel sharing a name would hand the lowest
    version's binary to every later interpreter, and that is invisible in the member name --
    an untagged name proves nothing on Windows -- so discriminate on the wheel's ABI tag.
    """
    abi_tags_by_artifact: dict = {}
    for version, wheel in awscrt_wheels_by_version.items():
        for artifact in wheel.members:
            abi_tags_by_artifact.setdefault(artifact, {})[version] = wheel.abi_tag

    for artifact, abi_tag_by_version in abi_tags_by_artifact.items():
        if len(abi_tag_by_version) == 1:
            continue
        non_abi3 = sorted(
            version for version, abi_tag in abi_tag_by_version.items() if abi_tag != "abi3"
        )
        assert not non_abi3, (
            f"{artifact} is installed by Python {sorted(abi_tag_by_version)} but Python "
            f"{non_abi3} gets it from a version-specific wheel, so only that copy would "
            f"ship and the later interpreters could not import it"
        )


@pytest.mark.network
def test_lowest_abi3_python_matches_awscrt(awscrt_wheels_by_version):
    """Keeps the fixtures' abi3 floor honest against awscrt's real wheel matrix."""
    abi3_versions = {
        version for version, wheel in awscrt_wheels_by_version.items() if wheel.abi_tag == "abi3"
    }
    assert abi3_versions, "awscrt published no abi3 win_amd64 wheel for any version"

    lowest_abi3 = min(abi3_versions, key=_version_key)
    assert _version_key(lowest_abi3) == LOWEST_ABI3_PYTHON, (
        f"awscrt now publishes abi3 wheels from Python {lowest_abi3}, not "
        f"{'.'.join(str(part) for part in LOWEST_ABI3_PYTHON)}; update LOWEST_ABI3_PYTHON"
    )
