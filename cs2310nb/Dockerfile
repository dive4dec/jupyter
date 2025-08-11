ARG ROOT_CONTAINER=ubuntu:24.04

FROM $ROOT_CONTAINER AS foundation

# Avoid prompt for user input for installation of dependencies
ENV DEBIAN_FRONTEND=noninteractive

ARG NB_USER="jovyan"
ARG NB_UID="1000"
ARG NB_GID="100"
ARG CONDA_DIR=/opt/conda
ENV CONDA_DIR=${CONDA_DIR} \
    SHELL=/bin/bash \
    NB_USER="${NB_USER}" \
    NB_UID=${NB_UID} \
    NB_GID=${NB_GID} \
    LC_ALL=C.UTF-8 \
    LANG=C.UTF-8 \
    LANGUAGE=C.UTF-8 \
    TZ=Asia/Hong_Kong \
    HOME="/home/${NB_USER}" \
    PATH="${CONDA_DIR}/bin:${PATH}"

# Fix: https://github.com/hadolint/hadolint/wiki/DL4006
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Use system bashrc since /home/jovyan is temporary
RUN mv /etc/skel/.bashrc /etc/bash.bashrc && \
    # Enable prompt color in the skeleton .bashrc before creating the default NB_USER
    # hadolint ignore=SC2016
    sed -i 's/^#force_color_prompt=yes/force_color_prompt=yes/' /etc/bash.bashrc

# Fix the UID conflict with user ubuntu
# See https://bugs.launchpad.net/cloud-images/+bug/2005129
RUN touch /var/mail/ubuntu && chown ubuntu /var/mail/ubuntu && userdel -r ubuntu && \
    useradd -l -m -s /bin/bash -N -u "${NB_UID}" "${NB_USER}"

USER root
FROM foundation AS base

RUN apt-get update --yes && \
    # Patch newly discovered vulnerabilities in apt-get packages
    apt-get upgrade --yes && \
    apt-get install --yes --no-install-recommends \
    # To extract micromamba
    bzip2 \
    ca-certificates \
    locales \
    sudo \
    # used as an entrypoint that reaps zombie processes.
    # See https://github.com/krallin/tini#why-tini
    tini \
    wget \
    less \
    curl \
    && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

RUN echo "en_US.UTF-8 UTF-8" > /etc/locale.gen && \
    echo "C.UTF-8 UTF-8" >> /etc/locale.gen && \
    locale-gen && \
    ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Install all OS dependencies
RUN apt-get update --yes && \
    apt-get install --yes --no-install-recommends \
    fonts-liberation \
    # To convert notebooks to html files
    pandoc \
    # A wrapper script that runs no more
    # to support `RESTARTABLE` option
    run-one \
    # Common useful utilities
    git \
    nano-tiny \
    tzdata \
    unzip \
    vim-tiny \
    # git-over-ssh
    openssh-client \
    # nbconvert dependencies
    # See https://nbconvert.readthedocs.io/en/latest/install.html#installing-tex
    texlive-xetex \
    texlive-fonts-recommended \
    texlive-plain-generic \
    dvisvgm \
    # Enable clipboard on Linux host systems
    xclip && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Dependencies for mystmd
