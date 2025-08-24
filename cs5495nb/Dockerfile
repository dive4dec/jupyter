FROM quay.io/jupyter/scipy-notebook:python-3.12

# Fix: https://github.com/hadolint/hadolint/wiki/DL4006
# Fix: https://github.com/koalaman/shellcheck/wiki/SC3014
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

USER root
### code-server ###
RUN wget -q https://code-server.dev/install.sh -O /tmp/install.sh && \
    sh /tmp/install.sh --version 4.96.2 && \
    fix-permissions "${HOME}" && \
    fix-permissions /usr/lib/code-server/ && \
    rm -rf ~/.cache/code-server/ && \
    rm -rf /tmp/install.sh

USER ${NB_UID}

RUN mamba install -c conda-forge --yes \
    'black' \
    'isort' \
    'nbgitpuller' \
    'jupyter-resource-usage' \
    'jupyter-vscode-proxy' \
    'jupyterlab_code_formatter' \
    'jupyterlab_execute_time' \
    'numpy<2.0.0' \
    && \
    mamba clean --all -f -y && \
    fix-permissions "${CONDA_DIR}" && \
    fix-permissions "/home/${NB_USER}"

RUN pip install --no-cache-dir \
    'torch' \
    'torch-tensorrt' \
    'torchvision' \
    'torchaudio' \
    'xgboost' \
    'shap' \
    'lime' \
    'captum' \
    'eli5' \
    'xgboost' \
    && \
    fix-permissions "${CONDA_DIR}" && \
    fix-permissions "/home/${NB_USER}"

# DIVE AI
RUN \
    mamba install -c conda-forge --yes \
    'jupyter-ai=2.31.*' \
    'gh' \
    'langchain' \
    'langchain-openai' \
    'langchain-community' \
    && \
    pip install --quiet --no-cache-dir \
    'git+https://github.com/dive4dec/dive_ai@3b9e78f5adaa7c633c8eaf5c0ae392b1627683d6#subdirectory=dive_ai' && \
    mamba clean --all -f -y && \    
    fix-permissions "${CONDA_DIR}"

COPY install-vscode-extension /usr/local/bin/

# Code extensions
RUN for ext in \
        ms-python.python \
        ms-python.pylint \
        ms-toolsai.jupyter \
        ms-toolsai.vscode-jupyter-powertoys \
        ms-python.black-formatter \
        ; do \
        code-server --extensions-dir /usr/lib/code-server/lib/vscode/extensions --install-extension "$ext"; \
    done

RUN for ext in \
    GitHub.copilot-chat@0.30.2 \
    GitHub.copilot@1.350.0 \
    Continue.continue@1.0.24 \
    ms-vsliveshare.vsliveshare@1.0.5857 \
    ; do \
    install-vscode-extension "$ext" --extensions-dir /usr/lib/code-server/lib/vscode/extensions; \
    done

# IPython config for AiMagics
COPY --chown=${NB_USER}:${NB_GID} ipython_config.py "${CONDA_DIR}/etc/ipython/ipython_config.py"

# USER jovyan
ENV TF_USE_LEGACY_KERAS=1
ENV XLA_FLAGS=--xla_gpu_cuda_data_dir=${CONDA_DIR}/lib
ENV LD_LIBRARY_PATH="/opt/conda/lib/:${CONDA_DIR}/lib/python3.12/site-packages/nvidia/cudnn/lib/:${CONDA_DIR}/lib/python3.12/site-packages/tensorrt_libs/:${CONDA_DIR}/lib/python3.12/site-packages/nvidia/cufft/lib/:${CONDA_DIR}/lib/python3.12/site-packages/nvidia/cusolver/lib/:${CONDA_DIR}/lib/python3.12/site-packages/nvidia/cusparse/lib/"