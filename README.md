# AWS Deadline Cloud for 3ds Max


[![pypi](https://img.shields.io/pypi/v/deadline-cloud-for-3ds-max.svg?style=flat)](https://pypi.python.org/pypi/deadline-cloud-for-3ds-max)
[![python](https://img.shields.io/pypi/pyversions/deadline-cloud-for-3ds-max.svg?style=flat)](https://pypi.python.org/pypi/deadline-cloud-for-3ds-max)
[![license](https://img.shields.io/pypi/l/deadline-cloud-for-3ds-max.svg?style=flat)](https://github.com/aws-deadline/deadline-cloud-for-3ds-max/blob/mainline/LICENSE)

AWS Deadline Cloud for 3ds Max is a python package that allows users to create [AWS Deadline Cloud][deadline-cloud] jobs from within 3ds Max. Using the [Open Job Description (OpenJD) Adaptor Runtime][openjd-adaptor-runtime] this package also provides a command line application that adapts 3ds Max's command line interface to support the [OpenJD specification][openjd].

[deadline-cloud]: https://docs.aws.amazon.com/deadline-cloud/latest/userguide/what-is-deadline-cloud.html
[deadline-cloud-client]: https://github.com/aws-deadline/deadline-cloud
[openjd]: https://github.com/OpenJobDescription/openjd-specifications/wiki
[openjd-adaptor-runtime]: https://github.com/OpenJobDescription/openjd-adaptor-runtime-for-python
[openjd-adaptor-runtime-lifecycle]: https://github.com/OpenJobDescription/openjd-adaptor-runtime-for-python/blob/release/README.md#adaptor-lifecycle

## Compatibility

This library requires:

1. 3ds Max 2024, 2025, 2026.
1. Python 3.10 or higher.
1. Windows operating system.

### Compatible Renderers

AWS Deadline Cloud officially supports rendering 3ds Max jobs using the following renderers:

* Autodesk Scanline 
* Autodesk Raytracer (ART) 
* Chaos Corona 
* Chaos V-Ray 6 (CPU & GPU)
* Chaos V-Ray 7 (CPU & GPU)
* Maxon Redshift
## Getting Started

This 3ds Max integration for AWS Deadline Cloud has two components that you will need to install:

1. The 3ds Max submitter plug-in must be installed on the workstation that you will use to submit jobs; and
2. The 3ds Max adaptor must be installed on all of your AWS Deadline Cloud worker hosts that will be running the 3ds Max jobs that you submit.

Before submitting any large, complex, or otherwise compute-heavy 3ds Max render jobs to your farm using the submitter and adaptor that you
set up, we strongly recommend that you construct a simple test scene that can be rendered quickly and submit renders of that
scene to your farm to ensure that your setup is correctly functioning.

## Submitter

The 3ds Max submitter plug-in creates a shelf button in your 3ds Max UI that can be used to submit jobs to AWS Deadline Cloud. Clicking this button
reveals a UI to create a job submission for AWS Deadline Cloud using the [AWS Deadline Cloud client library][deadline-cloud-client].
It automatically determines the files required based on the loaded scene, allows the user to specify render options, builds an
[Open Job Description template][openjd] that defines the workflow, and submits the job to the farm and queue of your choosing.

We are working on implementing a submitter installer for 3ds Max to automate the submitter installation. In the meantime, the submitter needs to be installed manually. To install the submitter follow the instructions [here](https://github.com/aws-deadline/deadline-cloud-for-3ds-max/blob/mainline/DEVELOPMENT.md#manual-installation).

## Adaptor

The 3ds Max Adaptor implements the [OpenJD][openjd-adaptor-runtime] interface that allows render workloads to launch 3ds Max and feed it commands. This gives the following benefits:
* a standardized render application interface,
* sticky rendering, where the application stays open between tasks,

Jobs created by the submitter use this adaptor by default, and require that both the installed adaptor
and the 3dsMax executable be available on the PATH of the user that will be running the jobs.

Alternatively, you can set the `3DSMAX_EXECUTABLE` environment variable to point to a 3dsMax executable.
The adaptor supports both `3dsmax` and `3dsmaxbatch`.

The adaptor can be installed by the standard python packaging mechanisms:
```sh
$ pip install deadline-cloud-for-3ds-max
```

After installation it can then be used as a command line tool:
```sh
$ 3dsmax-openjd --help
```

For more information on the commands the OpenJD adaptor runtime provides, see [here][openjd-adaptor-runtime-lifecycle].

## Versioning

This package's version follows [Semantic Versioning 2.0](https://semver.org/), but is still considered to be in its 
initial development, thus backwards incompatible versions are denoted by minor version bumps. To help illustrate how
versions will increment during this initial development stage, they are described below:

1. The MAJOR version is currently 0, indicating initial development. 
2. The MINOR version is currently incremented when backwards incompatible changes are introduced to the public API. 
3. The PATCH version is currently incremented when bug fixes or backwards compatible changes are introduced to the public API. 

## Security

See [CONTRIBUTING](https://github.com/aws-deadline/deadline-cloud-for-3ds-max/blob/release/CONTRIBUTING.md#security-issue-notifications) for more information.

## Telemetry

See [telemetry](https://github.com/aws-deadline/deadline-cloud-for-3ds-max/blob/release/docs/telemetry.md) for more information.

## License

This project is licensed under the Apache-2.0 License.