RUN \
    apt-get update --yes && \
    apt-get install --yes --no-install-recommends \
    latexmk \
    biber \
    lmodern \
    && \
    paperconfig -p a4 \
    && \
    apt-get clean && rm -rf /var/lib/apt/lists/*


# Desktop
RUN \
    apt-get update --yes && \
    apt-get install --yes --no-install-recommends \
    gpg \
    software-properties-common \
    emacs \    
    thonny \
    dbus-x11 \
    xfce4 \
    xfce4-panel \
    xfce4-session \
    xfce4-settings \
    xorg \
    xubuntu-icon-theme \
    x11-utils \
    xfonts-base \
    xvfb \
    && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Install VS Code
RUN wget -qO- https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > microsoft.gpg && \
    install -o root -g root -m 644 microsoft.gpg /etc/apt/trusted.gpg.d/ && \
    sh -c 'echo "deb [arch=$(dpkg --print-architecture)] https://packages.microsoft.com/repos/vscode stable main" > /etc/apt/sources.list.d/vscode.list' && \
    apt-get install -y apt-transport-https && \
    apt-get update --yes && \
    apt-get install --yes code && \
    apt-get clean && rm -rf /var/lib/apt/lists/* microsoft.gpg


# Install Firefox Nightly
RUN add-apt-repository ppa:ubuntu-mozilla-daily/ppa && \
    apt-get update --yes && \
    apt-get install --yes firefox-trunk && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Modify code.desktop to include --no-sandbox
RUN sed -i 's|Exec=/usr/share/code/code|Exec=/usr/share/code/code --no-sandbox|' /usr/share/applications/code.desktop && \
    sed -i 's|Exec=firefox-trunk|Exec=firefox-trunk --no-sandbox|' /usr/share/applications/firefox-trunk.desktop

# Add alias to /etc/bash.bashrc to include --no-sandbox
RUN cat <<EOF >> /etc/bash.bashrc
alias code='code --no-sandbox'
alias firefox-trunk='firefox-trunk --no-sandbox'
alias firefox='firefox-trunk --no-sandbox'
EOF

# Create a wrapper script for Firefox nightly with --no-sandbox
RUN echo -e '#!/bin/bash\nexec /usr/bin/firefox-trunk --no-sandbox "$@"' > /usr/local/bin/firefox-trunk-no-sandbox && \
    chmod +x /usr/local/bin/firefox-trunk-no-sandbox && \
    # Set Firefox nightly as the default browser with --no-sandbox
    update-alternatives --install /usr/bin/x-www-browser x-www-browser /usr/local/bin/firefox-trunk-no-sandbox 200 && \
    update-alternatives --set x-www-browser /usr/local/bin/firefox-trunk-no-sandbox && \
    update-alternatives --install /usr/bin/gnome-www-browser gnome-www-browser /usr/local/bin/firefox-trunk-no-sandbox 200 && \
    update-alternatives --set gnome-www-browser /usr/local/bin/firefox-trunk-no-sandbox

# Install TurboVNC based on the current architecture
RUN ARCH=$(dpkg --print-architecture) && \
    wget -q "https://github.com/TurboVNC/turbovnc/releases/download/3.2/turbovnc_3.2_${ARCH}.deb" -O /tmp/turbovnc.deb && \
    apt-get update --yes && \
    apt-get install --yes --no-install-recommends /tmp/turbovnc.deb && \
    rm /tmp/turbovnc.deb && \
    ln -s /opt/TurboVNC/bin/* /usr/local/bin/ && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Programming languages backends
RUN \
    apt-get update --yes && \
    apt-get install --yes --no-install-recommends \
    build-essential \
    cmake \
    ninja-build \
    # Java
    default-jdk default-jre \
    # C, C++
    gdb \
    fpc-source \
    # SQL
    sqlite3 \
    pdf2svg \
    && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# For installing some jupyter kernels
RUN apt-get update --yes && \
    apt-get install --yes --no-install-recommends libzmq3-dev

# A script to correct permissions after running certain commands
COPY fix-permissions /usr/local/bin/fix-permissions
RUN chmod a+rx /usr/local/bin/fix-permissions

# Make sure these dirs are writable by the `users` group.
RUN echo "auth requisite pam_deny.so" >> /etc/pam.d/su && \
    sed -i.bak -e 's/^%admin/#%admin/' /etc/sudoers && \
    sed -i.bak -e 's/^%sudo/#%sudo/' /etc/sudoers && \
    mkdir -p "${CONDA_DIR}" && \
    chown "${NB_USER}:${NB_GID}" "${CONDA_DIR}" && \
    chmod g+w /etc/passwd && \
    fix-permissions "${HOME}" && \
    fix-permissions "${CONDA_DIR}"

USER ${NB_UID}

# Pin python version here, or leave it empty for the latest version
ARG PYTHON_VERSION=3.12

# Pin micromamba version here, or leave it empty for the latest version
ARG MICROMAMBA_VERSION=2.3.0-1

# Download and install Micromamba, and initialize Conda prefix.
#   <https://github.com/mamba-org/mamba#micromamba>
# Install Python, Mamba and jupyter_core
COPY --chown="${NB_UID}:${NB_GID}" initial-condarc "${CONDA_DIR}/.condarc"
WORKDIR /tmp
RUN set -x && \
    # Computing artifact location
    case "$(uname)" in \
      Linux) \
        PLATFORM="linux" ;; \
      Darwin) \
        PLATFORM="osx" ;; \
      *NT*) \
        PLATFORM="win" ;; \
    esac && \
    ARCH="$(uname -m)" && \
    case "$ARCH" in \
      aarch64|ppc64le|arm64) \
          ;; \
      *) \
        ARCH="64" ;; \
    esac && \
    case "$PLATFORM-$ARCH" in \
        linux-aarch64|linux-ppc64le|linux-64|osx-arm64|osx-64|win-64) \
            ;; \
        *) \
        echo "Failed to detect your OS" >&2 && \
        exit 1 ;; \
    esac && \
    if [ "${MICROMAMBA_VERSION:-}" = "" ]; then \
        RELEASE_URL="https://github.com/mamba-org/micromamba-releases/releases/latest/download/micromamba-${PLATFORM}-${ARCH}" ; \
    else \
        RELEASE_URL="https://github.com/mamba-org/micromamba-releases/releases/download/${MICROMAMBA_VERSION}/micromamba-${PLATFORM}-${ARCH}" ; \
    fi && \
    BIN_FOLDER="${CONDA_DIR}/bin" && \
    mkdir -p "${BIN_FOLDER}" && \
    curl "${RELEASE_URL}" -o "${BIN_FOLDER}/micromamba" -fsSL --compressed && \
    chmod +x "${BIN_FOLDER}/micromamba" && \
    ln -s ${BIN_FOLDER}/micromamba ${BIN_FOLDER}/mamba && \
    ln -s ${BIN_FOLDER}/micromamba ${BIN_FOLDER}/conda

# Set MAMBA_ROOT_PREFIX environment variable for the Docker build process and runtime
ENV MAMBA_ROOT_PREFIX=${CONDA_DIR}

USER root

# Add call to micromamba init script
RUN cat <<'EOF' >> /etc/bash.bashrc
eval "$(mamba shell hook --shell bash)"
alias conda="micromamba"
alias mamba="micromamba"
mamba activate
EOF

# Install CUDA Toolkit
RUN ARCH=$(dpkg --print-architecture) && \
    if [ "$ARCH" = "amd64" ]; then \
        wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2404/x86_64/cuda-ubuntu2404.pin && \
        mv cuda-ubuntu2404.pin /etc/apt/preferences.d/cuda-repository-pin-600 && \
        wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2404/x86_64/3bf863cc.pub && \
        gpg --dearmor -o /usr/share/keyrings/cuda-archive-keyring.gpg 3bf863cc.pub && \
        echo "deb [signed-by=/usr/share/keyrings/cuda-archive-keyring.gpg] https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2404/x86_64/ /" > /etc/apt/sources.list.d/cuda.list && \
        apt-get update && \
        apt-get install --yes cuda-toolkit-12-8 && \
        rm -rf /var/lib/apt/lists/* 3bf863cc.pub; \
    else \
        echo "Skipping CUDA installation: unsupported architecture ($ARCH)"; \
    fi



USER ${NB_UID}

RUN if [ "${PYTHON_VERSION:-}" = "" ]; then PYTHON_SPECIFIER="python"; else PYTHON_SPECIFIER="python=${PYTHON_VERSION}"; fi && \
        mamba install --yes \
        "${PYTHON_SPECIFIER}" \
        && \
        # Pin major.minor version of python
        mkdir -p "${CONDA_DIR}/conda-meta" && \
        mamba list python | sed 's/^[[:space:]]*//' | grep '^python ' | tr -s ' ' | cut -d ' ' -f 1,2 >> "${CONDA_DIR}/conda-meta/pinned" && \
        mamba clean --all -f -y && \
        fix-permissions "${CONDA_DIR}" && \
        fix-permissions "/home/${NB_USER}"

