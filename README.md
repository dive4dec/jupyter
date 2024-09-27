# Jupyter Environments for DIVE

Welcome to the `jupyter` repository under the `dive4dec` organization! This repository contains the Makefile and Docker configurations to build and run Jupyter Docker images for the DIVE platform.

## Prerequisites

Before you begin, ensure you have Docker with Buildx and container build support. Optionally, you may install QEMU for emulating different architectures for building multiarch images. For detailed instructions on setting up Docker Buildx and QEMU, see the [Docker documentation](https://docs.docker.com/build/building/multi-platform/).


## Build a Docker Image

To build a Docker image, use the following command:

```sh
make image.<image_variable>
```

For example, to build the `cs1302nb` image for the course [CS1302](ccha23.github.io/cs1302i24a/):

```sh
make image.cs1302nb
```

## RUN a Docker image

To run a Docker image after it is built, use the following command:

```sh
make run-image.<image_variable>
```

This will run the Docker container and expose both the Jupyter notebook port (8888) and the JupyterHub port (8000). For example, to run the `cs1302nb` image:

```sh
make run-image.cs1302nb
```

For more details of the other make commands, see the [Makefile](./Makefile).
