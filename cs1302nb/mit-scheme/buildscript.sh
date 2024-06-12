#!/bin/sh
# See: https://groups.csail.mit.edu/mac/users/gjs/6946/installation.html

set -e

SCHEME_VERSION=12.1
SCMUTILS_VERSION=20230902
SRC=/tmp/src
mkdir -p /tmp/src

apt-get update --yes
apt-get install --yes --no-install-recommends wget make gcc m4 autotools-dev libssl-dev libncurses5-dev libx11-dev libxt-dev libltdl-dev

wget "https://ftp.gnu.org/gnu/mit-scheme/stable.pkg/${SCHEME_VERSION}/mit-scheme-${SCHEME_VERSION}-x86-64.tar.gz" -O "${SRC}/mit-scheme-${SCHEME_VERSION}.tar.gz"
wget "https://groups.csail.mit.edu/mac/users/gjs/6946/mechanics-system-installation/native-code/scmutils-${SCMUTILS_VERSION}.tar.gz" -O "${SRC}/scmutils-${SCMUTILS_VERSION}.tar.gz"

# Compile mit-scheme
cd ${SRC}
tar xzf mit-scheme-${SCHEME_VERSION}.tar.gz
rm mit-scheme-${SCHEME_VERSION}.tar.gz
cd mit-scheme-${SCHEME_VERSION}/src
./configure
make
make install
# # Compile documentation
# apt-get install --yes --no-install-recommends wget make gcc texinfo ghostscript
# cd ../doc
# ./configure
# make
# # Install documentation
# make install-info install-html install-pdf

# Install scmutils
cd ${SRC}
tar xzf scmutils-${SCMUTILS_VERSION}.tar.gz
rm scmutils-${SCMUTILS_VERSION}.tar.gz
cd scmutils-${SCMUTILS_VERSION}
./install.sh
cp mechanics.sh /usr/local/bin/mechanics

# # Install kernel
# apt-get install --yes --no-install-recommends pkg-config libzmq3-dev
# git clone https://github.com/joeltg/mit-scheme-kernel
# cd mit-scheme-kernel
# make -e AUXDIR=/usr/local/lib/mit-scheme-x86-64-${SCHEME_VERSION}
# mkdir -p /usr/local/share/jupyter/kernels
# make install -e AUXDIR=/usr/local/lib/mit-scheme-x86-64-${SCHEME_VERSION}