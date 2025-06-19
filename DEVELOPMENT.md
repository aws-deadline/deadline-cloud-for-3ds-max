[deadline-cloud-monitor-setup]: https://docs.aws.amazon.com/deadline-cloud/latest/userguide/submitter.html#install-deadline-cloud-monitor
[aws-cli-credentials]: https://docs.aws.amazon.com/cli/v1/userguide/cli-chap-authentication.html
[3ds-max-2024-folders-documentation]: https://help.autodesk.com/view/MAXDEV/2024/ENU/?guid=GUID-F7577416-051E-478C-BB5D-81243BAAC8EC

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

## Submitter Development Workflow

WARNING: This workflow installs additional Python packages into your 3ds Max's python distribution.

#### Manual installation

1. Clone `deadline-cloud-for-3ds-max`, and build your local copy running `hatch build`.
1. To install the submitter in 3dsMax, you need to copy the UI components into the corresponding 3ds Max installation directories. You can find the UI component files in your local copy of `deadline-cloud-for-3ds-max`.
    1. Copy `<LOCAL_REPO_PATH>\install_files\STDCMenuCreator_v#.ms` into your 3DS Max startup scripts (e.g. `C:\Program Files\Autodesk\<version>\scripts\Startup`, more details about 3ds Max system directories can be found in the 3ds Max [documentation][3ds-max-2024-folders-documentation]). For 3ds Max 2024 use `STDCMenuCreator_v0.ms`. For 3ds Max 2025+ use `STDCMenuCreator_v1.ms`.
    1. Copy `<LOCAL_REPO_PATH>\install_files\AWSDeadline-SubmitToDeadlineCloud.mcr` in 3ds Max usermacros directory (e.g. `C:\Users\<username>\AppData\Local\Autodesk\3dsMax\<version>\ENU\usermacros`).
1. The point of entry for the submitter is the `run_ui.py` file under the `max_submitter` folder. Thus, this file needs to be discoverable by 3dsMax, and `max_submitter` needs to be a discoverable package by python. In Powershell run:
    1. `$env:ADSK_3DSMAX_SCRIPTS_ADDON_DIR += ";<LOCAL_REPO_PATH>\src\deadline\max_submitter"`.
    1. `$env:PYTHONPATH += ";<LOCAL_REPO_PATH>\src\;<LOCAL_REPO_PATH>\src\deadline\max_submitter"`.
1. Install `deadline` package to `~\DeadlineCloudSubmitter\Submitters\3dsMax\scripts`, using a python version that is compatible with the version of 3dsMax that you are using. In Powershell run:
    1. `& "C:\Program Files\Autodesk\<version>\Python\python.exe" -m ensurepip`
    1. `& "C:\Program Files\Autodesk\<version>\Python\python.exe" -m pip install deadline -t $env:HOMEPATH\DeadlineCloudSubmitter\Submitters\3dsMax\scripts` 
1. Run `3dsmax` from the same command-line window where the environment variables were set. To do so, `3dsmax` needs to be part of the PATH. In Powershell run `$env:PATH += ";C:\Program Files\Autodesk\<version>"`.
1. To supply AWS account credentials for the submitter to use when submitting a job you can either:
    1. [Install and set up the Deadline Cloud Monitor][deadline-cloud-monitor-setup], and then log in to the monitor. Logging in
       to the monitor will make AWS credentials available to the submitter, automatically.
    1. Set up an AWS credentials profile [as you would for the AWS CLI][aws-cli-credentials], and select that profile for the submitter
       to use.
    1. Or default to your AWS EC2 instance profile credentials if you are running a workstation in the cloud.

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

### Intergration Test Workflow
Integration tests are located under `test/integ` directory of this repository. If you are adding
or modifying functionality, then you will want to be writing one or more integ tests to demonstrate that your
logic behaves as expected and that future changes do not accidentally break your change.

To run the integ tests, you need to:
1. Add 3dsMax python executable to the PATH:
   
   For example, default path of 3dsMax python on Windows is 

```
C:\Program Files\Autodesk\3ds Max 2024\Python
```
2. Run command to install pip to this python executable:
```
python -m ensurepip
```
3. Set the `3DSMAX_EXECUTABLE` environment variable to use `3dsmaxbatch`

4. Use hatch to run all integ tests:
```
hatch run integ:test
```
5. (Optional) Use hatch to run submitter tests:
```
hatch run integ:test_submitters
```
6. (Optional) Use hatch to run adaptor tests:
```
hatch run integ:test_adaptors
```