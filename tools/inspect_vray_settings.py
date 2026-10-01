"""
Script to inspect V-Ray renderer settings in 3ds Max.
Run this in 3ds Max Python console or via MAXScript python.ExecuteFile()
"""

from pymxs import runtime as rt


def inspect_vray_settings():
    """Print current V-Ray renderer settings used by max_utils."""

    renderer = rt.renderers.current
    renderer_name = str(renderer)

    print("=" * 60)
    print(f"Current Renderer: {renderer_name}")
    print("=" * 60)

    # Check if V-Ray
    is_vray = "V_Ray" in renderer_name or "VRay" in renderer_name
    is_gpu = "GPU" in renderer_name

    print(f"Is V-Ray: {is_vray}")
    print(f"Is GPU: {is_gpu}")
    print()

    if not is_vray:
        print("Not a V-Ray renderer, exiting.")
        return

    # V-Ray VFB settings
    print("-" * 40)
    print("V-Ray VFB / Output Settings:")
    print("-" * 40)

    settings = [
        "output_on",  # V-Ray VFB enabled
        "output_splitgbuffer",  # Split buffer enabled
        "output_splitRGB",  # Save RGB channels
        "output_splitAlpha",  # Save Alpha channel
        "output_splitfilename",  # Split buffer filename
        "output_splitbitmap",  # Split buffer bitmap object
        "output_saveRawFile",  # Save raw .vrimg files
    ]

    for setting in settings:
        try:
            value = getattr(renderer, setting)
            print(f"  {setting}: {value}")
        except Exception as e:
            print(f"  {setting}: <not available> ({e})")

    # For GPU, also check vray_rt_settings
    if is_gpu:
        print()
        print("-" * 40)
        print("V-Ray GPU (vray_rt_settings):")
        print("-" * 40)

        vray_rt_settings = rt.renderers.current.V_Ray_settings
        if vray_rt_settings:
            for setting in settings:
                try:
                    value = getattr(vray_rt_settings, setting)
                    print(f"  {setting}: {value}")
                except Exception as e:
                    print(f"  {setting}: <not available> ({e})")

    # Render Element Manager
    print()
    print("-" * 40)
    print("Render Element Manager:")
    print("-" * 40)

    re_manager = rt.maxOps.GetCurRenderElementMgr()
    if re_manager:
        num_elements = re_manager.NumRenderElements()
        print(f"  Number of render elements: {num_elements}")
        print(f"  Elements active: {re_manager.GetElementsActive()}")

        print()
        print("  Render Elements:")
        for i in range(num_elements):
            element = re_manager.GetRenderElement(i)
            element_name = element.elementName if hasattr(element, "elementName") else str(element)
            element_enabled = element.enabled if hasattr(element, "enabled") else "N/A"

            # Get output filename
            try:
                output_file = re_manager.GetRenderElementFilename(i)
            except:  # noqa: E722
                output_file = "<none>"

            # Check vrayVFB property
            vray_vfb = "N/A"
            try:
                vray_vfb = element.vrayVFB
            except:  # noqa: E722
                pass

            print(f"    [{i}] {element_name}")
            print(f"        enabled: {element_enabled}, vrayVFB: {vray_vfb}")
            print(f"        output: {output_file}")
    else:
        print("  No render element manager found")

    # Dump all renderer attributes
    print()
    print("-" * 40)
    print("All Renderer Attributes:")
    print("-" * 40)

    try:
        # Get all properties using showProperties
        props = rt.getPropNames(renderer)
        if props:
            print(f"  Found {len(props)} properties:")
            for prop in sorted(props, key=str):
                try:
                    value = rt.getProperty(renderer, prop)
                    # Truncate long values
                    value_str = str(value)
                    if len(value_str) > 100:
                        value_str = value_str[:100] + "..."
                    print(f"    {prop}: {value_str}")
                except Exception as e:
                    print(f"    {prop}: <error reading: {e}>")
        else:
            print("  No properties found via getPropNames")
    except Exception as e:
        print(f"  Error getting properties: {e}")

    # Also try dir() on the renderer
    print()
    print("-" * 40)
    print("Renderer dir() attributes (output_* and split*):")
    print("-" * 40)

    try:
        attrs = dir(renderer)
        output_attrs = [a for a in attrs if "output" in a.lower() or "split" in a.lower()]
        for attr in sorted(output_attrs):
            try:
                value = getattr(renderer, attr)
                print(f"    {attr}: {value}")
            except Exception as e:
                print(f"    {attr}: <error: {e}>")
    except Exception as e:
        print(f"  Error with dir(): {e}")

    print()
    print("=" * 60)
    print("Done")
    print("=" * 60)


if __name__ == "__main__":
    inspect_vray_settings()
