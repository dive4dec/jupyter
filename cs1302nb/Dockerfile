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
    sed -i 's/^#force_color_prompt=yes/force_color_prompt=yes/' /etc/bash.bashrc

# Fix the UID conflict with user ubuntu
# See https://bugs.launchpad.net/cloud-images/+bug/2005129
RUN touch /var/mail/ubuntu && chown ubuntu /var/mail/ubuntu && \
    userdel -r ubuntu && \
    useradd -l -m -s /bin/bash -N -u "${NB_UID}" "${NB_USER}"

USER root
FROM foundation AS base

# ============================================================
# ALL apt-get packages merged into one layer
# ============================================================
RUN apt-get update --yes && \
    apt-get install --yes --no-install-recommends \
    # -- Core utilities --
    bzip2 ca-certificates locales sudo tini wget less curl \
    git nano-tiny tzdata unzip vim-tiny openssh-client xclip \
    run-one tree ripgrep tmux \
    # -- nbconvert / LaTeX --
    pandoc texlive-xetex texlive-fonts-recommended texlive-plain-generic \
    dvisvgm latexmk biber lmodern \
    # -- Desktop --
    fonts-liberation gpg software-properties-common emacs thonny \
    dbus-x11 xfce4 xfce4-panel xfce4-session xfce4-settings xorg \
    xubuntu-icon-theme x11-utils xfonts-base xvfb \
    # -- Programming languages --
    build-essential cmake ninja-build default-jdk default-jre \
    gdb fpc-source sqlite3 pdf2svg \
    # -- misc --
    libzmq3-dev \
    && \
    paperconfig -p a4 && \
    echo "en_US.UTF-8 UTF-8" > /etc/locale.gen && \
    echo "C.UTF-8 UTF-8" >> /etc/locale.gen && \
    locale-gen && \
    ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Install VS Code
