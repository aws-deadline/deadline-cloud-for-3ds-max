# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
from __future__ import annotations

import re
import shutil
import subprocess
import sys

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

SUPPORTED_PYTHON_VERSIONS = ["3.9", "3.10", "3.11", "3.12"]
SUPPORTED_PLATFORMS = ["win_amd64"]
# Packages with compiled extension modules, fetched once per supported Python version so the
# bundle carries a loadable artifact for each interpreter. Resolving these in the base
# environment alone would ship only what the build host's interpreter produced. awscrt is
# not uniformly abi3 (3.9 and 3.10 get version-specific artifacts, 3.11+ abi3), and pyyaml's
# `_yaml` is version-specific and fails soft -- it falls back to its pure-Python parser.
NATIVE_DEPENDENCIES = ["xxhash", "psutil", "awscrt", "pyyaml"]


def _get_project_dict() -> dict[str, Any]:
    if sys.version_info < (3, 11):
        with TemporaryDirectory() as toml_env:
            toml_install_pip_args = ["pip", "install", "--target", toml_env, "toml"]
            subprocess.run(toml_install_pip_args, check=True)
            sys.path.insert(0, toml_env)
            import toml
        mode = "r"
    else:
        import tomllib as toml

        mode = "rb"

    with open("pyproject.toml", mode) as pyproject_toml:
        return toml.load(pyproject_toml)


def _get_dependencies(pyproject_dict: dict[str, Any]) -> list[str]:
    if "project" not in pyproject_dict:
        raise Exception("pyproject.toml is missing project section")
    if "dependencies" not in pyproject_dict["project"]:
        raise Exception("pyproject.toml is missing dependencies section")

    dependencies = pyproject_dict["project"]["dependencies"]
    deps_noopenjd = filter(lambda dep: not dep.startswith("openjd"), dependencies)
    return list(map(lambda dep: dep.replace(" ", ""), deps_noopenjd))


def _get_package_version_regex(package: str) -> re.Pattern:
    # Case-insensitive because `pip list` prints the distribution's casing, not the
    # requirement's: `pyyaml` is reported as `PyYAML`. The required whitespace keeps a prefix
    # sibling like `pyyaml-env-tag` from matching.
    return re.compile(rf"^{re.escape(package)}\s+(\S+)\s*$", re.IGNORECASE)


def _get_package_version(package: str, install_path: Path) -> str:
    version_regex = _get_package_version_regex(package)
    pip_args = ["pip", "list", "--path", str(install_path)]
    output = subprocess.run(pip_args, check=True, capture_output=True).stdout.decode("utf-8")
    for line in output.split("\n"):
        match = version_regex.match(line)
        if match:
            return match.group(1)
    raise Exception(f"Could not find version for package {package}")


def _add_console_extra(requirement: str) -> str:
    """Add deadline's `console` extra to a requirement string, preserving its specifier."""
    match = re.fullmatch(
        r"(?P<name>[A-Za-z0-9._-]+)(?:\[(?P<extras>[^\]]*)\])?(?P<spec>.*)", requirement
    )
    if not match or match.group("name").lower() != "deadline":
        return requirement
    extras = [extra for extra in (match.group("extras") or "").split(",") if extra]
    if "console" not in extras:
        extras.append("console")
    return f"{match.group('name')}[{','.join(extras)}]{match.group('spec')}"


def _build_base_environment(working_directory: Path, dependencies: list[str]) -> Path:
    (working_directory / "base_env").mkdir()
    base_env_path = working_directory / "base_env"
    # The bundle is the submitter, which needs AWS Console sign-in. The console extra is
    # requested here rather than declared in project.dependencies to keep awscrt out of the
    # published wheel's metadata: no awscrt wheel satisfying botocore's crt pin exists for
    # macosx_10_9_x86_64, so a consumer resolving this package under --only-binary=:all: for
    # that tag would fail or silently backtrack.
    #
    # Requesting the extra rather than installing awscrt directly keeps the bundle on the
    # exact awscrt botocore's crt extra pins, plus the botocore floor the console login
    # provider itself needs -- that provider lives in botocore, not in deadline.
    dependencies_for_pip = [_add_console_extra(dep) for dep in dependencies]
    base_env_pip_args = [
        "pip",
        "install",
        "--target",
        str(base_env_path),
        "--only-binary=:all:",
        # Without this pip takes the platform tags from whatever host the build runs on, so
        # the bundle's contents would depend on the runner rather than on what it targets.
        # --platform requires the --only-binary and --target above.
        "--platform",
        _target_platform(),
        *dependencies_for_pip,
    ]
    subprocess.run(base_env_pip_args, check=True)
    return base_env_path


