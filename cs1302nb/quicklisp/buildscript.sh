#!/bin/sh

# This script installs Quicklisp and sets up the Maxima-Jupyter kernel for use in Jupyter notebooks.
# It assumes SBCL and Maxima are already installed, and it configures the kernel to run inside a Conda environment.

set -euxo pipefail

# Install Quicklisp
echo "Installing Quicklisp..."
curl -sSL -o /tmp/quicklisp.lisp https://beta.quicklisp.org/quicklisp.lisp
sbcl --non-interactive --load /tmp/quicklisp.lisp \
     --eval '(quicklisp-quickstart:install :path "/opt/quicklisp/ql")'

# Optional: move sbclrc if needed
if [ -f /tmp/quicklisp/sbclrc ]; then
    mv /tmp/quicklisp/sbclrc /etc/
fi

# Clone Maxima-Jupyter
echo "Cloning Maxima-Jupyter..."
cd /tmp
git clone https://github.com/dive4dec/maxima-jupyter.git
cd maxima-jupyter

# Install Maxima-Jupyter kernel
echo "Installing Maxima-Jupyter kernel..."
maxima --batch-string='load("load-maxima-jupyter.lisp"); jupyter_system_install(true, "pkg/");'

# Patch kernel.json to use correct path
echo "Patching kernel.json..."
perl -pi -e 's`/usr/local`/opt/conda`g' pkg/usr/local/share/jupyter/kernels/maxima/kernel.json

# Move kernel and support files
echo "Finalizing installation..."
mkdir -p ${CONDA_DIR}/share/jupyter/kernels/
mv pkg/usr/local/share/jupyter/kernels/maxima ${CONDA_DIR}/share/jupyter/kernels/
mv pkg/usr/local/share/maxima-jupyter ${CONDA_DIR}/share/

# Test kernel startup
echo "Testing Maxima-Jupyter kernel..."
maxima --very-quiet \
    --preload-lisp=${CONDA_DIR}/share/maxima-jupyter/bundle.lisp \
    --preload-lisp=${CONDA_DIR}/share/maxima-jupyter/local-projects/maxima-jupyter/load-maxima-jupyter.lisp \
    --batch-string='jupyter_kernel_start("examples/MaximaJupyterExample.ipynb")$'

# Fix permissions
fix-permissions "/opt/quicklisp"
