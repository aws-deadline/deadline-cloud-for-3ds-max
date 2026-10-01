# Filter Output Assets from get_referenced_files()

## Problem

The `get_referenced_files()` function currently uses `ATSOps.GetFiles()` which returns all tracked assets, including render outputs (main render output path, Render Elements like AO/Z-depth, and Bake-to-Texture paths). These output files should not be included in the referenced files list since they are destinations, not source dependencies.

## Current Implementation

```python
def get_referenced_files() -> list:
    rt.ATSOps.Refresh()
    maps = rt.ATSOps.GetFiles(pymxs.byref(None))
    maps_in_scene = [str(x.replace("\\", "/")) for x in list(maps)[1]]
    # ... nested file handling ...
    return maps_in_scene
```

## Proposed Change (Minimal)

Use `AssetManager.getAssetId()` and `AssetManager.getAsset()` to check each file's asset type and filter out `#RenderOutput` and `#VideoPost` types.

```python
def get_referenced_files() -> list:
    """
    Finds all referenced files (bitmap textures, xrefs).
    Excludes render output files (render outputs, render elements, video post).

    :returns: list with paths to all referenced files
    :return_type: list
    """
    # Refresh Asset Tracking to make sure we have the latest version
    rt.ATSOps.Refresh()

    # Convert result from usedMaps MAXScript function into a python list
    maps = rt.ATSOps.GetFiles(pymxs.byref(None))
    # Note: ATSOps returns list[int, [file paths]]
    all_files = list(maps)[1]

    # Filter out output assets (RenderOutput, VideoPost)
    maps_in_scene = []
    for f in all_files:
        try:
            asset_id = rt.AssetManager.getAssetId(f)
            asset_obj = rt.AssetManager.getAsset(asset_id)
            asset_type = str(asset_obj.getType())
            if asset_type in ("#RenderOutput", "#VideoPost"):
                continue
        except Exception:
            # If we can't determine the asset type, include the file
            pass
        maps_in_scene.append(str(f.replace("\\", "/")))

    # Check for nested files to make sure the path correctly gets converted when it's relative
    nested_files: list[list] = []
    for i, map_ in enumerate(maps_in_scene):
        if os.path.normpath(map_) == get_scene_path():
            continue
        nested = rt.ATSOps.GetDependentFiles(map_, False, pymxs.byref(None))[1]
        if not nested:
            continue
        for item in nested:
            try:
                index = maps_in_scene.index(item.replace("\\", "/"))
            except ValueError:
                # Item may have been filtered out as an output asset
                continue
            # Pass along the nested file, the index of that nested file and the index of the parent
            # in maps_in_scene
            nested_files += [[item, index, i]]

    # Update the path in the maps_in_scene
    for file in nested_files:
        relative_dir = os.path.split(maps_in_scene[file[2]])[0]
        maps_in_scene[file[1]] = os.path.join(relative_dir, file[0])

    return maps_in_scene
```

## Key Changes

1. Added filtering loop that checks each file's asset type via `AssetManager`
2. Skip files with type `#RenderOutput` or `#VideoPost`
3. Added try/except in nested file handling to handle cases where a nested file was filtered out
4. Wrapped asset type check in try/except to gracefully handle edge cases

## Asset Types Reference

| Type | Description | Include? |
|------|-------------|----------|
| `#Bitmap` | Texture files | Yes |
| `#XRef` | External references | Yes |
| `#Photometric` | IES light files | Yes |
| `#ExternalLink` | External links | Yes |
| `#RenderOutput` | Main render output, render elements | No |
| `#VideoPost` | Video post output paths | No |

## Proposed Tests

### Unit Tests (with mocked pymxs)

```python
import pytest
from unittest.mock import MagicMock, patch

@pytest.fixture
def mock_pymxs():
    """Mock pymxs module for testing."""
    with patch.dict('sys.modules', {'pymxs': MagicMock()}):
        yield

class TestGetReferencedFilesFiltering:
    """Tests for output asset filtering in get_referenced_files()."""

    def test_excludes_render_output_assets(self, mock_pymxs):
        """Verify that #RenderOutput type assets are excluded."""
        # Setup: ATSOps returns mix of input and output files
        # Assert: Only input files are returned

    def test_excludes_video_post_assets(self, mock_pymxs):
        """Verify that #VideoPost type assets are excluded."""
        # Setup: ATSOps returns VideoPost output path
        # Assert: VideoPost path is not in result

    def test_includes_bitmap_assets(self, mock_pymxs):
        """Verify that #Bitmap type assets are included."""
        # Setup: ATSOps returns bitmap texture paths
        # Assert: All bitmap paths are in result

    def test_includes_xref_assets(self, mock_pymxs):
        """Verify that #XRef type assets are included."""
        # Setup: ATSOps returns XRef paths
        # Assert: All XRef paths are in result

    def test_handles_asset_manager_exception(self, mock_pymxs):
        """Verify graceful handling when AssetManager fails."""
        # Setup: AssetManager.getAssetId raises exception
        # Assert: File is still included (fail-open behavior)

    def test_nested_files_with_filtered_parent(self, mock_pymxs):
        """Verify nested file handling when parent is filtered out."""
        # Setup: Parent file is RenderOutput, has nested dependencies
        # Assert: No crash, nested files handled correctly
```

### Integration Tests (requires 3ds Max)

```python
class TestGetReferencedFilesIntegration:
    """Integration tests requiring 3ds Max environment."""

    def test_scene_with_render_output_set(self):
        """Test scene that has render output path configured."""
        # Setup: Create scene with render output path
        # Call: get_referenced_files()
        # Assert: Render output path not in result

    def test_scene_with_render_elements(self):
        """Test scene with render elements (AO, Z-depth, etc.)."""
        # Setup: Create scene with render elements
        # Call: get_referenced_files()
        # Assert: Render element paths not in result

    def test_scene_with_mixed_assets(self):
        """Test scene with textures, xrefs, and render outputs."""
        # Setup: Create scene with various asset types
        # Call: get_referenced_files()
        # Assert: Only input assets returned
```

## Alternative Approaches Considered

### 1. Using ATSOps.GetFileSystemStatus with bitmask
- Pros: Uses same API as current implementation
- Cons: Requires understanding undocumented bitmask values, less readable

### 2. Full migration to AssetManager.getAssets()
- Pros: Cleaner API, no ATSOps dependency
- Cons: Larger change, may miss "stale" references that ATS holds onto

## Recommendation

The proposed change is minimal and targeted:
- Adds ~15 lines of filtering logic
- Preserves existing ATSOps-based enumeration
- Uses well-documented AssetManager type checking
- Fails open (includes file if type check fails)