# Fix compatibility issues with AI tools
RUN echo "packaging<25" >> "${CONDA_DIR}/conda-meta/pinned"

# Tensorflow
RUN pip install --quiet --no-cache-dir \
    'tensorflow==2.19.*' \
    && \
    fix-permissions "${CONDA_DIR}"

# PyTorch
RUN ARCH=$(dpkg --print-architecture) && \
    PIP_INDEX="" && \
    [ "$ARCH" = "amd64" ] && PIP_INDEX="--index-url https://download.pytorch.org/whl/cu128"; \
    pip install --quiet --no-cache-dir \
        'torch==2.7.*' \
        'torchvision==0.22.*' \
        'torchaudio==2.7.*' \
        $PIP_INDEX && \
    fix-permissions "${CONDA_DIR}"


# Install Jupyter Notebook, Lab, and Hub
RUN \
    mamba install --yes --quiet \
    # code-server requirement
    'nodejs==24.4.*' \
    'jupyterlab==4.4.*' \
    'notebook==7.4.*' \
    'jupyterhub==5.3.*' \
    && \
    # jupyter notebook --generate-config && \
    mamba clean --all -f -y && \
    npm cache clean --force && \
    jupyter lab clean && \
    fix-permissions "${CONDA_DIR}" && \
    fix-permissions "/home/${NB_USER}"