RUN wget -qO- https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > microsoft.gpg && \
    install -o root -g root -m 644 microsoft.gpg /etc/apt/trusted.gpg.d/ && \
    sh -c 'echo "deb [arch=$(dpkg --print-architecture)] https://packages.microsoft.com/repos/vscode stable main" > /etc/apt/sources.list.d/vscode.list' && \
    apt-get install -y --no-install-recommends apt-transport-https && \
    apt-get update --yes && \
    apt-get install --yes --no-install-recommends code && \
    apt-get clean && rm -rf /var/lib/apt/lists/* microsoft.gpg
# Install Clang 22 via apt (avoids conflicts with ROOT's LLVM when installed via mamba)
RUN wget -O /tmp/llvm.sh https://apt.llvm.org/llvm.sh && \
    chmod +x /tmp/llvm.sh && \
    /tmp/llvm.sh 22 all && \
    rm -f /tmp/llvm.sh && \
    for cmd in $(dpkg -L clang-format-22 clang-tidy-22 clang-22 clangd-22 lld-22 lldb-22 llvm-22 2>/dev/null | grep '^/usr/bin/.*-22$'); do \
        base=$(basename "$cmd"); \
        base=${base%-22}; \
        update-alternatives --install "/usr/bin/$base" "$base" "$cmd" 200; \
    done && \
    apt-get clean && rm -rf /var/lib/apt/lists/*


# Install Firefox Nightly
RUN add-apt-repository ppa:ubuntu-mozilla-daily/ppa && \
    apt-get update --yes && \
    apt-get install --yes --no-install-recommends firefox-trunk && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Modify desktop files to include --no-sandbox
RUN sed -i 's|Exec=/usr/share/code/code|Exec=/usr/share/code/code --no-sandbox|' /usr/share/applications/code.desktop && \
    sed -i 's|Exec=firefox-trunk|Exec=firefox-trunk --no-sandbox|' /usr/share/applications/firefox-trunk.desktop && \
    cat <<EOF >> /etc/bash.bashrc
alias code='code --no-sandbox'
alias firefox-trunk='firefox-trunk --no-sandbox'
alias firefox='firefox-trunk --no-sandbox'
EOF

# Create a wrapper script for Firefox nightly with --no-sandbox
RUN echo -e '#!/bin/bash\nexec /usr/bin/firefox-trunk --no-sandbox "$@"' > /usr/local/bin/firefox-trunk-no-sandbox && \
    chmod +x /usr/local/bin/firefox-trunk-no-sandbox && \
    update-alternatives --install /usr/bin/x-www-browser x-www-browser /usr/local/bin/firefox-trunk-no-sandbox 200 && \
    update-alternatives --set x-www-browser /usr/local/bin/firefox-trunk-no-sandbox && \
    update-alternatives --install /usr/bin/gnome-www-browser gnome-www-browser /usr/local/bin/firefox-trunk-no-sandbox 200 && \
    update-alternatives --set gnome-www-browser /usr/local/bin/firefox-trunk-no-sandbox

# Install TurboVNC based on the current architecture
RUN ARCH=$(dpkg --print-architecture) && \
    wget -q "https://github.com/TurboVNC/turbovnc/releases/download/3.3/turbovnc_3.3_${ARCH}.deb" -O /tmp/turbovnc.deb && \
    apt-get update --yes && \
    apt-get install --yes --no-install-recommends /tmp/turbovnc.deb && \
    rm /tmp/turbovnc.deb && \
    ln -s /opt/TurboVNC/bin/* /usr/local/bin/ && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# MIT Scheme
COPY mit-scheme/ /tmp/mit-scheme/
RUN bash /tmp/mit-scheme/buildscript.sh

# fix-permissions script
COPY fix-permissions /usr/local/bin/fix-permissions
RUN chmod a+rx /usr/local/bin/fix-permissions

# PAM / sudoers / group permissions
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
ARG MICROMAMBA_VERSION=2.7.0-0

# Download and install Micromamba
COPY --chown="${NB_UID}:${NB_GID}" initial-condarc "${CONDA_DIR}/.condarc"
WORKDIR /tmp
RUN set -x && \
    case "$(uname)" in \
      Linux) PLATFORM="linux" ;; \
      Darwin) PLATFORM="osx" ;; \
      *NT*) PLATFORM="win" ;; \
    esac && \
    ARCH="$(uname -m)" && \
    case "$ARCH" in \
      aarch64|ppc64le|arm64) ;; \
      *) ARCH="64" ;; \
    esac && \
    case "$PLATFORM-$ARCH" in \
        linux-aarch64|linux-ppc64le|linux-64|osx-arm64|osx-64|win-64) ;; \
        *) echo "Failed to detect your OS" >&2 && exit 1 ;; \
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
        apt-get install --yes --no-install-recommends cuda-toolkit-12-8 && \
        rm -rf /var/lib/apt/lists/* 3bf863cc.pub; \
    else \
        echo "Skipping CUDA installation: unsupported architecture ($ARCH)"; \
    fi

USER ${NB_UID}

# ============================================================
# Python + PyTorch + Jupyter + Clang — merged into one big install
# ============================================================
RUN if [ "${PYTHON_VERSION:-}" = "" ]; then PYTHON_SPECIFIER="python"; else PYTHON_SPECIFIER="python=${PYTHON_VERSION}"; fi && \
    mamba install --yes \
    "${PYTHON_SPECIFIER}" \
    && \
    mkdir -p "${CONDA_DIR}/conda-meta" && \
    mamba list python | sed 's/^[[:space:]]*//' | grep '^python ' | tr -s ' ' | cut -d ' ' -f 1,2 >> "${CONDA_DIR}/conda-meta/pinned" && \
    mamba clean --all -f -y && \
    fix-permissions "${CONDA_DIR}" && \
    fix-permissions "/home/${NB_USER}" && \
    \
    # -- PyTorch (cu128) --
    ARCH=$(dpkg --print-architecture) && \
    PIP_INDEX="" && \
    [ "$ARCH" = "amd64" ] && PIP_INDEX="--index-url https://download.pytorch.org/whl/cu128"; \
    pip install --quiet --no-cache-dir \
        'torch==2.11.*' \
        'torchvision==0.26.*' \
        'torchaudio==2.11.*' \
        $PIP_INDEX && \
    \
    # -- Jupyter core + Node.js --
    mamba install --yes --quiet \
    'nodejs==24.*' \
    'notebook==7.5.*' \
    'jupyterlab==4.5.*' \
    'jupyterhub==5.4.*' \
    && \
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
    sh /tmp/install.sh --version 4.123.0 && \
    fix-permissions "${HOME}" && \
    fix-permissions /usr/lib/code-server/ && \
    rm -rf ~/.cache/code-server/ && \
    rm -rf /tmp/install.sh

USER ${NB_UID}

