# Jupyter Environments for DIVE

Welcome to the `jupyter` repository under the `dive4dec` organization! This repository contains the Makefile and Docker configurations to build and run Jupyter Docker images for the DIVE platform.

The images in this repository:

| Image | Purpose |
|-------|---------|
| `divenb` | The general-purpose DIVE notebook image (JupyterLab + VS Code in the browser + Chrome, Obsidian, MIT Scheme, ROOT, TeX, and more). Multiarch: `linux/amd64` and `linux/arm64`. |
| `cs1302nb`, `cs2310nb`, `cs5483nb`, ... | Course-specific notebook images. |
| `jhub` | The JupyterHub server image. |

## Prerequisites

Before you begin, ensure you have Docker with Buildx and container build support. Optionally, you may install QEMU for emulating different architectures for building multiarch images. For detailed instructions on setting up Docker Buildx and QEMU, see the [Docker documentation](https://docs.docker.com/build/building/multi-platform/).

## Use the `divenb` image from Docker Hub

If you only need to run the image, no build is required. The multiarch images are published to [Docker Hub](https://hub.docker.com/r/chungc/divenb):

```sh
docker pull chungc/divenb:0.2.83
docker run -it --rm -p 8888:8888 -p 8000:8000 chungc/divenb:0.2.83
```

Docker Hub resolves the tag to the correct architecture for the pulling host automatically (an `amd64` machine gets the `linux/amd64` image, an Apple Silicon machine gets `linux/arm64`).

List available versions and verify a tag is multiarch:

```sh
docker buildx imagetools inspect chungc/divenb:0.2.83
```

From this repository, the equivalent make commands are:

```sh
# Pull the latest published image
make docker-pull.divenb registry=chungc IMAGE_TAG=0.2.83

# Run it (exposes JupyterLab on 8888 and code-server on 8000)
make docker-run.divenb registry=chungc IMAGE_TAG=0.2.83
```

## Build a Docker Image

To build a Docker image (single architecture, the architecture of your machine), use:

```sh
make image.<image_variable>
```

For example, to build the `cs1302nb` image for the course [CS1302](ccha23.github.io/cs1302i24a/):

```sh
make image.cs1302nb
```

To build a specific version, use the `image-name^version` syntax (see [How the version tags work](#how-the-version-tags-work)):

```sh
make image.divenb^0.2.83
```

To build and publish a multiarch image in one step (cross-building with BuildKit/QEMU, requires the `container` buildx builder), see [Multiarch images](#multiarch-images) below.

## RUN a Docker image

To run a Docker image after it is built, use the following command:

```sh
make run-image.<image_variable>
```

This will run the Docker container and expose both the Jupyter notebook port (8888) and the JupyterHub port (8000). For example, to run the `cs1302nb` image:

```sh
make run-image.cs1302nb
```

## Multiarch images

A multiarch image is a single tag that contains one image per architecture, described by a manifest list. When a client pulls the tag, the registry serves the image matching the client's architecture, so the same pull command works on `linux/amd64` and `linux/arm64` machines.

### Option A: one machine cross-builds both arches

```sh
# Builds --platform linux/amd64,linux/arm64 and pushes the manifest list in one go
make public-image.divenb^0.2.83
```

This requires BuildKit with the `container` builder (created via `docker buildx create --name container --driver docker-container --use`) and QEMU for the non-native arch. The non-native half runs under emulation, so it is much slower than building natively.

### Option B: build each half on native hardware (recommended)

If you have a `linux/amd64` machine and a `linux/arm64` machine (e.g. an Apple Silicon Mac), you can build each half natively on its matching machine and stitch the two halves together afterwards. Both halves must be built from the **same commit** of this repository.

On the amd64 machine:

```sh
make image-amd64.divenb^0.2.83 registry=chungc
# pushes chungc/divenb:0.2.83-linux-amd64
```

On the arm64 machine:

```sh
make image-arm64.divenb^0.2.83 registry=chungc
# pushes chungc/divenb:0.2.83-linux-arm64
```

Then, from **either** machine (it is a pure registry operation, no image is built or pulled locally):

```sh
make image-stitch.divenb^0.2.83 registry=chungc
# creates the multiarch manifest chungc/divenb:0.2.83
```

Verify:

```sh
docker buildx imagetools inspect chungc/divenb:0.2.83
# should list both linux/amd64 and linux/arm64
```

Notes:

- The `-linux-amd64` / `-linux-arm64` tags are kept as the individual halves. They are also useful if a client needs to pin an architecture explicitly: `docker pull chungc/divenb:0.2.83-linux-arm64`.
- `docker login` is required on the building machine(s); `registry=chungc` targets `docker.io/chungc` (the default public registry).
- `image-stitch` uses `docker buildx imagetools create`, which only re-points a tag at existing manifests on the registry. It runs in seconds and works from any logged-in machine.

## Developer guide: how the Makefile works

### The image naming syntax

Every build target takes an `<image>^<version>[^<build-target>][^<dockerfile-suffix>]` argument, parsed by the `parse-image-info` rule:

```
divenb^0.2.83          ->  name=divenb  version=0.2.83
divenb^0.2.83^collab   ->  name=divenb  version=0.2.83  build-target=collab
divenb^0.2.83^^min     ->  name=divenb  version=0.2.83  dockerfile-suffix=min (Dockerfile.min)
```

The resulting tag is `version[-build-target][.dockerfile-suffix]`, so `divenb^0.2.83^collab` produces `divenb:0.2.83-collab` from `divenb/Dockerfile`, and `divenb^0.2.83^^min` produces `divenb:0.2.83.min` from `divenb/Dockerfile.min`.

If no version is given (`make image.divenb`), the tag is `latest`.

### How the version tags work

- The version is **always supplied on the command line** as the `^version` part of the target. The `divenb := divenb^0.2.83` line near the top of the Makefile is documentation of the current release, not an automatic default: `make docker-build.divenb` builds `divenb:latest`, while `make docker-build.divenb^0.2.83` builds `divenb:0.2.83`.
- When you cut a new release, bump the version on the command line and (optionally) update the `:=` line at the top of the Makefile to record the new release.
- BuildKit layer caching is shared across builds via the `$(FULL_IMAGE_NAME):cache1` tag (`--cache-from` / `--cache-to`), so rebuilding a version after a small Dockerfile change reuses layers.

### How multiarch images are created

There are two mechanisms:

1. **`docker-multiarch.%` / `public-image.%`** runs `docker buildx build --platform linux/amd64,linux/arm64 --push`. BuildKit builds both arches (the foreign one under QEMU emulation via the `container` builder) and pushes a single manifest list to the version tag in one step.
2. **`image-amd64.%` / `image-arm64.%` / `image-stitch.%`** build each half natively on a matching machine, pushing `<name>:<version>-linux-<arch>`, then `image-stitch.%` combines them with `docker buildx imagetools create` into a manifest list at `<name>:<version>`. Option 2 avoids emulation entirely and is the recommended workflow when both kinds of hardware are available.

In both cases the end result is identical: one version tag that is a manifest list with one entry per architecture.

### The `--build-context` flags

The `divenb` and `cs1302nb` Dockerfiles reference sibling repositories (e.g. `jupyter-ai-hermes`, `jupyterlab-pwa`) as named build contexts. The Makefile passes them as `--build-context <name>=../../<path>` pairs in `docker-build`, `docker-multiarch`, `image-amd64`, and `image-arm64`. These paths are relative to the image directory, so all four targets must be run from this repository root, with the sibling checkouts present (they are submodules of the parent `dive4dec/dive-deploy` repository).

## Make target reference

| Target | What it does |
|--------|--------------|
| `image.<img>^<ver>` | Build (native arch) and push if `registry` is set |
| `public-image.<img>^<ver>` | Cross-build both arches and push the multiarch manifest (registry `chungc`) |
| `public-image-as-latest.<img>^<ver>` | Same as above, tag `latest` |
| `image-amd64.<img>^<ver> registry=...` | Build + push the `linux/amd64` half as `<img>:<ver>-linux-amd64` |
| `image-arm64.<img>^<ver> registry=...` | Build + push the `linux/arm64` half as `<img>:<ver>-linux-arm64` |
| `image-stitch.<img>^<ver> registry=...` | Stitch the two halves into the multiarch `<img>:<ver>` tag (registry-only, fast) |
| `docker-build.<img>^<ver>` | Build locally only (no push) |
| `docker-pull.<img>^<ver>` | Pull from the registry |
| `docker-run.<img>^<ver>` | Run a container (8888 + 8000, mounts `./` at `/home/jovyan/work`) |
| `run-image.<img>^<ver>` | `docker-run` of the locally built image |
| `image-info.<img>^<ver>` | Print the parsed image name/tag/version/Dockerfile without building |

For more details of the other make commands, see the [Makefile](./Makefile).