ENV JUPYTER_PORT=8888
EXPOSE $JUPYTER_PORT

USER root

### code-server ###
RUN wget -q https://code-server.dev/install.sh -O /tmp/install.sh && \
    sh /tmp/install.sh --version 4.101.2 && \
    fix-permissions "${HOME}" && \
    fix-permissions /usr/lib/code-server/ && \
    rm -rf ~/.cache/code-server/ && \
    rm -rf /tmp/install.sh

### Clang ###
# See https://apt.llvm.org/
RUN wget https://apt.llvm.org/llvm.sh && \
    chmod +x llvm.sh && \
    sudo ./llvm.sh 20 all && \
    rm -rf llvm.sh && \
    for cmd in $(dpkg -L clang-format-20 clang-tidy-20 clang-20 clangd-20 lld-20 lldb-20 llvm-20 | grep '^/usr/bin/.*-20$'); do \
      base=$(basename "$cmd"); \
      base=${base%-20}; \
      update-alternatives --install "/usr/bin/$base" "$base" "$cmd" 200; \
    done

USER ${NB_UID}

# Programming languages support
RUN \
    mamba install --quiet --yes \
    # Java
    'openjdk=23.0.*' \
    'ant=1.10.*' \
    # Documentations
    'jupyterlab-myst=2.4.*' \
    'jupyterlite=0.6.*' \
    'nbdev=2.4.*' \
    'jupyterlite-sphinx=0.20.*' \ 
    && \
    pip install --quiet --no-cache-dir \
    'calysto-scheme==1.4.*' \
    # Documentations
    'jupyterlab-quarto==0.3.*' \
    && \
    # scheme kernel
    python -m calysto_scheme install --sys-prefix && \
    # Java kernel
    wget 'https://github.com/SpencerPark/IJava/releases/download/v1.3.0/ijava-1.3.0.zip' \
    -O /tmp/ijava.zip && \
    unzip /tmp/ijava.zip -d /tmp/ijava && \
    python /tmp/ijava/install.py --sys-prefix && \
    rm -rf /tmp/ijava \
    && \
    mamba clean --all -f -y && \
    fix-permissions "${CONDA_DIR}" && \
    npm cache clean --force