# ============================================================
# Programming language kernels + Course packages + UI extensions
# ============================================================
RUN \
    mamba install --quiet --yes \
    'openjdk=23.*' \
    'ant=1.10.*' \
    'jupyterlab-myst=2.7.*' \
    'jupyterlite=0.7.*' \
    'jupyterlite-sphinx=0.22.*' \
    && \
    pip install --quiet --no-cache-dir \
    'calysto-scheme==1.4.*' \
    && \
    python -m calysto_scheme install --sys-prefix && \
    \
    # Java kernel (IJupyter)
    wget 'https://github.com/SpencerPark/IJava/releases/download/v1.3.0/ijava-1.3.0.zip' \
    -O /tmp/ijava.zip && \
    unzip /tmp/ijava.zip -d /tmp/ijava && \
    python /tmp/ijava/install.py --sys-prefix && \
    rm -rf /tmp/ijava && \
    \
    # -- Course packages --
    mamba install --quiet --yes \
    'manim=0.20.*' \
    'manimpango=0.6.*' \
    'pandas=2.3.*' \
    'matplotlib-base=3.10.*' \
    'ipympl=0.10.*' \
    'sympy=1.14.*' \
    && \
    mamba clean --all -f -y && \
    npm cache clean --force && \
    fix-permissions "${CONDA_DIR}"

# ============================================================
# JupyterLab extensions + LSP + Formatters
# ============================================================
RUN mamba install --quiet --yes \
    'websockify=0.13.*' \
    'jupyter-vscode-proxy=0.7.*' \
    'jupytext=1.18.*' \
    'black=25.1.*' \
    'jupyterlab_code_formatter=3.0.*' \
    'jupyterlab-lsp=5.2.*' \
    'jupyter-resource-usage=1.2.*' \
    'nbgitpuller==1.3.*' \
    'jupyterlab-git==0.52.*' \
    && \
    pip install --quiet --no-cache-dir \
    'python-lsp-server[all]==1.14.*' \
    'astyle==3.6.*' \
    'jupyter-www-proxy' \
    && \
    npm install -g --save-dev \
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

# MyST documentation tool
RUN npm install -g mystmd@1.10.1 && \
    npm cache clean --force

# Remote desktop proxy
RUN pip install --quiet --no-cache-dir \
    'jupyter-remote-desktop-proxy==3.0.*' \
    && \
    mamba clean --all -f -y && \
    fix-permissions "${CONDA_DIR}"

# IPython kernel for virtualenvs
RUN mamba install --quiet --yes 'ipykernel=7.2.*' && \
    mamba clean --all -f -y && \
    fix-permissions "${CONDA_DIR}"

# ============================================================
# AI/ML packages — langchain, transformers, MLC, etc.
# ============================================================
RUN mamba install --quiet --yes \
    'git-lfs=3.7.*' \
    'nvitop=1.7.*' \
    'gpustat=1.1.*' \
    'pyarrow=24.0.*' \
    'pypdf2=3.0.*' \
    && \
    pip install --quiet --no-cache-dir \
    --no-build-isolation \
    'langchain==1.3.*' \
    'langchain-openai==1.2.*' \
    'sentence-transformers==5.5.*' \
    'transformers==5.10.*' \
    'accelerate==1.13.*' \
    'bitsandbytes==0.49.*' \
    'tiktoken==0.13.*' \
    'datasets==4.8.*' \
    'optimum==2.1.*' \
    && \
    pip install --quiet --no-cache-dir \
    'gptqmodel==7.0.*' \
    && \
    pip install --no-build-isolation --pre -U -f https://mlc.ai/wheels mlc-llm-nightly-cu128 mlc-ai-nightly-cu128 \
    && \
    mamba clean --all -f -y && \
    fix-permissions "${CONDA_DIR}"

USER root

# Emscripten for MLC Wasm
RUN curl -fsSL -o /tmp/emsdk.tar.gz https://github.com/emscripten-core/emsdk/archive/refs/tags/6.0.0.tar.gz && \
    tar -xzf /tmp/emsdk.tar.gz -C /opt && \
    mv /opt/emsdk-6.0.0 /opt/emsdk && \
    rm /tmp/emsdk.tar.gz && \
    chmod +x /opt/emsdk/emsdk && \
    /opt/emsdk/emsdk install latest && \
    /opt/emsdk/emsdk activate latest && \
    fix-permissions /opt/emsdk

# Cosmopolitan LibC (cosmocc)
RUN mkdir -p /opt/cosmocc && \
    wget https://github.com/jart/cosmopolitan/releases/download/4.0.2/cosmocc-4.0.2.zip && \
    unzip cosmocc-4.0.2.zip -d /opt/cosmocc && \
    rm cosmocc-4.0.2.zip && \
    fix-permissions /opt/cosmocc

