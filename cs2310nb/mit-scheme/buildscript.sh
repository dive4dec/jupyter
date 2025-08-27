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
wget --quiet "https://ftp.gnu.org/gnu/mit-scheme/stable.pkg/${SCHEME_VERSION}/mit-scheme-${SCHEME_VERSION}-x86-64.tar.gz" -O "${SRC}/mit-scheme-${SCHEME_VERSION}.tar.gz"
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
make
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
