FROM jupyter/scipy-notebook:python-3.11

LABEL maintainer="Jupyter Project <jupyter@googlegroups.com>"

# Fix: https://github.com/hadolint/hadolint/wiki/DL4006
# Fix: https://github.com/koalaman/shellcheck/wiki/SC3014
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Install Tensorflow with pip
RUN pip install --no-cache-dir \
    'xgboost' \
    && \
    mamba install -c conda-forge --yes \
    'black' \
    'code-server' \
    'nbgitpuller' \
    'isort' \
    'jupyter-resource-usage' \
    'jupyter-vscode-proxy' \
    'jupyterlab_code_formatter' \
    'jupyterlab_execute_time' \
    && \
    mamba clean --all -f -y && \
    fix-permissions "${CONDA_DIR}" && \
    fix-permissions "/home/${NB_USER}"

RUN pip install --no-cache-dir --timeout=120 \
    'tensorflow[and-cuda]==2.16.1' \
    'tensorrt==8.6.1' \
    && \
    # Link libdevice file to the required path
    mkdir -p "${CONDA_DIR}/lib/" && \
    ln -s ${CONDA_DIR}/nvvm/ ${CONDA_DIR}/lib/nvvm && \
    fix-permissions "${CONDA_DIR}" && \
    fix-permissions "/home/${NB_USER}"

RUN ln -s /opt/conda/lib/python3.11/site-packages/tensorrt_libs/libnvinfer.so.8 /opt/conda/lib/python3.11/site-packages/tensorrt_libs/libnvinfer.so.8.6.1 && \
    ln -s /opt/conda/lib/python3.11/site-packages/tensorrt_libs/libnvinfer_plugin.so.8 /opt/conda/lib/python3.11/site-packages/tensorrt_libs/libnvinfer_plugin.so.8.6.1

# RUN pip install --no-cache-dir \
#     'torch' \
#     'torch-tensorrt' \
#     'tensorrt' \
#     'torchvision' \
#     'torchaudio' \
#     && \
#     fix-permissions "${CONDA_DIR}" && \
#     fix-permissions "/home/${NB_USER}"

# USER root
# RUN apt update && apt upgrade --yes
# RUN echo "#1000    ALL=(ALL:ALL) NOPASSWD:ALL" >> /etc/sudoers.d/user

USER jovyan
ENV XLA_FLAGS=--xla_gpu_cuda_data_dir=${CONDA_DIR}/lib
ENV LD_LIBRARY_PATH="/opt/conda/lib/:${CONDA_DIR}/lib/python3.11/site-packages/nvidia/cudnn/lib/:${CONDA_DIR}/lib/python3.11/site-packages/tensorrt_libs/:${CONDA_DIR}/lib/python3.11/site-packages/nvidia/cufft/lib/:${CONDA_DIR}/lib/python3.11/site-packages/nvidia/cusolver/lib/:${CONDA_DIR}/lib/python3.11/site-packages/nvidia/cusparse/lib/"