USER ${NB_UID}

# ============================================================
# Data science + visualization + UI extensions — merged
# ============================================================
RUN mamba install --quiet --yes \
    altair bokeh bottleneck blas cython h5py numba patsy \
    pytables seaborn scikit-learn sqlalchemy statsmodels xlrd \
    && \
    pip install --quiet --no-cache-dir tables \
    && \
    mamba install --quiet --yes \
    'jupyter-archive=3.4.*' \
    && \
    pip install --quiet --no-cache-dir \
    'jupyterlab_theme_solarized_dark' \
    'theme-darcula' \
    'custom-slideshow' \
    && \
    mamba clean --all -f -y && \
    fix-permissions "${CONDA_DIR}"

# Copy local files (scripts + configs)
COPY start.sh /usr/local/bin/
COPY start-notebook.sh start-singleuser.sh install-vscode-extension /usr/local/bin/
COPY jupyter_server_config.py docker_healthcheck.py /etc/jupyter/

# Code-server extensions (built-in --install-extension)
RUN for ext in \
        llvm-vs-code-extensions.vscode-clangd \
        kylinideteam.cmake-intellisence \
        ms-python.python \
        ms-python.pylint \
        ms-toolsai.jupyter \
        ms-toolsai.vscode-jupyter-powertoys \
        ms-python.black-formatter \
        hediet.vscode-drawio \
        donjayamanne.githistory \
        mhutchie.git-graph \
        waderyan.gitblame \
        codezombiech.gitignore \
        ziyasal.vscode-open-in-github \
        alefragnani.project-manager \
        mads-hartmann.bash-ide-vscode \
        ; do \
        code-server --extensions-dir /usr/lib/code-server/lib/vscode/extensions --install-extension "$ext"; \
    done

# Code-server extensions (via install-vscode-extension for versioned downloads)
RUN for ext in \
    Continue.continue@1.2.22 \
    ; do \
    install-vscode-extension "$ext" --extensions-dir /usr/lib/code-server/lib/vscode/extensions; \
    done

# ACP Client extension for Hermes Agent
RUN install-vscode-extension "formulahendry.acp-client@0.2.0" --extensions-dir /usr/lib/code-server/lib/vscode/extensions && \
    sed -i 's/bn=ln(dn,\["navigator"\])/bn=function(){return navigator}/' \
        /usr/lib/code-server/lib/vscode/extensions/formulahendry.acp-client-*/dist/extension.js

USER ${NB_UID}

# Jupyter AI + nbgrader + course widgets
RUN pip install --quiet --no-cache-dir \
    'jupyter-ai==3.0.*' \
    'jupyter-ai-jupyternaut' \
    'jupyter-ai-magic-commands' \
    'divewidgets' \
    'nbgrader@git+https://github.com/dive4dec/nbgrader.git@8e0b69a6da48856e6f180d27041b6e1c96602934' \
    'jdc' \
    && \
    mamba clean --all -f -y && \
    fix-permissions "${CONDA_DIR}"

# Ollama
USER root
RUN curl -fsSL https://ollama.com/install.sh | sh


# Plotly + data viz + marimo + JupyterLab extensions
RUN mamba install --quiet --yes \
    'plotly=6.6.*' \
    'sqlglot=28.10.*' \
    'polars=1.41.*' \
    'duckdb=1.5.*' \
    && \
    pip install --quiet --no-cache-dir \
    'marimo[recommended]==0.23.*' \
    'git+https://github.com/dive4dec/jupyter-marimo-proxy@a493c16de8e47a29c8f82ff65b10ee9ae393606c' \
    'kaleido==0.2.*' \
    'jupyterlab-execute-time==3.2.*' \
    && \
    mamba install --quiet --yes \
    'xeus-cpp=0.10.*' \
    'xtensor=0.27.*' \
    'root=6.40.*' \
    'gxx_linux-64' \
    && \
    mamba clean --all -f -y && \
    fix-permissions "${CONDA_DIR}"



FROM base AS prod

# Configure container startup
ENTRYPOINT ["tini", "-g", "--", "micromamba", "run", "-n", "base"]
CMD ["start-notebook.sh"]

# NbGrader
ENV NBGRADER_UID=2000 \
    NBGRADER_USER=nbgrader

USER root

# Create NBGRADER_USER
RUN useradd -l -M -s /bin/bash -N -u "${NBGRADER_UID}" "${NBGRADER_USER}"