# Other packages needed by the course
RUN mamba install --quiet --yes \
    'manim=0.19.*' \
    'manimpango=0.6.*' \
    'pandas=2.2.*' \
    'matplotlib-base=3.10.*' \
    'ipympl=0.9.*' \
    'sympy=1.14.*' \
    && \
    mamba clean --all -f -y && \
    fix-permissions "${CONDA_DIR}"

RUN mamba install --quiet --yes \
    'websockify=0.13.*' \
    'jupyter-vscode-proxy=0.6' \
    'jupytext=1.17.*' \
    'black=25.1.*' \
    'jupyterlab_code_formatter=3.0.*' \
    'jupyterlab-lsp=5.1.*' \
    'jupyter-resource-usage=1.1.*' \
    'nbgitpuller==1.2.*' \
    'jupyterlab-git==0.51.*' \
    && \
    pip install --quiet --no-cache-dir \
    # 'jupyterlab_filesystem_access==0.6.*' \
    'python-lsp-server[all]==1.12.*' \
    # 'clangd==20.1.*' \
    # 'clang-format==20.1.*' \
    'astyle==3.6.*' \
    'jupyter-www-proxy' \
    && \
    # See https://jupyterlab-lsp.readthedocs.io/en/latest/Language%20Servers.html#example-getting-all-the-node-js-based-language-servers
    npm install -g --save-dev  \
    bash-language-server \
    dockerfile-language-server-nodejs \
    pyright \
    sql-language-server \
    typescript-language-server \
    unified-language-server \
    vscode-css-languageserver-bin \
    vscode-html-languageserver-bin \
    vscode-json-languageserver-bin \
    yaml-language-server \
    && \
    npm cache clean --force && \
    mamba clean --all -f -y && \
    fix-permissions "${CONDA_DIR}"

# Documentations with MyST
RUN \
    npm install -g \
    mystmd@1.5.1 \
    && \
    npm cache clean --force


RUN pip install --quiet --no-cache-dir \
    'jupyter-remote-desktop-proxy==3.0.*' \
    # git+https://github.com/b-data/jupyter-remote-desktop-proxy.git@QGIS \
    && \
    mamba clean --all -f -y && \
    fix-permissions "${CONDA_DIR}"


# Support virtual environments in jupyter notebook
RUN mamba install --quiet --yes \
    'ipykernel=6.29.*' \
    && \
    mamba clean --all -f -y && \
    fix-permissions "${CONDA_DIR}"

# # AI
RUN mamba install --quiet --yes \
    # See https://github.com/huggingface/transformers/issues/38442
    'numpy<2.0.0' \
    \
    # Langchain: https://python.langchain.com/docs/how_to/installation/
    'langchain=0.3.*' \
    'langchain-openai=0.3.*' \
    'langchain-community=0.3.*' \
    \
    'git-lfs=3.6.*' \
    \
    'nvitop=1.5.*' \
    'gpustat=1.1.*' \
    \
    'pyarrow=20.0.*' \
    'pypdf2=3.0.*' \
    && \
    pip install --quiet --no-cache-dir \
    --no-build-isolation \
    'langchain-ollama==0.3.*' \
    'sentence-transformers==4.1.*' \
    'transformers==4.53.*' \
    'accelerate==1.8.*' \
    'tiktoken==0.9.*' \
    'huggingface_hub==0.33.*' \
    'datasets==4.0.*' \
    'optimum==1.26.*' \
    'bitsandbytes==0.46.*' \
    'gptqmodel==2.2.*' \
    # 'datatrove==0.5.*' \
    # 'evaluate==0.4.*' \
    # # TorchTune: https://github.com/pytorch/torchtune
    # 'torchtune==0.6.*' \
    # 'chromadb==0.5.*' \
    # 'flax==0.10.*' \
    # 'tensorflow-datasets==4.9.*' \
    # 'tensorflow-hub==0.16.*' \
    # 'tensorflowjs==4.22.*' \
    # 'tensorflow-decision-forests==1.11.*' \
    # 'auto-gptq==0.7.*' \
    && \
    # MLC: https://llm.mlc.ai/docs/get_started/introduction.html
    # MLC Wasm: https://llm.mlc.ai/docs/install/emcc.html 
    pip install --no-build-isolation --pre -U -f https://mlc.ai/wheels mlc-llm-nightly-cu128 mlc-ai-nightly-cu128 \
    && \
    mamba clean --all -f -y && \
    fix-permissions "${CONDA_DIR}"

