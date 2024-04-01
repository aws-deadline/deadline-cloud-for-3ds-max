# Development documentation
This package has two active branches:

- `mainline` -- For active development. This branch is not intended to be consumed by other packages. Any commit to this branch may break APIs, dependencies, and so on, and thus break any consumer without notice.
- `release` -- The official release of the package intended for consumers. Any breaking releases will be accompanied with an increase to this package's interface version.

## Build / Test / Release

### Build the package

```bash
hatch build
```

### Run tests

```bash
hatch run test
```

### Run linting

```bash
hatch run lint
```

### Run formatting

```bash
hatch run fmt
```

### Run tests for all supported Python versions

```bash
hatch run all:test
```

## Use development Submitter in 3ds Max

```bash
hatch run install
hatch shell
```
Then launch 3ds Max from that terminal.

A development version of deadline-cloud-for-3ds-max is then available to be loaded.

## Submitter Development Workflow

WARNING: This workflow installs additional Python packages into your 3ds Max's python distribution.

#### Manual installation

1. Copy `STDCMenuCreator.ms` into your 3DS Max startup scripts (e.g. `C:\Program Files\Autodesk\<version>\scripts\Startup`)
2. Put `AWSDeadline-SubmitToDeadlineCloud.mcr` in 3ds Max usermacros directory (e.g. `C:\Users\<username>\AppData\Local\Autodesk\3dsMax\<version>\ENU\usermacros`).
3. Create a `python` folder in your scripts directory (e.g. `C:\Users\<username>\AppData\Local\Autodesk\3dsMax\<version>\ENU\scripts`).
4. Copy `max_submitter` folder into that newly created `python` folder.
5. Install `deadline` package (from CodeArtifact) to `~\DeadlineCloudSubmitter\Submitters\3dsMax\scripts` using a Python 3.9 installation (for compatibility with Max)
    - `pip install deadline -t ~\DeadlineCloudSubmitter\Submitters\3dsMax\scripts`

#### Install for Development

1. Copy `STDCMenuCreator.ms` into your 3DS Max startup scripts (e.g. `C:\Program Files\Autodesk\<version>\scripts\Startup`).
2. Modify the file path in `STDCMenuCreator.ms`  to `<reporoot>/src/deadline/max_submitter`. Set the `DEBUG` variable to `true`.
3. Put `AWSDeadline-SubmitToDeadlineCloud.mcr` and `AWSDeadline-RunJobBundleTests.mcr` in 3ds Max usermacros directory (e.g. `C:\Users\<username>\AppData\Local\Autodesk\3dsMax\<version>\ENU\usermacros`).
4. Modify the path in `AWSDeadline-SubmitToDeadlineCloud.mcr` to `<reporoot>/src/deadline/max_submitter/run_ui.py`. Set the `DEBUG` variable to `true`.
5. Modify the path in `AWSDeadline-RunJobBundleTests.mcr` to `<reporoot>/src/deadline/max_submitter/job_bundle_output_test_runner.py`. Set the `DEBUG` variable to `true`.
6. Install `deadline` package (from CodeArtifact) to `~\DeadlineCloudSubmitter\Submitters\3dsMax\scripts` using a Python 3.9 installation (for compatibility with Max)
    - `pip install deadline -t ~\DeadlineCloudSubmitter\Submitters\3dsMax\scripts`

### Usage

After installation a "Deadline Cloud" menu is available the menu bar. Run "Submit to Deadline Cloud" to open the submitter.

### Application Interface Adaptor Development Workflow

You can work on the adaptor alongside your submitter development workflow using a Deadline Cloud
farm that uses a service-managed fleet. You'll need to perform the following steps to substitute
your build of the adaptor for the one in the service.

1. Use the development location from the Submitter Development Workflow. Make sure you're running 3ds Max with `set DEADLINE_ENABLE_DEVELOPER_OPTIONS=true` enabled.
2. Build wheels for `openjd_adaptor_runtime`, `deadline` and `deadline_cloud_for_3ds_max`, place them in a "wheels" folder in `deadline-cloud-for-3ds-max`. A script is provided to do this, just execute from `deadline-cloud-for-3ds-max`:

   ```bash
   # If you don't have the build package installed already
   $ pip install build
   ...
   $ ./scripts/build_wheels.sh
   ```

   Wheels should have been generated in the "wheels" folder:

   ```bash
   $ ls ./wheels
   deadline_cloud_for_3ds_max-<version>-py3-none-any.whl
   deadline-<version>-py3-none-any.whl
   openjd_adaptor_runtime-<version>-py3-none-any.whl
   ```

3. Open the 3ds Max integrated submitter, and in the Job-Specific Settings tab, enable the option 'Include Adaptor Wheels'. This option is only visible when the environment variable `DEADLINE_ENABLE_DEVELOPER_OPTIONS` is set to `true`. Then submit your test job.