def _target_platform() -> str:
    """The single platform tag the bundle is resolved for.

    The bundle is one flat directory, so it can only hold one build of a given filename; a
    second supported platform would need the merge to keep them apart before this could
    return more than one.
    """
    if len(SUPPORTED_PLATFORMS) != 1:
        raise Exception(
            f"the bundle resolves wheels for exactly one platform, but SUPPORTED_PLATFORMS "
            f"is {SUPPORTED_PLATFORMS}"
        )
    return SUPPORTED_PLATFORMS[0]


def _python_version_key(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))


def _download_native_dependencies(working_directory: Path, base_env: Path) -> list[Path]:
    versioned_native_dependencies = [
        f"{package_name}=={_get_package_version(package_name, base_env)}"
        for package_name in NATIVE_DEPENDENCIES
    ]
    native_dependency_paths = []
    # Ascending order is load-bearing: _copy_native_to_base_env resolves a filename
    # collision in favour of the tree it sees first.
    for version in sorted(SUPPORTED_PYTHON_VERSIONS, key=_python_version_key):
        native_dependency_path = working_directory / "native" / f"{version.replace('.', '_')}"
        native_dependency_paths.append(native_dependency_path)
        native_dependency_path.mkdir(parents=True)
        native_dependency_pip_args = [
            "pip",
            "install",
            "--target",
            str(native_dependency_path),
            "--python-version",
            version,
            "--platform",
            _target_platform(),
            "--only-binary=:all:",
            # These trees exist only for their compiled artifacts and overwrite the base
            # environment during the merge. Without --no-deps each would carry a transitive
            # closure resolved independently of the base environment's, clobbering whatever
            # it resolved for anything they share.
            "--no-deps",
            *versioned_native_dependencies,
        ]
        subprocess.run(native_dependency_pip_args, check=True)
    return native_dependency_paths


def _copy_native_to_base_env(base_env: Path, native_dependency_paths: list[Path]) -> None:
    """Flatten the per-version native trees into the bundle, first tree to supply a name wins.

    ``native_dependency_paths`` is ascending by Python version, and the winner must not be
    the base environment: it resolved these for whatever interpreter the build host runs,
    which need not be a version the bundle targets.

    Which copy survives follows from wheel naming, so no per-package rule is needed.
    Version-specific names carry an interpreter tag and cannot collide, so every version
    keeps its own. Colliding names are abi3, and abi3 is forward compatible only -- so the
    copy built for the lowest supported abi3 Python is the one that loads everywhere, which
    is what ascending order keeps.
    """
    copied: set[Path] = set()
    for native_dependency_path in native_dependency_paths:
        for file in native_dependency_path.rglob("*"):
            if file.is_file():
                relative = file.relative_to(native_dependency_path)
                if relative in copied:
                    continue
                in_base_env = base_env / relative
                in_base_env.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(str(file), str(in_base_env))
                copied.add(relative)


def _get_zip_path(working_directory: Path, project_dict: dict[str, Any]) -> Path:
    if "project" not in project_dict:
        raise Exception("pyproject.toml is missing project section")
    if "name" not in project_dict["project"]:
        raise Exception("pyproject.toml is missing name section")
    transformed_project_name = (
        f"{project_dict['project']['name'].replace('-', '_')}_submitter-deps.zip"
    )
    return working_directory / transformed_project_name


def _zip_bundle(base_env: Path, zip_path: Path) -> None:
    shutil.make_archive(str(zip_path.with_suffix("")), "zip", str(base_env))


def _copy_zip_to_destination(zip_path: Path) -> Path:
    dependency_bundle_dir = Path.cwd() / "dependency_bundle"
    dependency_bundle_dir.mkdir(exist_ok=True)
    zip_destination = dependency_bundle_dir / zip_path.name
    if zip_destination.exists():
        zip_destination.unlink()
    shutil.copy(str(zip_path), str(zip_destination))

    return zip_destination


def build_deps_bundle() -> None:
    with TemporaryDirectory() as working_directory:
        working_directory = Path(working_directory)
        project_dict = _get_project_dict()
        dependencies = _get_dependencies(project_dict)
        base_env = _build_base_environment(working_directory, dependencies)
        native_dependency_paths = _download_native_dependencies(working_directory, base_env)
        _copy_native_to_base_env(base_env, native_dependency_paths)
        zip_path = _get_zip_path(working_directory, project_dict)
        _zip_bundle(base_env, zip_path)
        print(list(working_directory.glob("*")))
        _copy_zip_to_destination(zip_path)


if __name__ == "__main__":
    build_deps_bundle()