USER root

### Emscripten ###
# Install Emscripten for MLC Wasm
# See: 
#   https://emscripten.org/docs/getting_started/downloads.html
#   https://llm.mlc.ai/docs/install/emcc.html
RUN wget https://github.com/emscripten-core/emsdk/archive/refs/tags/4.0.10.tar.gz && \
    tar -xzf 4.0.10.tar.gz && \
    rm 4.0.10.tar.gz && \
    mv emsdk-4.0.10 /opt/emsdk && \
    cd /opt/emsdk && \
    fix-permissions /opt/emsdk && \
    chmod +x emsdk && \
    ./emsdk install latest && \
    ./emsdk activate latest

### cosmocc ###
# Install Cosmopolitan LibC
# See: https://github.com/jart/cosmopolitan
RUN mkdir -p /opt/cosmocc && \
    wget https://github.com/jart/cosmopolitan/releases/download/4.0.2/cosmocc-4.0.2.zip && \
    unzip cosmocc-4.0.2.zip -d /opt/cosmocc && \
    rm cosmocc-4.0.2.zip && \
    fix-permissions /opt/cosmocc


USER ${NB_UID}

RUN mamba install --quiet --yes \
    altair \
    bokeh \
    bottleneck \
    blas \
    cython \
    h5py \
    numba \
    patsy \
    pytables \
    seaborn \
    scikit-learn \
    sqlalchemy \
    statsmodels \
    xlrd \
    && \
    pip install --quiet --no-cache-dir \
    tables \
    && \
    mamba clean --all -f -y && \
    fix-permissions "${CONDA_DIR}"

# Other UI enhancements
RUN \
    mamba install --quiet --yes \
    'jupyter-archive' \
    # && \
    # pip install --quiet --no-cache-dir \
    # 'jupyterlab-unfold==0.3.*' \
    # 'jupyterlab-favorites==3.2.*' \
    # 'jupyterlab-scenes==2.0.*' \
    && \
    mamba clean --all -f -y && \    
    fix-permissions "${CONDA_DIR}"

# Themes
RUN pip install --quiet --no-cache-dir \
    'jupyterlab_theme_solarized_dark' \
    'theme-darcula' && \
    fix-permissions "${CONDA_DIR}"

# Slideshow
RUN pip install --quiet --no-cache-dir \
    # not compatible with jupyterlab-myst
    # 'jupyterlab_rise==0.42.*' \
    'jupyterlab-deck==0.2.*' && \
    fix-permissions "${CONDA_DIR}"

# Copy local files as late as possible to avoid cache busting
COPY start.sh /usr/local/bin/
COPY start-notebook.sh start-singleuser.sh install-vscode-extension /usr/local/bin/
# Currently need to have both jupyter_notebook_config and jupyter_server_config to support classic and lab
COPY jupyter_server_config.py docker_healthcheck.py /etc/jupyter/

