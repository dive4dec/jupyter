#!/bin/sh
# Adapted from https://github.com/mathinstitut/goemaxima/blob/master/buildscript.sh
# ---
# This script build SBCL and Maxima from source.

## Comment out due to some issue building the documentation.
# set -euxo pipefail

# Ensure script is run as root
if [ "$(id -u)" -ne 0 ]; then
    echo "Please run as root."
    exit 1
fi

# Create temporary source directory
SRC=$(mktemp -d)
trap "rm -rf $SRC" EXIT

MAXIMA_VERSION=5.44.0
SBCL_VERSION=2.5.7

echo "Installing build dependencies..."
apt-get update --yes
apt-get install --yes --no-install-recommends \
    wget make gcc

echo "Downloading Maxima and SBCL sources..."
wget --quiet "https://github.com/mathinstitut/maxima-mirror/releases/download/${MAXIMA_VERSION}/maxima-${MAXIMA_VERSION}.tar.gz" -O "${SRC}/maxima-${MAXIMA_VERSION}.tar.gz"
wget --quiet "https://github.com/sbcl/sbcl/archive/refs/tags/sbcl-${SBCL_VERSION}.tar.gz" -O "${SRC}/sbcl-${SBCL_VERSION}.tar.gz"

echo "Bootstrapping and compiling SBCL..."
apt-get install -y sbcl
pushd "${SRC}"
tar -xzf sbcl-${SBCL_VERSION}.tar.gz
rm sbcl-${SBCL_VERSION}.tar.gz
pushd sbcl-sbcl-${SBCL_VERSION}
echo "\"${SBCL_VERSION}"\" > version.lisp-expr
./make.sh
apt-get remove -y sbcl
./install.sh
popd
popd

echo "Compiling Maxima..."
pushd "${SRC}"
tar -xf maxima-${MAXIMA_VERSION}.tar.gz
rm maxima-${MAXIMA_VERSION}.tar.gz
pushd maxima-${MAXIMA_VERSION}
./configure
make
make install
make clean
popd
popd

echo "Build and installation complete."