USER ${NB_UID}

# nbgrader deploy
RUN mkdir -p ${CONDA_DIR}/srv/exchange && chmod ugo+rw $_

RUN jupyter server extension disable --sys-prefix nbgrader.server_extensions.formgrader && \
    jupyter labextension disable nbgrader:formgrader && \
    jupyter labextension disable nbgrader:course-list && \
    jupyter labextension disable nbgrader:create-assignment

# Configuration files
COPY --chown="${NB_UID}:${NB_GID}" initial-condarc "${CONDA_DIR}/.condarc"
COPY --chown=${NB_USER}:${NB_GID} nbgrader_config.py ${CONDA_DIR}/etc/jupyter/nbgrader_config.py
COPY --chown="${NB_UID}:${NB_GID}" kernels/ "${CONDA_DIR}/share/jupyter/kernels/"
COPY --chown="${NB_UID}:${NB_GID}" jupyterlab_code_formatter_settings.json "${CONDA_DIR}/share/jupyter/labextensions/jupyterlab_code_formatter/schemas/jupyterlab_code_formatter/settings.json"
COPY --chown="${NB_UID}:${NB_GID}" jupyterlab_code_formatter_settings.json "${CONDA_DIR}/share/jupyter/labextensions/@jupyter-lsp/jupyterlab-lsp/schemas/@jupyter-lsp/jupyterlab-lsp/diagnostics.json"
COPY --chown="${NB_UID}:${NB_GID}" jupyter_server_config.d/ "${CONDA_DIR}/etc/jupyter/jupyter_server_config.d/"

# Disable news and update announcements
RUN jupyter labextension disable "@jupyterlab/apputils-extension:announcements"

RUN fix-permissions "/usr/lib/code-server/lib/vscode/extensions"

# ============================================================
# Hermes Agent (system-wide) + jupyter-ai-hermes + jupyter-hermes-proxy
# ============================================================
# Strategy:
#   1. Clone hermes-agent source once, build web_dist, pip install into conda
#   2. COPY submodule sources and pip install from local paths
# This avoids curl|install.sh (which creates isolated venvs), symlinks,
# and duplicate git clones.  The `hermes` command lands at /opt/conda/bin/
# where both JupyterLab and code-server can find it.

# Clone hermes-agent, build dashboard web_dist, and pip install into conda
RUN git clone --depth 1 --branch v2026.5.29.2 https://github.com/NousResearch/hermes-agent.git /tmp/hermes-agent && \
    # FIX v2026.5.29.2: pyproject.toml excludes hermes_cli.* subpackages (dashboard_auth, etc.)
    sed -i 's/include = \["agent", "agent.\*", "tools", "tools.\*", "hermes_cli", "gateway"/include = ["agent", "agent.*", "tools", "tools.*", "hermes_cli", "hermes_cli.*", "gateway"/' /tmp/hermes-agent/pyproject.toml && \
    # Build the dashboard web UI (required for jupyter-hermes-proxy)
    cd /tmp/hermes-agent/web && \
    npm install && \
    npm run build && \
    cd / && \
    # Install hermes-agent into the conda environment
    pip install --quiet --no-cache-dir /tmp/hermes-agent && \
    rm -rf /tmp/hermes-agent && \
    fix-permissions "${CONDA_DIR}"

# Install jupyter-ai-hermes and jupyter-hermes-proxy from build contexts
# The Makefile passes --build-context for each submodule, avoiding symlinks
# and the "too many links" buildkit error.
COPY --from=jupyter-ai-hermes --chown=${NB_USER}:${NB_GID} . /tmp/jupyter-ai-hermes
COPY --from=jupyter-hermes-proxy --chown=${NB_USER}:${NB_GID} . /tmp/jupyter-hermes-proxy
RUN pip install --quiet --no-cache-dir \
    /tmp/jupyter-ai-hermes \
    /tmp/jupyter-hermes-proxy \
    && \
    rm -rf /tmp/jupyter-ai-hermes /tmp/jupyter-hermes-proxy && \
    fix-permissions "${CONDA_DIR}"

# Add Emscripten, CUDA, CosmoCC to PATH
ENV PATH="/opt/emsdk:/opt/emsdk/upstream/emscripten:/usr/local/cuda/bin:${PATH}:/opt/cosmocc/bin"
RUN chmod a+w /opt/emsdk/upstream/emscripten/cache


WORKDIR "${HOME}"


FROM prod AS default

USER ${NB_USER}