# Code extensions
RUN for ext in \
        llvm-vs-code-extensions.vscode-clangd \
        kylinideteam.cmake-intellisence \
        # vadimcn.vscode-lldb \
        ms-python.python \
        ms-python.pylint \
        ms-toolsai.jupyter \
        ms-toolsai.vscode-jupyter-powertoys \
        ms-python.black-formatter \
        # streetsidesoftware.code-spell-checker@4.1.0 \
        hediet.vscode-drawio \
        # eamodio.gitlens \
        donjayamanne.githistory \
        mhutchie.git-graph \
        waderyan.gitblame \
        codezombiech.gitignore \
        ziyasal.vscode-open-in-github \
        alefragnani.project-manager \
        ziyasal.vscode-open-in-github \
        mads-hartmann.bash-ide-vscode \
        ; do \
        code-server --extensions-dir /usr/lib/code-server/lib/vscode/extensions --install-extension "$ext"; \
    done

RUN for ext in \
    GitHub.copilot-chat@0.28.5 \
    GitHub.copilot@1.342.0 \
    Continue.continue@1.0.17 \
    ms-vsliveshare.vsliveshare@1.0.5857 \
    ; do \
    install-vscode-extension "$ext" --extensions-dir /usr/lib/code-server/lib/vscode/extensions; \
    done

RUN \
    mamba install --quiet --yes \
    'gh=2.74.*' \
    'jupyter-ai=2.31.*' \
    && \
    # pip install --quiet --no-cache-dir --pre \
    # 'jupyter-ai==3.0.0b0' \
    # && \
    pip install --quiet --no-cache-dir \
    'divewidgets' \
    # 'nbgrader==0.9.*' \
    'nbgrader@git+https://github.com/dive4dec/nbgrader.git@8e0b69a6da48856e6f180d27041b6e1c96602934' \
    # 'vllm' \
    'jdc' \
    # 'jupyterlab-tensorboard-pro' \
    && \
    mamba clean --all -f -y && \    
    fix-permissions "${CONDA_DIR}"

# Other Tools
USER root

# Ollama
RUN curl -fsSL https://ollama.com/install.sh | sh

USER ${NB_UID}

RUN \
    mamba install --quiet --yes \
    'plotly=6.1.*' \
    'sqlglot=26.22.*' \
    'polars=1.30.*' \
    'duckdb=1.3.*' \
    && \
    pip install --quiet --no-cache-dir \
    'marimo[recommended]==0.14.*' \
    'git+https://github.com/dive4dec/jupyter-marimo-proxy@a493c16de8e47a29c8f82ff65b10ee9ae393606c' \
    'kaleido==0.2.*' \
    # 'capymoa==0.8.*' \
    && \
    mamba clean --all -f -y && \    
    fix-permissions "${CONDA_DIR}"

RUN \
    mamba install --quiet --yes \
    # Python
    # 'xeus-python' \
    # C, C++
    'xeus-cpp' \
    # 'xeus-cling=0.15.*' \
    'xtensor' \
    # 'xwidgets' \
    'root' \
    && \
    mamba clean --all -f -y && \    
    fix-permissions "${CONDA_DIR}"

# # Fix issue of packaging version being None after downgrade
# # This is caused by installing langchain above 
# RUN rm -rf /opt/conda/lib/python3.12/packaging-25.0.dist-info

# ----------------------------------------------------------

FROM foundation AS prod

COPY --from=base /etc/ /etc/
COPY --from=base /usr/ /usr/
COPY --from=base /var/ /var/
COPY --from=base /home/ /home/
COPY --from=base /opt/ /opt/

# set Mamba root prefix
ENV MAMBA_ROOT_PREFIX=${CONDA_DIR}

# Configure container startup
ENTRYPOINT ["tini", "-g", "--"]
# Configure container startup
CMD ["start-notebook.sh"]

ENV JUPYTER_PORT=8888
EXPOSE $JUPYTER_PORT

