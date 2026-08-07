# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""Unit tests for the maxcmd_render task-driver pure-logic functions."""

import importlib.util
import json
from pathlib import Path

# The driver lives under max_submitter/scripts, which is not an importable
# package (the scripts are injected as embedded files, not imported at runtime).
# Load it directly by file path so we can unit-test its pure helpers.
_SCRIPT_PATH = (
    Path(__file__).parents[3]
    / "src"
    / "deadline"
    / "max_submitter"
    / "scripts"
    / "maxcmd_render.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("maxcmd_render", _SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


maxcmd_render = _load_module()


class TestLoadPathMappingRules:
    """Tests for load_path_mapping_rules JSON parsing."""

    def test_missing_file_returns_empty(self):
        assert maxcmd_render.load_path_mapping_rules("does/not/exist.json") == []

    def test_empty_path_returns_empty(self):
        assert maxcmd_render.load_path_mapping_rules("") == []

    def test_parses_source_dest_pairs(self, tmp_path):
        rules_file = tmp_path / "rules.json"
        rules_file.write_text(
            json.dumps(
                {
                    "path_mapping_rules": [
                        {"source_path": "L:/tex", "destination_path": "C:/session/tex"},
                        {"source_path": "M:/cut", "destination_path": "C:/session/cut"},
                    ]
                }
            )
        )
        assert maxcmd_render.load_path_mapping_rules(str(rules_file)) == [
            ("L:/tex", "C:/session/tex"),
            ("M:/cut", "C:/session/cut"),
        ]

    def test_skips_incomplete_rules(self, tmp_path):
        rules_file = tmp_path / "rules.json"
        rules_file.write_text(
            json.dumps(
                {
                    "path_mapping_rules": [
                        {"source_path": "L:/tex", "destination_path": ""},
                        {"source_path": "", "destination_path": "C:/x"},
                        {"source_path": "S:/fx", "destination_path": "C:/session/fx"},
                    ]
                }
            )
        )
        assert maxcmd_render.load_path_mapping_rules(str(rules_file)) == [
            ("S:/fx", "C:/session/fx"),
        ]

    def test_malformed_json_returns_empty(self, tmp_path):
        rules_file = tmp_path / "rules.json"
        rules_file.write_text("{ not valid json")
        assert maxcmd_render.load_path_mapping_rules(str(rules_file)) == []


class TestBuildPrerenderMaxscript:
    """Tests for build_prerender_maxscript MAXScript generation."""

    def test_source_is_normalized_and_lowercased(self):
        script = maxcmd_render.build_prerender_maxscript([("L:\\Tex\\Wood", "C:/session/tex/wood")])
        # Source is normalized (backslash -> slash) and lowercased for matching
        assert '"l:/tex/wood"' in script
        # Destination keeps its case, normalized slashes
        assert '"C:/session/tex/wood"' in script

    def test_includes_bitmap_and_xref_remap_loops(self):
        script = maxcmd_render.build_prerender_maxscript([("L:/tex", "C:/s/tex")])
        assert "getClassInstances Bitmaptexture" in script
        assert "getXRefFile" in script

    def test_includes_output_and_render_element_remapping(self):
        script = maxcmd_render.build_prerender_maxscript([("L:/out", "C:/s/out")])
        # Main render output is remapped and its directory ensured
        assert "rendOutputFilename" in script
        assert "makeDir" in script
        # Render element outputs (incl. Pencil+ Line) are remapped
        assert "GetCurRenderElementMgr" in script
        assert "SetRenderElementFilename" in script

    def test_no_rules_produces_valid_empty_remap_block(self):
        script = maxcmd_render.build_prerender_maxscript([])
        assert "local remaps = #(" in script
        assert "getClassInstances Bitmaptexture" in script

    def test_render_elements_redirected_to_output_dir(self):
        """
        With an output dir, render element outputs (e.g. Pencil+ Line) are
        redirected there keeping their own filename, instead of relying on a
        path-mapping rule that output-only dirs never get.
        """
        script = maxcmd_render.build_prerender_maxscript(
            [("L:/tex", "C:/s/tex")], output_dir="C:/Sessions/s/out"
        )
        assert 'local jobOutputDir = "C:/Sessions/s/out"' in script
        assert "baseName = filenameFromPath reFn" in script
        assert 'reMapped = jobOutputDir + "/" + baseName' in script

    def test_render_elements_fall_back_to_rule_remap_without_output_dir(self):
        """Without an output dir, render elements use the rule-based remap."""
        script = maxcmd_render.build_prerender_maxscript([("L:/tex", "C:/s/tex")])
        assert 'local jobOutputDir = ""' in script
        assert "reMapped = _remapPath reFn" in script

    def test_render_element_basename_collision_is_disambiguated(self):
        """
        Two render elements whose scene paths share a basename would flatten to
        the same file under the job output dir. The script must track claimed
        basenames and, on collision, insert the element index before the
        extension so sequence-mode frame padding still composes.
        """
        script = maxcmd_render.build_prerender_maxscript(
            [("L:/tex", "C:/s/tex")], output_dir="C:/Sessions/s/out"
        )
        # Case-insensitive collision check against the claimed-names set.
        assert "findItem usedNames (toLower baseName)" in script
        # Index inserted before the extension, not appended after it.
        assert (
            'baseName = (getFilenameFile baseName) + "_re" + (reIdx as string) '
            "+ (getFilenameType baseName)" in script
        )
        assert "append usedNames (toLower baseName)" in script

    def test_main_output_basename_seeds_used_names(self):
        """The redirected beauty-pass basename is claimed so an element can't clobber it."""
        script = maxcmd_render.build_prerender_maxscript(
            [("L:/tex", "C:/s/tex")], output_dir="C:/Sessions/s/out"
        )
        assert "local usedNames = #()" in script
        assert "append usedNames (toLower (filenameFromPath rendOutputFilename))" in script

    def test_output_filename_seeds_used_names(self):
        """
        The -outputName beauty-pass filename is seeded into usedNames so an
        element whose basename matches can't collide with the main output even
        when rendOutputFilename is empty (common).
        """
        script = maxcmd_render.build_prerender_maxscript(
            [("L:/tex", "C:/s/tex")], output_dir="C:/Sessions/s/out", output_filename="render.exr"
        )
        assert 'local cmdOutputName = "render.exr"' in script
        assert "append usedNames (toLower cmdOutputName)" in script

    def test_output_filename_empty_does_not_seed(self):
        """When no output filename is passed, cmdOutputName is empty and no seed fires."""
        script = maxcmd_render.build_prerender_maxscript(
            [("L:/tex", "C:/s/tex")], output_dir="C:/Sessions/s/out", output_filename=""
        )
        assert 'local cmdOutputName = ""' in script

    def test_main_output_redirected_to_output_dir(self):
        """
        When no -outputName is passed the render falls back to the scene-baked
        rendOutputFilename, whose output-only directory gets no path-mapping
        rule. With an output dir it must be redirected there (keeping the
        scene's filename) so the write lands in a writable, captured location.
        """
        script = maxcmd_render.build_prerender_maxscript(
            [("L:/tex", "C:/s/tex")], output_dir="C:/Sessions/s/out"
        )
        assert (
            'rendOutputFilename = jobOutputDir + "/" + (filenameFromPath rendOutputFilename)'
            in (script)
        )

    def test_main_output_falls_back_to_rule_remap_without_output_dir(self):
        """Without an output dir, the main render output uses the rule-based remap."""
        script = maxcmd_render.build_prerender_maxscript([("L:/tex", "C:/s/tex")])
        assert "rendOutputFilename = _remapPath rendOutputFilename" in script

    def test_prefix_match_requires_path_boundary(self):
        """
        A rule prefix must match at a path boundary so "L:/tex" does not also
        capture "L:/textures/...". The generated script guards the remainder
        with a boundary check (empty tail or leading separator).
        """
        script = maxcmd_render.build_prerender_maxscript([("L:/tex", "C:/s/tex")])
        assert "tail = substring np (src.count + 1) (-1)" in script
        assert 'tail == "" or tail[1] == "/"' in script


class TestRunMaxcmd:
    """Tests for run_maxcmd output handling."""

    def test_non_utf8_output_does_not_crash(self, monkeypatch):
        """A stray non-UTF-8 byte from 3dsmaxcmd must not crash the reader."""

        class FakeProcess:
            # 0xb9 (superscript one) is invalid as a standalone UTF-8 byte.
            stdout = [b"normal line\n", b"bad byte \xb9 here\n"]

            def wait(self):
                return 0

        monkeypatch.setattr(maxcmd_render.subprocess, "Popen", lambda *a, **k: FakeProcess())

        # Should complete without raising UnicodeDecodeError and return the code.
        assert maxcmd_render.run_maxcmd(["3dsmaxcmd", "scene.max"]) == 0

    def test_returns_process_exit_code(self, monkeypatch):
        class FakeProcess:
            stdout: list = []

            def wait(self):
                return 3

        monkeypatch.setattr(maxcmd_render.subprocess, "Popen", lambda *a, **k: FakeProcess())
        assert maxcmd_render.run_maxcmd(["3dsmaxcmd", "scene.max"]) == 3


class TestBuildMaxcmdCommand:
    """Tests for build_maxcmd_command command-line assembly."""

    def test_minimal_command(self):
        cmd = maxcmd_render.build_maxcmd_command(
            "3dsmaxcmd", "C:/s/scene.max", 1, 10, "C:/s/pre.ms"
        )
        assert cmd == [
            "3dsmaxcmd",
            "-start:1",
            "-end:10",
            "-preRenderScript:C:/s/pre.ms",
            "C:/s/scene.max",
        ]

    def test_command_includes_camera_and_output(self):
        cmd = maxcmd_render.build_maxcmd_command(
            "3dsmaxcmd",
            "C:/s/scene.max",
            1,
            10,
            "C:/s/pre.ms",
            camera="RenderCam",
            output_path="C:/out/render.exr",
        )
        assert "-camera:RenderCam" in cmd
        assert "-outputName:C:/out/render.exr" in cmd
        # Scene file is always last
        assert cmd[-1] == "C:/s/scene.max"

    def test_output_name_passed_verbatim_without_frame_token(self):
        """
        The output name must be passed as a plain stem with no per-frame token.

        3ds Max renders an explicit range (-start:N -end:N) in sequence mode and
        inserts the padded frame number itself (render0001.exr), so each
        per-frame task already writes a distinct file. Injecting a frame token
        here would double-number the output (render0001.0001.exr). Verified on a
        multi-frame Deadline Cloud render (frames 1-3 produced
        cmdtest0001/0002/0003.jpeg). This test pins that the driver does not add
        one.
        """
        cmd = maxcmd_render.build_maxcmd_command(
            "3dsmaxcmd",
            "C:/s/scene.max",
            2,
            2,
            "C:/s/pre.ms",
            output_path="C:/out/render.exr",
        )
        # Exactly the stem we passed, with no frame number / padding token added.
        assert "-outputName:C:/out/render.exr" in cmd
        assert not any("%04d" in arg or "####" in arg for arg in cmd)
        # The single-frame task still passes the explicit range that puts Max in
        # sequence mode (so Max does the padding).
        assert "-start:2" in cmd and "-end:2" in cmd


class TestParseArgs:
    """Tests for parse_args — parameters arrive as argv, not source literals."""

    def test_parses_all_arguments(self):
        args = maxcmd_render.parse_args(
            [
                "--executable",
                "3dsmaxcmd",
                "--scene-file",
                "C:/s/scene.max",
                "--output-dir",
                "C:/out",
                "--output-file-name",
                "render.exr",
                "--camera",
                "Cam001",
                "--frame",
                "7",
                "--rules-file",
                "C:/s/rules.json",
            ]
        )
        assert args.executable == "3dsmaxcmd"
        assert args.scene_file == "C:/s/scene.max"
        assert args.output_dir == "C:/out"
        assert args.output_file_name == "render.exr"
        assert args.camera == "Cam001"
        assert args.frame == 7
        assert args.rules_file == "C:/s/rules.json"

    def test_optional_values_default_to_empty(self):
        args = maxcmd_render.parse_args(["--scene-file", "C:/s/scene.max", "--frame", "1"])
        assert args.output_dir == ""
        assert args.output_file_name == ""
        assert args.camera == ""
        assert args.rules_file == ""

    def test_trailing_backslash_and_quote_values_are_safe(self):
        """
        Passing values as argv (not interpolating into raw-string literals)
        means a Windows path ending in a backslash or containing a quote is
        carried verbatim instead of breaking the task script's parsing.
        """
        args = maxcmd_render.parse_args(
            [
                "--scene-file",
                r"C:\renders\a\scene.max",
                "--output-dir",
                "D:\\renders\\",  # trailing backslash
                "--output-file-name",
                'weird".exr',  # embedded quote
                "--frame",
                "1",
            ]
        )
        assert args.output_dir == "D:\\renders\\"
        assert args.output_file_name == 'weird".exr'
