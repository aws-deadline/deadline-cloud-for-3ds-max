# V-Ray Standalone Tile Rendering

For advanced V-Ray users, you can export V-Ray scene files (.vrscene) locally within 3ds Max and submit them as standalone job bundles with tile rendering support. This workflow is particularly useful for large resolution renders where tiling can reduce memory footprint and optimize render times.

## When to Use This Workflow

Tile rendering with V-Ray Standalone on Linux workers is beneficial for:

- Large resolution renders (outdoor advertising, high-resolution entertainment content)
- Scenes with high memory requirements that benefit from processing smaller regions
- Optimizing render resources by splitting images into evenly sized regions rendered in parallel
- Minimizing rendering time through parallel processing
- Reducing infrastructure costs by leveraging Linux workers instead of Windows workers (Linux EC2 instances typically have lower hourly rates than equivalent Windows instances)

## Exporting V-Ray Scene Files

V-Ray for 3ds Max includes a Scene Exporter that creates .vrscene files containing all scene information (geometry, lights, shaders) that can be rendered with V-Ray Standalone.

**To export a V-Ray scene file:**

1. In 3ds Max, configure your V-Ray render settings as needed
1. Use the V-Ray Scene Exporter to export your scene as a .vrscene file
1. The exported file is a text-based format that contains complete scene data

## Submitting Tile Rendering Jobs

Once you have exported your .vrscene file, you can use the standalone tile rendering job bundle to submit optimized rendering jobs to Deadline Cloud.

For general information about creating and submitting job bundles, see [Open Job Description templates for Deadline Cloud](https://docs.aws.amazon.com/deadline-cloud/latest/developerguide/build-job-bundle.html) in the AWS Deadline Cloud Developer Guide.

**Reference implementation:**

The [tile_render_with_vray_linux](https://github.com/aws-deadline/deadline-cloud-samples/tree/mainline/job_bundles/tile_render_with_vray_linux) sample in the deadline-cloud-samples repository demonstrates:

- How to split large images into tiles
- Parallel rendering of tiles on Linux workers
- Automatic tile assembly after rendering completes

You can submit this job bundle using the Deadline Cloud CLI:

```bash
deadline bundle submit <path-to-job-bundle>
```

Or use the GUI submitter:

```bash
deadline bundle gui-submit <path-to-job-bundle>
```

**Benefits of this approach:**

- Reduced memory usage per render task
- Parallel processing of tiles for faster overall render times
- Better resource utilization across your Deadline Cloud farm
- Flexibility to customize tile dimensions based on your scene requirements
- Cost savings by using Linux workers instead of Windows workers (Linux EC2 instances typically cost less than equivalent Windows instances)

## Job Bundle Structure

The tile rendering job bundle uses Open Job Description templates to define:

- Job parameters for specifying the number of horizontal and vertical tiles
- Task parameters that create individual tasks for each tile
- A rendering step that processes each tile in parallel
- An assembly step that stitches tiles together after rendering completes

## Requirements

- V-Ray for 3ds Max with Scene Exporter
- Deadline Cloud farm configured with Linux workers
- V-Ray Standalone installed on worker nodes
- FFmpeg or similar tool for tile assembly (can be provided via Conda)