### Tensorflow
# minor issues: 
# https://github.com/tensorflow/tensorflow/issues/63109
ENV TF_CPP_MIN_LOG_LEVEL=2

# https://github.com/tensorflow/tensorboard/pull/3674
ENV TENSORBOARD_PROXY_URL="/proxy/%PORT%/"

# NbGrader
ENV NBGRADER_UID=2000 \
    NBGRADER_USER=nbgrader

# Create NBGRADER_USER with name nbgrader, UID=2000 and in the 'users' group
# On jupyterhub, this user should be the owner of the course root and exchange folder for nbgrader.
RUN useradd -l -M -s /bin/bash -N -u "${NBGRADER_UID}" "${NBGRADER_USER}"

# Switch back to jovyan to avoid accidental container runs as root
USER ${NB_UID}

# nbgrader deploy
RUN mkdir -p ${CONDA_DIR}/srv/exchange && chmod ugo+rw $_

RUN jupyter server extension disable --sys-prefix nbgrader.server_extensions.formgrader && \
    jupyter labextension disable nbgrader:formgrader && \
    jupyter labextension disable nbgrader:course-list && \
    jupyter labextension disable nbgrader:create-assignment


# Configuration files
# Conda
COPY --chown="${NB_UID}:${NB_GID}" initial-condarc "${CONDA_DIR}/.condarc"
# Nbgrader
COPY --chown=${NB_USER}:${NB_GID} nbgrader_config.py ${CONDA_DIR}/etc/jupyter/nbgrader_config.py
# Jupyter kernels
COPY --chown="${NB_UID}:${NB_GID}" kernels/ "${CONDA_DIR}/share/jupyter/kernels/"
# JupyterLab Code Formatting
COPY --chown="${NB_UID}:${NB_GID}" jupyterlab_code_formatter_settings.json "${CONDA_DIR}/share/jupyter/labextensions/jupyterlab_code_formatter/schemas/jupyterlab_code_formatter/settings.json"
# Jupyter LSP
COPY --chown="${NB_UID}:${NB_GID}" jupyterlab_code_formatter_settings.json "${CONDA_DIR}/share/jupyter/labextensions/@jupyter-lsp/jupyterlab-lsp/schemas/@jupyter-lsp/jupyterlab-lsp/diagnostics.json"
# IPython config
COPY --chown=${NB_USER}:${NB_GID} ipython_config.py "${CONDA_DIR}/etc/ipython/ipython_config.py"
# Jupyter Server
COPY --chown="${NB_UID}:${NB_GID}" jupyter_server_config.d/ "${CONDA_DIR}/etc/jupyter/jupyter_server_config.d/"

# Disable news and update
# See https://jupyterlab.readthedocs.io/en/stable/user/announcements.html
RUN jupyter labextension disable "@jupyterlab/apputils-extension:announcements"

USER ${NB_UID}

RUN \
    pip install --quiet --no-cache-dir \
    'git+https://github.com/dive4dec/dive_ai@3b9e78f5adaa7c633c8eaf5c0ae392b1627683d6#subdirectory=dive_ai' \
    && \
    fix-permissions "${CONDA_DIR}"

RUN fix-permissions "/usr/lib/code-server/lib/vscode/extensions"

# Add Emscripten and CUDA to PATH
ENV PATH="/opt/emsdk:/opt/emsdk/upstream/emscripten:/usr/local/cuda/bin:${PATH}:/opt/cosmocc/bin"

WORKDIR "${HOME}"

# ----------------------------------------------------------

FROM prod AS collab

USER ${NB_USER}

# Collaboration
RUN \
    mamba install --quiet --yes \
    'jupyter-collaboration=4.1.*' \
    && \
    pip install --pre --quiet --no-cache-dir \
    'jupyterlab-chat==0.16.*' \
    && \
    mamba clean --all -f -y && \
    fix-permissions "${CONDA_DIR}"

FROM prod AS default

USER ${NB_USER}