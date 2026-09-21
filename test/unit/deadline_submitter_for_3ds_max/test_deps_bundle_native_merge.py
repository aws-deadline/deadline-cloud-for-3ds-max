# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""Guards which compiled artifact the dependency bundle ships for each interpreter.

The bundle is one flat directory on ``PYTHONPATH``, so it holds a single file per name no
matter how many Python versions 3ds Max might embed. When two versions install the same
filename, the surviving copy is the only one any interpreter gets to load, and one built
for a newer Python fails to import on an older one.

The synthetic trees below reproduce the naming schemes, not the literal filenames: they use
POSIX-style names for readability, while the win_amd64 bundle actually ships an untagged
``_awscrt.pyd`` for abi3 and ``_awscrt.cp39-win_amd64.pyd`` for the version-specific wheels.
The merge is name-agnostic, so the scheme is what matters; the tests that download real
wheels pin the scheme itself. These tests assert which artifact is selected, not that it
loads -- that needs the target interpreter.
"""

import re
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

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


def _extension_members(wheel: Path) -> list:
    with zipfile.ZipFile(wheel) as archive:
        return [
            name.rsplit("/", 1)[-1]
            for name in archive.namelist()
            if name.endswith((".pyd", ".so", ".dll"))
        ]


@pytest.fixture(scope="module")
def awscrt_artifacts_by_version(tmp_path_factory) -> dict:
    """Extension-module names in the real win_amd64 awscrt wheel for each supported version.

    Downloads rather than asserting a filename list, so a change to awscrt's wheel matrix
    surfaces here instead of in a silently unloadable bundle. Skips when there is no index
    to reach; the other tests in this module do not need the network.
    """
    platform = deps_bundle.SUPPORTED_PLATFORMS[0]
    download_root = tmp_path_factory.mktemp("awscrt_wheels")
    artifacts = {}
    for version in sorted(deps_bundle.SUPPORTED_PYTHON_VERSIONS, key=_version_key):
        target = download_root / _tag(version)
        try:
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "download",
                    "awscrt",
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
        except (subprocess.CalledProcessError, OSError) as error:
            pytest.skip(f"cannot download awscrt {platform} wheels: {error}")
        wheels = list(target.glob("*.whl"))
        assert len(wheels) == 1, f"expected one awscrt wheel for Python {version}, got {wheels}"
        artifacts[version] = _extension_members(wheels[0])
    return artifacts


def test_real_awscrt_wheels_collide_only_on_untagged_names(awscrt_artifacts_by_version):
    """Pins the naming premise the merge rests on to the wheels actually resolved.

    Ascending-first-wins is only safe while every name that collides across versions is
    abi3. A version-specific wheel installing an untagged name would hand 3.9's binary to
    every later interpreter, so assert that colliding names carry no interpreter tag and
    tagged names collide with nothing.
    """
    versions_by_artifact: dict = {}
    for version, artifacts in awscrt_artifacts_by_version.items():
        for artifact in artifacts:
            versions_by_artifact.setdefault(artifact, set()).add(version)

    for artifact, versions in versions_by_artifact.items():
        tagged = re.search(r"\.cp\d+-", artifact) is not None
        if len(versions) > 1:
            assert not tagged, (
                f"{artifact} is installed by Python {sorted(versions)} yet carries an "
                f"interpreter tag; the merge would ship only the lowest version's copy"
            )
        else:
            assert tagged or len(awscrt_artifacts_by_version) == 1, (
                f"{artifact} carries no interpreter tag but comes from Python "
                f"{sorted(versions)} alone; an untagged name must be abi3, shared by every "
                f"version from the abi3 floor up"
            )


def test_lowest_abi3_python_matches_awscrt(awscrt_artifacts_by_version):
    """Keeps the fixtures' abi3 floor honest against awscrt's real wheel matrix."""
    untagged_versions = {
        version
        for version, artifacts in awscrt_artifacts_by_version.items()
        for artifact in artifacts
        if re.search(r"\.cp\d+-", artifact) is None
    }
    assert untagged_versions, "awscrt published no abi3 win_amd64 wheel for any version"

    lowest_abi3 = min(untagged_versions, key=_version_key)
    assert _version_key(lowest_abi3) == LOWEST_ABI3_PYTHON, (
        f"awscrt now publishes abi3 wheels from Python {lowest_abi3}, not "
        f"{'.'.join(str(part) for part in LOWEST_ABI3_PYTHON)}; update LOWEST_ABI3_PYTHON"
    )
