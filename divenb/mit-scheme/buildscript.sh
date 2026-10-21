#!/bin/sh
# Installation script for MIT Scheme and scmutils
# Reference: https://groups.csail.mit.edu/mac/users/gjs/6946/installation.html

set -euxo pipefail

# Ensure the script is run as root
if [ "$(id -u)" -ne 0 ]; then
  echo "This script must be run as root."
  exit 1
fi

# Define versions
SCHEME_VERSION=12.1
SCMUTILS_VERSION=20230902

# Arch-aware MIT Scheme tarball. The GNU mirror publishes a prebuilt-source
# tarball per architecture (mit-scheme-<ver>-<arch>.tar.gz); the x86-64
# tarball's microcode is x86 assembly, so building it on linux/arm64 fails with
# "unknown mnemonic". Map the build arch to GNU's tarball label, mirroring the
# arch-aware pattern used for Chrome/Obsidian in the Dockerfile (3d8c1b7).
case "$(dpkg --print-architecture)" in
  amd64)   SCHEME_ARCH=x86-64 ;;
  arm64)   SCHEME_ARCH=aarch64le ;;
  *)       echo "Unsupported architecture for MIT Scheme: $(dpkg --print-architecture)"; exit 1 ;;
esac

# Create a unique temporary directory
SRC=$(mktemp -d)
trap "rm -rf ${SRC}" EXIT

echo "Temporary source directory created at ${SRC}"

# Update package list and install dependencies
echo "Installing required packages..."
apt-get update --yes
apt-get install --yes --no-install-recommends \
  wget \
  make \
  gcc \
  m4 \
  autotools-dev \
  libssl-dev \
  libncurses5-dev \
  libx11-dev \
  libxt-dev \
  libltdl-dev

# Download MIT Scheme and scmutils
echo "Downloading MIT Scheme..."
wget --quiet "https://ftp.gnu.org/gnu/mit-scheme/stable.pkg/${SCHEME_VERSION}/mit-scheme-${SCHEME_VERSION}-${SCHEME_ARCH}.tar.gz" -O "${SRC}/mit-scheme-${SCHEME_VERSION}.tar.gz"
echo "Downloading scmutils..."
wget --quiet "https://groups.csail.mit.edu/mac/users/gjs/6946/mechanics-system-installation/native-code/scmutils-${SCMUTILS_VERSION}.tar.gz" -O "${SRC}/scmutils-${SCMUTILS_VERSION}.tar.gz"

# Verify downloads
if [ ! -s "${SRC}/mit-scheme-${SCHEME_VERSION}.tar.gz" ] || [ ! -s "${SRC}/scmutils-${SCMUTILS_VERSION}.tar.gz" ]; then
  echo "Download failed or files are empty."
  exit 1
fi

# Compile MIT Scheme
echo "Compiling MIT Scheme..."
pushd "${SRC}"
tar xzf mit-scheme-${SCHEME_VERSION}.tar.gz
rm mit-scheme-${SCHEME_VERSION}.tar.gz
pushd mit-scheme-${SCHEME_VERSION}/src
./configure
# GCC 15 + glibc 2.41 (Ubuntu 26.04): MIT Scheme 12.1 redefines _POSIX_C_SOURCE
# which conflicts with glibc's new 202405L value. The Makefile uses -Werror,
# so the redefinition warning becomes a fatal error. Disable -Werror to fix.
make CFLAGS="-Wno-error"
make install
popd
popd

# Install scmutils
echo "Installing scmutils..."
pushd "${SRC}"
tar xzf scmutils-${SCMUTILS_VERSION}.tar.gz
rm scmutils-${SCMUTILS_VERSION}.tar.gz
pushd scmutils-${SCMUTILS_VERSION}
./install.sh
cp mechanics.sh /usr/local/bin/mechanics
popd
popd

echo "Installation completed successfully."
