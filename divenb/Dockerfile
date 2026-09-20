ARG ROOT_CONTAINER=ubuntu:26.04

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
    PATH="${CONDA_DIR}/bin:${PATH}" \
    UV_LINK_MODE=copy

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
    fonts-liberation gpg software-properties-common emacs \
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

# fix-permissions script (needed by Emscripten, CosmoCC, and later stages)
COPY fix-permissions /usr/local/bin/fix-permissions
RUN chmod a+rx /usr/local/bin/fix-permissions

# Emscripten for MLC Wasm
RUN curl -fsSL -o /tmp/emsdk.tar.gz https://github.com/emscripten-core/emsdk/archive/refs/tags/6.0.8.tar.gz && \
    tar -xzf /tmp/emsdk.tar.gz -C /opt && \
    mv /opt/emsdk-6.0.8 /opt/emsdk && \
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

# Install VS Code
RUN wget -qO- https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > microsoft.gpg && \
    install -o root -g root -m 644 microsoft.gpg /etc/apt/trusted.gpg.d/ && \
    sh -c 'echo "deb [arch=$(dpkg --print-architecture)] https://packages.microsoft.com/repos/vscode stable main" > /etc/apt/sources.list.d/vscode.list' && \
    apt-get install -y --no-install-recommends apt-transport-https && \
    apt-get update --yes && \
    apt-get install --yes --no-install-recommends code && \
    apt-get clean && rm -rf /var/lib/apt/lists/* microsoft.gpg

# code-server
RUN wget -q https://code-server.dev/install.sh -O /tmp/install.sh && \
    sh /tmp/install.sh --version 4.138.0 && \
    fix-permissions "${HOME}" && \
    fix-permissions /usr/lib/code-server/ && \
    rm -rf ~/.cache/code-server/ && \
    rm -rf /tmp/install.sh

# Install Google Chrome (Chromium-family browser for Hermes CDP + student use)
# Ubuntu's chromium-browser is a snap stub unusable in Docker, so use Google's apt repo
RUN wget -q https://dl.google.com/linux/linux_signing_key.pub -O /tmp/chrome-key.pub && \
    mkdir -p /etc/apt/keyrings && \
    cat /tmp/chrome-key.pub | gpg --dearmor > /etc/apt/keyrings/google-chrome.gpg && \
    echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list && \
    apt-get update --yes && \
    apt-get install --yes --no-install-recommends google-chrome-stable && \
    rm /tmp/chrome-key.pub && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Disable Chromium/Electron sandbox globally for all Chromium-based apps.
# Containers lack CAP_SYS_ADMIN, so Chromium's namespace sandbox crashes on startup.
# ELECTRON_DISABLE_SANDBOX=1 covers VS Code (code-server) and Obsidian (Electron apps).
# Chrome wrapper handles its own --no-sandbox (Electron env var doesn't affect Chrome).
# Also: the old bash aliases for code/chrome are replaced by this env var + wrapper.
RUN echo "export ELECTRON_DISABLE_SANDBOX=1" >> /etc/bash.bashrc && \
    echo "export ELECTRON_DISABLE_SANDBOX=1" > /etc/profile.d/electron-sandbox.sh && \
    chmod 644 /etc/profile.d/electron-sandbox.sh && \
    # Chrome: /usr/bin/google-chrome-stable is a symlink → replace with wrapper
    mv /usr/bin/google-chrome-stable /usr/bin/google-chrome-stable.real && \
    printf '#!/bin/bash\nexec /usr/bin/google-chrome-stable.real --no-sandbox "$@"\n' > /usr/bin/google-chrome-stable && \
    chmod 755 /usr/bin/google-chrome-stable && \
    # Chrome .desktop: remove hardcoded --no-sandbox (wrapper handles it now)
    sed -i 's|Exec=/usr/bin/google-chrome-stable --no-sandbox|Exec=/usr/bin/google-chrome-stable|g' /usr/share/applications/google-chrome.desktop && \
    sed -i 's|Exec=/usr/bin/google-chrome-stable --no-sandbox|Exec=/usr/bin/google-chrome-stable|g' /usr/share/applications/com.google.Chrome.desktop && \
    # VS Code .desktop: remove hardcoded --no-sandbox (ELECTRON_DISABLE_SANDBOX handles it)
    sed -i 's| --no-sandbox||g' /usr/share/applications/code.desktop

# Replace bwrap with a passthrough wrapper for containers without CAP_SYS_ADMIN.
# Ubuntu 26.04 glycin (GTK image loader) uses bwrap to sandbox image decoders.
# bwrap needs mount namespaces (CAP_SYS_ADMIN), unavailable in K8s pods.
# Without this, XFCE panel crashes on icon load: "bwrap: Failed to make / slave".
# The wrapper strips sandbox flags and execs the target binary directly,
# which is safe because the container itself provides isolation.
COPY bwrap-wrapper.sh /tmp/bwrap-wrapper.sh
RUN mv /usr/bin/bwrap /usr/bin/bwrap.real && \
    cp /tmp/bwrap-wrapper.sh /usr/bin/bwrap && \
    chmod 755 /usr/bin/bwrap && \
    rm /tmp/bwrap-wrapper.sh

# Set Chrome as default browser via alternatives
RUN update-alternatives --install /usr/bin/x-www-browser x-www-browser /usr/bin/google-chrome-stable 200 && \
    update-alternatives --set x-www-browser /usr/bin/google-chrome-stable && \
    update-alternatives --install /usr/bin/gnome-www-browser gnome-www-browser /usr/bin/google-chrome-stable 200 && \
    update-alternatives --set gnome-www-browser /usr/bin/google-chrome-stable

# Install Obsidian (desktop note-taking app)
# Obsidian is Electron-based (Chromium sandbox) — needs --no-sandbox in containers.
# /usr/bin/obsidian → /etc/alternatives/obsidian → /opt/Obsidian/obsidian (symlink chain)
# Replace the /usr/bin symlink with a wrapper that injects --no-sandbox.
# NOTE: 1.13.8 was released without a Linux desktop build (APK only) — use 1.13.7,
# the latest release that still ships obsidian_<ver>_amd64.deb.
# NOTE: since 1.13.7 the .desktop file is md.obsidian.Obsidian.desktop (was
# obsidian.desktop in <=1.13.4); glob over both so the Exec rewrite survives renames.
RUN ARCH=$(dpkg --print-architecture) && \
    wget -q "https://github.com/obsidianmd/obsidian-releases/releases/download/v1.13.7/obsidian_1.13.7_amd64.deb" -O /tmp/obsidian.deb && \
    apt-get update --yes && \
    apt-get install --yes --no-install-recommends /tmp/obsidian.deb && \
    rm /tmp/obsidian.deb && \
    apt-get clean && rm -rf /var/lib/apt/lists/* && \
    # Replace symlink with --no-sandbox wrapper (covers terminal + .desktop launcher)
    mv /usr/bin/obsidian /usr/bin/obsidian.real && \
    printf '#!/bin/bash\nexec /usr/bin/obsidian.real --no-sandbox "$@"\n' > /usr/bin/obsidian && \
    chmod 755 /usr/bin/obsidian && \
    # Point .desktop at the wrapper (deb package points at /opt/Obsidian/obsidian directly).
    # Filename is md.obsidian.Obsidian.desktop since 1.13.7 (obsidian.desktop before).
    find /usr/share/applications -maxdepth 1 -name '*bsidian*.desktop' -exec sed -i 's|Exec=/opt/Obsidian/obsidian|Exec=/usr/bin/obsidian|' {} +

# Install TurboVNC based on the current architecture
RUN ARCH=$(dpkg --print-architecture) && \
    wget -q "https://github.com/TurboVNC/turbovnc/releases/download/3.3.1/turbovnc_3.3.1_${ARCH}.deb" -O /tmp/turbovnc.deb && \
    apt-get update --yes && \
    apt-get install --yes --no-install-recommends /tmp/turbovnc.deb && \
    rm /tmp/turbovnc.deb && \
    ln -s /opt/TurboVNC/bin/* /usr/local/bin/ && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Hide logout from XFCE Applications menu (prevents accidental VNC session kill)
RUN sed -i '/^\[Desktop Entry\]/a NoDisplay=true' /usr/share/applications/xfce4-session-logout.desktop

# MIT Scheme
COPY mit-scheme/ /tmp/mit-scheme/
RUN bash /tmp/mit-scheme/buildscript.sh

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
ARG PYTHON_VERSION=3.14

# Pin micromamba version here, or leave it empty for the latest version
ARG MICROMAMBA_VERSION=2.9.0-0

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

# Install uv for fast pip installs (10-100x faster than pip).
# uv detects the conda env via CONDA_PREFIX and installs into it with --system.
# At runtime, pip is replaced with a uv wrapper (see prod stage) so that
# both interactive `pip install foo` and programmatic calls go through uv.
# `python -m pip` retains the original pip as an escape hatch.
# uv is installed via mamba (conda-forge) into /opt/conda/bin — never /home/jovyan.

# Install CUDA Toolkit 13.3 (ubuntu2604 repo).
# Note: cu133 PyTorch/MLC wheels do not exist yet, so we use cu130 wheels
# (which bundle their own CUDA 13.0 runtime, compatible with the 13.3 toolkit).
# COMMENTED OUT — not needed for divenb (PyTorch wheels bundle their own CUDA runtime).
# RUN ARCH=$(dpkg --print-architecture) && \
#     if [ "$ARCH" = "amd64" ]; then \
#         wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2604/x86_64/cuda-ubuntu2604.pin && \
#         mv cuda-ubuntu2604.pin /etc/apt/preferences.d/cuda-repository-pin-600 && \
#         wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2604/x86_64/60DF8A40.pub && \
#         gpg --dearmor -o /usr/share/keyrings/cuda-archive-keyring.gpg 60DF8A40.pub && \
#         echo "deb [signed-by=/usr/share/keyrings/cuda-archive-keyring.gpg] https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2604/x86_64/ /" > /etc/apt/sources.list.d/cuda.list && \
#         apt-get update && \
#         apt-get install --yes --no-install-recommends cuda-toolkit-13-3 && \
#         rm -rf /var/lib/apt/lists/* 60DF8A40.pub; \
#     else \
#         echo "Skipping CUDA installation: unsupported architecture ($ARCH)"; \
#     fi

USER ${NB_UID}

# ============================================================
# Python + PyTorch + Jupyter merged into one big install
# ============================================================
RUN if [ "${PYTHON_VERSION:-}" = "" ]; then PYTHON_SPECIFIER="python"; else PYTHON_SPECIFIER="python=${PYTHON_VERSION}"; fi && \
    mamba install --yes \
    "${PYTHON_SPECIFIER}" \
    'uv' \
    && \
    mkdir -p "${CONDA_DIR}/conda-meta" && \
    mamba list python | sed 's/^[[:space:]]*//' | grep '^python ' | tr -s ' ' | cut -d ' ' -f 1,2 >> "${CONDA_DIR}/conda-meta/pinned" && \
    mamba clean --all -f -y && \
    fix-permissions "${CONDA_DIR}" && \
    fix-permissions "/home/${NB_USER}" && \
    \
    # -- PyTorch (cu130 — cu133 wheels don't exist yet) --
    ARCH=$(dpkg --print-architecture) && \
    PIP_INDEX="" && \
    [ "$ARCH" = "amd64" ] && PIP_INDEX="--index-url https://download.pytorch.org/whl/cu130"; \
    uv pip install --system --no-cache \
        'torch==2.11.*' \
        'torchvision==0.26.*' \
        'torchaudio==2.11.*' \
        $PIP_INDEX && \
    \
    # -- Jupyter core + Node.js --
    mamba install --yes --quiet \
    'nodejs==24.*' \
    'notebook==7.6.*' \
    'jupyterlab==4.6.*' \
    'jupyterhub==5.5.*' \
    'ipykernel=7.3.*' \
    && \
    mamba clean --all -f -y && \
    npm cache clean --force && \
    jupyter lab clean && \
    npm install -g agent-browser && \
    fix-permissions "${CONDA_DIR}" && \
    fix-permissions "/home/${NB_USER}"

ENV JUPYTER_PORT=8888
EXPOSE $JUPYTER_PORT

USER ${NB_UID}
    
# ============================================================
# Programming language kernels + Course packages + UI extensions
# ============================================================
RUN \
    mamba install --quiet --yes \
    'openjdk=25.*' \
    'ant=1.10.*' \
    'jupyterlab-myst=2.7.*' \
    'jupyterlite=0.8.*' \
    && \
    # jupyterlite-sphinx 0.22.1 pins jupyterlite-core<0.8 (conflicts with jupyterlite 0.8)
    # Install via pip --no-deps to force compatibility; other deps already satisfied by mamba
    uv pip install --system --no-cache --no-deps 'jupyterlite-sphinx==0.22.*' \
    && \
    # yasi (calysto-scheme dep) uses node.s on ast.Constant removed in Python 3.14
    # Patch only .s] and .s) and .s, patterns (AST attribute access), not .sort/.split etc.
    curl -sL "https://files.pythonhosted.org/packages/3a/58/e369cc04c658f6fbf53de6f05163fc6adbb16694ff7ae56886875fe30c07/yasi-2.1.2.tar.gz" -o /tmp/yasi.tar.gz && \
    mkdir -p /tmp/yasi-src && tar xzf /tmp/yasi.tar.gz -C /tmp/yasi-src && \
    find /tmp/yasi-src -name '*.py' -exec sed -i "s/\.s\]/\.value\]/g; s/\.s)/\.value)/g; s/\.s,/\.value,/g; s/\.s$/\.value/g" {} + && \
    uv pip install --system --no-cache /tmp/yasi-src/yasi-2.1.2 && \
    rm -rf /tmp/yasi.tar.gz /tmp/yasi-src && \
    uv pip install --system --no-cache 'calysto-scheme==1.4.*' && \
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
    'matplotlib-base=3.11.*' \
    'ipympl=0.10.*' \
    'sympy=1.14.*' \
    && \
    mamba clean --all -f -y && \
    npm cache clean --force && \
    fix-permissions "${CONDA_DIR}"

# Rust kernel (evcxr_jupyter)
# Ubuntu 26.04 ships rustc 1.93 + cargo via apt — no rustup needed.
# evcxr_jupyter v0.21.1 compiles from source via cargo (~3-5 min).
# PINNED: 0.22.0 depends on rust-analyzer crates (ra_ap_*) that require rustc 1.95,
# which apt's rustc 1.93 lacks -> build failure. 0.21.1 is the last version that
# compiles against apt's rustc. Keep the pin; don't let cargo re-resolve to latest.
USER root
RUN apt-get update --yes && \
    apt-get install --yes --no-install-recommends rustc cargo && \
    apt-get clean && rm -rf /var/lib/apt/lists/* && \
    cargo install evcxr_jupyter --version 0.21.1 --root /usr/local && \
    evcxr_jupyter --install && \
    mkdir -p "${CONDA_DIR}/share/jupyter/kernels" && \
    mv "/home/${NB_USER}/.local/share/jupyter/kernels/rust" \
       "${CONDA_DIR}/share/jupyter/kernels/rust" && \
    rm -rf /root/.cargo /home/${NB_USER}/.cargo && \
    fix-permissions "${CONDA_DIR}"
USER ${NB_UID}

# ============================================================
# JupyterLab extensions + LSP + Formatters
# ============================================================
RUN mamba install --quiet --yes \
    'websockify=0.13.*' \
    'jupyter-vscode-proxy=0.7.*' \
    'jupytext=1.18.*' \
    'black=25.1.*' \
    'jupyterlab_code_formatter=3.0.*' \
    'jupyterlab-lsp=5.3.*' \
    'jupyter-resource-usage=1.2.*' \
    'nbgitpuller==1.3.*' \
    'jupyterlab-git==0.54.*' \
    && \
    uv pip install --system --no-cache \
    'python-lsp-server[all]==1.15.*' \
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
RUN uv pip install --system --no-cache \
    'jupyter-remote-desktop-proxy==3.0.*' \
    && \
    mamba clean --all -f -y && \
    fix-permissions "${CONDA_DIR}" && \
    # Patch VNC xstartup: export ELECTRON_DISABLE_SANDBOX=1 (prevents VS Code renderer crash)
    # and copy XFCE config from /etc/skel if missing (since /home/jovyan is a mounted PVC).
    sed -i '1a export ELECTRON_DISABLE_SANDBOX=1' \
        "${CONDA_DIR}/lib/python3.14/site-packages/jupyter_remote_desktop_proxy/share/xstartup" && \
    sed -i '2a cp -rn /etc/skel/.config/xfce4 ~/".config/xfce4" 2>/dev/null || true' \
        "${CONDA_DIR}/lib/python3.14/site-packages/jupyter_remote_desktop_proxy/share/xstartup"

# ============================================================
# AI/ML packages — langchain, transformers, MLC, etc.
# ============================================================
RUN mamba install --quiet --yes \
    'git-lfs=3.7.*' \
    'nvitop=1.7.*' \
    'gpustat=1.1.*' \
    'pyarrow=25.0.*' \
    'pypdf=5.*' \
    && \
    uv pip install --system --no-cache \
    --no-build-isolation \
    'langchain==1.3.*' \
    'langchain-openai==1.4.*' \
    'sentence-transformers==5.6.*' \
    'transformers==5.14.*' \
    'accelerate==1.14.*' \
    'bitsandbytes==0.50.*' \
    'tiktoken==0.13.*' \
    'datasets==4.8.*' \
    'optimum==2.2.*' \
    && \
    # COMMENTED OUT — GPTQ quantization tool not needed for divenb.
    # uv pip install --system --no-cache \
    # 'gptqmodel==7.3.*' \
    # 'scikit_build_core' \
    # 'setuptools_scm' \
    # 'cython' \
    # && \
    # COMMENTED OUT — MLC-LLM on-device inference not needed (vLLM serves models).
    # uv pip install --system --no-build-isolation --pre -U \
    #     -f https://mlc.ai/wheels mlc-llm-nightly-cu130 mlc-ai-nightly-cu130 \
    # && \
    mamba clean --all -f -y && \
    fix-permissions "${CONDA_DIR}"

# ============================================================
# Data science + visualization + UI extensions — merged
# ============================================================
RUN mamba install --quiet --yes \
    altair bokeh bottleneck blas cython h5py numba patsy \
    pytables seaborn scikit-learn sqlalchemy statsmodels xlrd \
    && \
    uv pip install --system --no-cache tables \
    && \
    mamba install --quiet --yes \
    'jupyter-archive=3.5.*' \
    && \
    uv pip install --system --no-cache \
    'jupyterlab_theme_solarized_dark' \
    'theme-darcula' \
    && \
    mamba clean --all -f -y && \
    fix-permissions "${CONDA_DIR}"


# Ollama
# COMMENTED OUT — redundant with vLLM serving Socrates.
# USER root
# RUN curl -fsSL https://ollama.com/install.sh | sh

# Hermes Agent needs root for apt-get (libolm-dev)
USER root
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
RUN git clone --depth 1 --branch v2026.9.14 https://github.com/NousResearch/hermes-agent.git /tmp/hermes-agent && \
    # hermes requires setuptools>=77 for SPDX license expression
    uv pip install --system --no-cache 'setuptools>=77' && \
    # Patch: fix the ACP cancel (stop button) None-crash (still present in v2026.9.14).
    # When interrupted mid-tool-loop, run_conversation returns final_response=None;
    # .get("final_response", "") returns None (key exists, default ignored), then
    # None.startswith() raises AttributeError → "Internal error" → stop button errors.
    # (The old "junk output after cancel" bug 2 was refactored upstream in 0.21.x: the
    #  block now uses a local `suppress` var and the INTERRUPT_WAITING_FOR_MODEL_PREFIX
    #  import is still in use — so that sed no longer applies. Re-verify this sed after
    #  the next hermes bump: it must match exactly once.)
    sed -i 's/final_response = result.get("final_response", "")/final_response = result.get("final_response") or ""/' \
        /tmp/hermes-agent/acp_adapter/server.py && \
    # Build the dashboard web UI (required for jupyter-hermes-proxy)
    cd /tmp/hermes-agent/web && \
    npm install && \
    npm run build && \
    cd / && \
    # Install hermes-agent into the conda environment
    # hermes setup.py blocks bdist_wheel outside Nix; set HERMES_NIX_BUILD=1 to allow wheel build in Docker
    HERMES_NIX_BUILD=1 uv pip install --system --no-cache '/tmp/hermes-agent[acp]' && \
    # pip install doesn't include web_dist (not in package-data), so copy it manually.
    # Required by jupyter-hermes-proxy which runs `hermes dashboard --skip-build`.
    cp -r /tmp/hermes-agent/hermes_cli/web_dist /opt/conda/lib/python3.14/site-packages/hermes_cli/web_dist && \
    # Install Matrix adapter dependencies (mautrix[encryption], etc.)
    # libolm-dev provides system olm library; CMAKE_POLICY_VERSION_MINIMUM
    # needed because python-olm's CMakeLists requires CMake < 3.5 (removed in 26.04)
    apt-get update --yes && \
    apt-get install --yes --no-install-recommends libolm-dev && \
    apt-get clean && rm -rf /var/lib/apt/lists/* && \
    CMAKE_POLICY_VERSION_MINIMUM=3.5 uv pip install --system --no-cache \
        'mautrix[encryption]==0.21.*' \
        'aiosqlite==0.22.*' \
        'asyncpg==0.31.*' \
        'aiohttp-socks==0.11.*' \
        && \
    fix-permissions "${CONDA_DIR}"

# Patch: hermes-agent v2026.8.31 (0.21.0) daemon_pool.py is broken on Python 3.14
#
# tools/daemon_pool.py ships DaemonThreadPoolExecutor._adjust_thread_count
# hard-coded to the CPython 3.8-3.13 ThreadPoolExecutor private API
# (self._initializer / self._initargs passed to _worker). CPython 3.14
# removed those attributes; the initializer now lives in a WorkerContext
# built via self._create_worker_context() and _worker's signature changed to
# _worker(exec_ref, ctx, work_queue). Result: the FIRST submit() on any
# DaemonThreadPoolExecutor raises
#     AttributeError: 'DaemonThreadPoolExecutor' object has no attribute
#     '_initializer'
# because hermes routes EVERY tool call through that pool
# (agent/tool_executor.py), so every tool (MCP, terminal, read_file,
# web_search, execute_code) fails for the lifetime of the session. This
# image runs Python 3.14, so the %%hermes persona was completely broken;
# hosts on Python <= 3.13 are unaffected.
#
# Fix: overwrite the installed module with hermes_daemon_pool_314.py
# (byte-identical to upstream except a sys.version_info >= (3, 14) guard in
# _adjust_thread_count). Gate: hermes_daemon_pool_gate.py then exercises the
# PATCHED (installed) pool — submit, results, daemon flag, _threads_queues
# absence, initializer path, and a wedged-worker exit check in a subprocess
# pinned to site-packages — failing the build on any regression.
# Re-verify this whole step after any hermes-agent version bump.
COPY hermes_daemon_pool_314.py /tmp/hermes-daemon-pool-314.py
COPY hermes_daemon_pool_gate.py /tmp/hermes-daemon-pool-gate.py
RUN mv /tmp/hermes-daemon-pool-314.py "${CONDA_DIR}/lib/python3.14/site-packages/tools/daemon_pool.py" && \
    # PYTHONDONTWRITEBYTECODE: keep the gate (and its subprocess) from
    # dropping root-owned .pyc files into site-packages.
    PYTHONDONTWRITEBYTECODE=1 python3 /tmp/hermes-daemon-pool-gate.py "${CONDA_DIR}/lib/python3.14/site-packages" && \
    # This stage runs as root, but later fix-permissions runs as ${NB_USER}
    # and cannot chown/chmod root-owned files — hand ownership over now.
    chown "${NB_UID}:${NB_GID}" "${CONDA_DIR}/lib/python3.14/site-packages/tools/daemon_pool.py" && \
    rm -f /tmp/hermes-daemon-pool-gate.py

# ------------------------------------------------------------------
# ACP turn-stall watchdog — fixes %%hermes "Redirected the active turn".
#
# Root cause: the `hermes acp` server serializes turns per session via
# state.is_running and folds any prompt arriving during an in-flight turn into
# it ("active-turn redirect"), replying "Redirected the active turn with your
# correction." When the in-flight turn wedges (dropped/hung LLM stream, or a
# stuck approval/tool call), NOTHING clears is_running — the exception path
# only covers exceptions, not hangs — so every later prompt is permanently
# swallowed and answered with nothing; the magic then wrote that ack into the
# notebook as the "answer" (the "%%hermes is broken" symptom).
#
# Fix (hermes-agent / acp_adapter, installed above): a server-side watchdog
# thread that hard-interrupts a session with no client-visible activity for
# HERMES_ACP_TURN_STALL_TIMEOUT seconds (default 300), reusing the existing
# cancel() path (cancel_event + request_hard_interrupt). Activity-based, so a
# long healthy streaming turn is never touched. The companion magic-side
# changes (redirect-ack cancel+retry-once, stderr drain, meaningful timeout)
# ship via the jupyter-ai-hermes-magics build context below.
#
# Re-verify this whole step after any hermes-agent version bump: the patch
# script is assertion-guarded and fails the build if any anchor drifted.
COPY patch_acp_adapter.py /tmp/hermes-acp-watchdog-patch.py
COPY hermes_acp_watchdog_gate.py /tmp/hermes-acp-watchdog-gate.py
RUN SP="${CONDA_DIR}/lib/python3.14/site-packages" && \
    # 1) apply the assertion-guarded patch (non-zero exit => build fails if
    #    the upstream file drifted and the patch needs re-review).
    python3 /tmp/hermes-acp-watchdog-patch.py "$SP" && \
    # 2) functional gate: drive the REAL patched acp_adapter with a fake agent
    #    (no LLM) — a wedged turn must be rescued by the watchdog (redirect
    #    ack -> hard-interrupt -> retry succeeds) and a healthy streaming turn
    #    must NOT be interrupted. Exits non-zero => build fails.
    HERMES_HOME=/tmp/hermes-wd-home PYTHONDONTWRITEBYTECODE=1 \
        python3 /tmp/hermes-acp-watchdog-gate.py && \
    # 3) hand ownership of the patched files (and their .orig-hermes-wd
    #    rollback backups) to the notebook user — a later fix-permissions
    #    runs as ${NB_USER} and cannot chown root-owned files.
    chown "${NB_UID}:${NB_GID}" \
        "$SP/acp_adapter/server.py" \
        "$SP/acp_adapter/session.py" \
        "$SP/acp_adapter/server.py.orig-hermes-wd" \
        "$SP/acp_adapter/session.py.orig-hermes-wd" && \
    rm -f /tmp/hermes-acp-watchdog-patch.py /tmp/hermes-acp-watchdog-gate.py

USER ${NB_UID}

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

# install-vscode-extension script (needed for versioned VSIX downloads from Marketplace)
COPY install-vscode-extension /usr/local/bin/install-vscode-extension
RUN chmod a+rx /usr/local/bin/install-vscode-extension

# Code-server extensions (via install-vscode-extension for versioned downloads)
RUN for ext in \
    formulahendry.acp-client@0.2.0 \
    ; do \
    install-vscode-extension "$ext" --extensions-dir /usr/lib/code-server/lib/vscode/extensions; \
    done && \
    sed -i 's/bn=ln(dn,\["navigator"\])/bn=function(){return navigator}/' \
        /usr/lib/code-server/lib/vscode/extensions/formulahendry.acp-client-*/dist/extension.js

# DeepSeek Harness for VS Code (Jager.dsh-vscode) — community extension providing
# the @dsh chat participant in code-server. Shipped as a checked-in VSIX (the
# marketplace vspackage download is gzip-wrapped; a plain `code-server
# --install-extension <publisher>.<name>` also fails because code-server does not
# query the VS Marketplace by default). The VSIX is version-pinned in the repo
# (extensions/dsh-vscode-0.13.17.vsix); bump the file + this line together.
COPY --chown=${NB_USER}:${NB_GID} extensions/dsh-vscode-0.13.17.vsix /tmp/dsh-vscode.vsix
COPY --chown=${NB_USER}:${NB_GID} assets/dsh-icon-whale.png /tmp/dsh-icon-whale.png
RUN code-server --extensions-dir /usr/lib/code-server/lib/vscode/extensions \
        --install-extension /tmp/dsh-vscode.vsix --force \
    && rm -f /tmp/dsh-vscode.vsix \
    && DSH_EXT=$(ls -d /usr/lib/code-server/lib/vscode/extensions/jager.dsh-vscode-* | head -1) \
    # The bundled media/icon.png is a FULL-COLOR app icon (blue gradient, opaque
    # canvas). VS Code renders activity-bar / sidebar-view icons as MONOCHROME
    # CSS masks using only the alpha channel, tinted with the theme color — so
    # an opaque-canvas app icon shows as a solid filled square ("blank" icon).
    # Swap in assets/dsh-icon-whale.png: a transparent-background whale glyph
    # (alpha = the whale only) extracted from the original icon. It tints
    # correctly on dark AND light themes. Re-extract if the extension's brand
    # changes; keep the name stable so this line doesn't need updating.
    && cp -f /tmp/dsh-icon-whale.png "$DSH_EXT/media/icon.png" \
    && chown ${NB_USER}:${NB_GID} "$DSH_EXT/media/icon.png" \
    && rm -f /tmp/dsh-icon-whale.png \
    && echo "dsh-vscode extension: $(basename "$DSH_EXT")" \
    && echo "dsh icon: $(wc -c < "$DSH_EXT/media/icon.png") bytes (monochrome whale glyph)"

# Jupyter AI
RUN uv pip install --system --no-cache \
    'jupyter-ai==3.1.*' \
    # 'jupyter-ai-jupyternaut' \
    # 'jupyter-ai-magic-commands' \
    && \
    mamba clean --all -f -y && \
    fix-permissions "${CONDA_DIR}"

# Pin jupyter_server_documents to 0.3.0 (jupyter-ai has no version constraint and
# uv resolves to 0.2.5 by default). 0.3.0 hardcodes serverSideExecution="true",
# which routes cell execution through a server-side handler with allow_stdin=False,
# breaking input(). Patch to "false" to use the standard kernel WebSocket instead.
RUN uv pip install --system --no-cache 'jupyter-server-documents==0.3.*' && \
    sed -i 's/page_config\["serverSideExecution"\] = "true"/page_config\["serverSideExecution"\] = "false"/' "$(python3 -c 'import jupyter_server_documents.app as a; print(a.__file__)')" && \
    fix-permissions "${CONDA_DIR}"

# Install jupyter-ai-hermes and jupyter-hermes-proxy from build contexts
# The Makefile passes --build-context for each submodule, avoiding symlinks
# and the "too many links" buildkit error.
COPY --from=jupyter-ai-hermes --chown=${NB_USER}:${NB_GID} . /tmp/jupyter-ai-hermes
COPY --from=jupyter-hermes-proxy --chown=${NB_USER}:${NB_GID} . /tmp/jupyter-hermes-proxy
RUN uv pip install --system --no-cache \
    /tmp/jupyter-ai-hermes \
    /tmp/jupyter-hermes-proxy \
    && \
    # Pin agent-client-protocol to 0.9.0 AFTER jupyter-ai-hermes install.
    # jupyter-ai-hermes -> jupyter-ai-acp-client -> agent-client-protocol>=0.11,
    # but Hermes acp_adapter requires 0.9.0 (needs ModelInfo in acp.schema).
    # 0.9.0 works for both — jupyter-ai-acp-client's >=0.11 constraint is overly strict.
    uv pip install --system --no-cache 'agent-client-protocol==0.9.0' && \
    rm -rf /tmp/jupyter-ai-hermes /tmp/jupyter-hermes-proxy && \
    fix-permissions "${CONDA_DIR}"

# Install jupyter-dsh-proxy (JupyterLab launcher tile for the dsh web UI) from
# its build context. URL-mode proxy: it points at the dsh web server started by
# the 41-dsh-web boot hook (shared with the VS Code extension instance). The
# entry point is auto-discovered by jupyter-server-proxy — no extra config.
COPY --from=jupyter-dsh-proxy --chown=${NB_USER}:${NB_GID} . /tmp/jupyter-dsh-proxy
RUN uv pip install --system --no-cache /tmp/jupyter-dsh-proxy && \
    rm -rf /tmp/jupyter-dsh-proxy && \
    fix-permissions "${CONDA_DIR}"

# Patch jupyter-ai-tools AFTER all installs (jupyter-ai-hermes reinstalls it).
# _resolve_cell_id misidentifies numeric cell IDs as indices: JupyterLab 4+ YDoc
# cell IDs can be short numeric strings (e.g. "22334524"). _is_index_like() returns
# True for any numeric string, so such cell IDs are treated as array indices →
# "Invalid cell index" → run_cell/select_cell fail. Fix: only treat as index if
# value < 10000 (larger numbers are cell IDs, not indices).
RUN NBKIT="$(python3 -c 'import jupyter_ai_tools.toolkits.notebook as m; print(m.__file__)')" && \
    sed -i 's/    elif _is_index_like(cell_id_or_index):/    elif _is_index_like(cell_id_or_index) and int(cell_id_or_index) < 10000:/' "$NBKIT" && \
    fix-permissions "${CONDA_DIR}"

# Install cppmanlite from build context (submodule, same pattern as jupyter-ai-hermes)
COPY --from=cppmanlite --chown=${NB_USER}:${NB_GID} . /tmp/cppmanlite
RUN uv pip install --system --no-cache /tmp/cppmanlite && \
    rm -rf /tmp/cppmanlite && \
    fix-permissions "${CONDA_DIR}"

# Install jupyterlab-pwa from build context (PWA support: manifest, service worker, installability)
COPY --from=jupyterlab-pwa --chown=${NB_USER}:${NB_GID} . /tmp/jupyterlab-pwa
RUN uv pip install --system --no-cache /tmp/jupyterlab-pwa && \
    rm -rf /tmp/jupyterlab-pwa && \
    fix-permissions "${CONDA_DIR}"

# Install jupyter-ai-hermes-magics from build context (%%hermes cell magic)
COPY --from=jupyter-ai-hermes-magics --chown=${NB_USER}:${NB_GID} . /tmp/jupyter-ai-hermes-magics
RUN uv pip install --system --no-cache /tmp/jupyter-ai-hermes-magics && \
    rm -rf /tmp/jupyter-ai-hermes-magics && \
    fix-permissions "${CONDA_DIR}"

# ──────────────────────────────────────────────────────────────────────────
# DeepSeek Harness (dsh) + dsh-openai-shim
#
# Layering (IMPORTANT): the dsh runtime (~262MB, self-contained Node SEA) and
# the shim are installed into the CONDA ENV (/opt/conda) — the ephemeral image
# layer — using `uv pip install --system` (shim) and `npm i -g` (dsh runtime).
# Never `--user`, never ~/.local. Nothing in this block touches the user home.
# Only DSH_HOME ($HOME/.dsh) is written by dsh itself at RUNTIME (profiles/
# sessions/user plugins) on the NFS-mounted home. A fresh home is fine: dsh
# auto-initializes its profile skeleton on first use.
#
#   @deepseek-ai/dsh (npm) → the complete dsh CLI + Web UI + ACP + 262MB runtime
#                            (replaces deepseek-harness-sdk 0.1.5rc1 which was
#                            the SDK-focused build missing web-app frontend)
#   dsh-openai-shim        → zero-dep OpenAI-compatible proxy (build context);
#                            remaps reasoning_effort + clamps max_tokens so dsh's
#                            DeepSeek route works against Socrates/LiteLLM/sglang
#   pnpm                   → needed ONLY for `dsh plugin add`; running dsh needs no pnpm
#
# The npm `dsh` reads DEEPSEEK_BASE_URL + DEEPSEEK_API_KEY env at runtime
# (confirmed in source: "DEEPSEEK_BASE_URL wins when set"), so the spawner-
# injected env (→ :8090 shim) auto-routes all dsh LLM calls through the shim
# without any profile patch.
# ──────────────────────────────────────────────────────────────────────────
COPY --from=dsh-openai-shim --chown=${NB_USER}:${NB_GID} . /tmp/dsh-openai-shim
# Hard install: shim (pip) + dsh npm distro (npm -g) + pnpm, all into the
# conda env (ephemeral layer). Node 24 is already in conda (line ~319).
#   --cache /tmp/dsh-npm-cache: the in-image /home/${NB_USER}/.npm is left
#   root-owned by an earlier root step, so npm's default cache EACCES as ${NB_UID};
#   using an ephemeral cache sidesteps it.
#   --force: overwrites the conda bin/dsh if a previous layer left one (e.g.
#   the PyPI deepseek-harness-sdk that 0.2.48-0.2.50 installed).
RUN uv pip install --system --no-cache /tmp/dsh-openai-shim \
    && npm install -g --force --no-fund --no-audit --cache /tmp/dsh-npm-cache \
        '@deepseek-ai/dsh@0.1.5-rc.2' \
    && npm install -g --no-fund --no-audit --cache /tmp/dsh-npm-cache pnpm \
    && rm -rf /tmp/dsh-openai-shim /tmp/dsh-npm-cache \
    && fix-permissions "${CONDA_DIR}"
# Non-fatal sanity: surface the resolved paths/versions in the build log.
RUN echo "dsh CLI:  $(command -v dsh || echo 'MISSING — check PATH') v$(dsh --version 2>/dev/null | head -1)" \
    && echo "dsh web: $(dsh web --help 2>&1 | head -1)" \
    && echo "pnpm:   $(pnpm --version 2>/dev/null || echo 'MISSING')" \
    && echo "shim:   $(command -v dsh-openai-shim || echo 'MISSING')"

# ──────────────────────────────────────────────────────────────────────────
# dsh web UI: DISABLE the launch-token/cookie requirement (divendb-only).
# `dsh --profile web` mints a random launch token and gates the page + every
# /api + WebSocket call behind a token->signed-cookie exchange; there is no
# flag/env/config to turn it off. In this image the server binds 127.0.0.1
# only and is reachable ONLY via the code-server port-forward, which is itself
# behind JupyterHub auth (and implies full pod shell) — so the token adds no
# real security, only friction. The patch removes the token/cookie requirement
# while KEEPING the loopback host-fence (isTrustedApiRequest -> 403), the real
# network boundary. Deterministic + loud: if a future dsh version bumps change
# the source shape, the assertions below fail the build rather than silently
# shipping a token-gated image. (Divendb-specific; not a dsh upstream change.)
# ──────────────────────────────────────────────────────────────────────────
COPY --chown=${NB_USER}:${NB_GID} dsh-web-tokenless.py /tmp/dsh-web-tokenless.py
RUN python /tmp/dsh-web-tokenless.py \
    && rm -f /tmp/dsh-web-tokenless.py \
    && grep -c "dsh-web-tokenless" /opt/conda/lib/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai/dsh-client-connection/lib/index.js

# ──────────────────────────────────────────────────────────────────────────
# dsh web UI: make it work under a URL SUBPATH (divendb-only, build-time).
# The `dsh --profile web` SPA is built to be served at the origin root (/).
# In the divendb image it is reached ONLY through the JupyterHub + code-server
# proxy path (…/vscode/proxy/3080/), so the browser — sitting at that subpath —
# would resolve the main bundle, plugin scripts, API and WebSocket against the
# site root → all 404 → blank page. (code-server's transparent proxy STRIPS the
# /vscode/proxy/<port> prefix before forwarding to 127.0.0.1:3080, so the
# server always sees root and is fine; the break is purely client-side URL
# resolution.) The patch makes every client-side URL base-aware:
#   · host-frontend-static: <base href="/"> -> "./", and /plugins/ -> ./plugins/
#   · client-connection / api-gateway / client-ui-chat / session-log-export:
#     base location.origin -> document.baseURI, and strip leading/trailing
#     slashes so new URL("api/x", base) and ws://…/api/remote.mux land under
#     the proxy prefix.
# Works at origin root too (no prefix → baseURI = origin+"/"). Deterministic:
# each replacement asserts its target appears exactly once, so a dsh version
# bump that changes the source shape fails the build loudly.
# ──────────────────────────────────────────────────────────────────────────
COPY --chown=${NB_USER}:${NB_GID} dsh-web-subpath.py /tmp/dsh-web-subpath.py
RUN python /tmp/dsh-web-subpath.py \
    && rm -f /tmp/dsh-web-subpath.py \
    && for f in \
        dsh-host-frontend-static/lib/index.js \
        dsh-client-connection/lib/client.js \
        dsh-api-gateway/lib/client.js \
        dsh-client-ui-chat/lib/client.js \
        dsh-session-log-export/lib/client.js; do \
        node --check /opt/conda/lib/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai/$f \
        || { echo "SYNTAX ERROR after subpath patch in $f"; exit 1; }; \
      done \
    && grep -rl "dsh-web-subpath" /opt/conda/lib/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai --include=*.js | wc -l

# ──────────────────────────────────────────────────────────────────────────
# NOTE: the jupyter-ai-dsh ACP *persona* was removed (0.2.49). dsh is now used
# via the dsh-openai-shim proxy + the `Jager.dsh-vscode` code-server extension
# (in-editor @dsh chat, installed in the code-server extensions block below),
# not as a Jupyter AI persona.
# ──────────────────────────────────────────────────────────────────────────

# Install jupyter-python-tutor from build context (%%pytutor cell magic)
COPY --from=jupyter-python-tutor --chown=${NB_USER}:${NB_GID} . /tmp/jupyter-python-tutor
RUN uv pip install --system --no-cache /tmp/jupyter-python-tutor && \
    rm -rf /tmp/jupyter-python-tutor && \
    fix-permissions "${CONDA_DIR}"

# Install jupyter-cpp-tutor from build context (%%cpptutor cell magic)
COPY --from=jupyter-cpp-tutor --chown=${NB_USER}:${NB_GID} . /tmp/jupyter-cpp-tutor
RUN uv pip install --system --no-cache /tmp/jupyter-cpp-tutor && \
    rm -rf /tmp/jupyter-cpp-tutor && \
    fix-permissions "${CONDA_DIR}"

# Plotly + data viz + marimo + JupyterLab extensions + nbgrader + course widgets
#
# --build-constraints: hatchling<=1.32.1. hatchling is a build-ISOLATION dep (not
# a runtime dep — absent from the final env) pulled in to build nbgrader/marimo
# from source, whose build hook is hatch-jupyter-builder (stuck at 0.9.1, 2024).
# hatchling 1.32.3 (released 2026-09-17, after the 0.2.50 build) changed
# BuildHookInterface to a 2-param generic, so the old 1-param
# `JupyterBuildHook(BuildHookInterface[JupyterBuildConfig])` subclass raises
# "Too few arguments" at build time. 1.32.1 is the last compatible release and
# is what the working 0.2.50 image resolved. Pin is a build-constraint (not -c,
# which would leak hatchling into the runtime env).
RUN printf 'hatchling<=1.32.1\n' > /tmp/hatchling-build-constraints.txt && \
    mamba install --quiet --yes \
    'plotly=6.9.*' \
    'sqlglot=28.10.*' \
    'polars=1.43.*' \
    'duckdb=1.5.*' \
    && \
    uv pip install --system --no-cache \
    --build-constraints /tmp/hatchling-build-constraints.txt \
    'divewidgets' \
    'nbgrader@git+https://github.com/dive4dec/nbgrader.git@8e0b69a6da48856e6f180d27041b6e1c96602934' \
    'jdc' \
    'marimo[recommended]==0.23.*' \
    'git+https://github.com/dive4dec/jupyter-marimo-proxy@a493c16de8e47a29c8f82ff65b10ee9ae393606c' \
    'kaleido==0.2.*' \
    'jupyterlab-execute-time==3.3.*' \
    && \
    mamba install --quiet --yes \
    'xeus-cpp=0.10.*' \
    'xtensor=0.9.*' \
    'root=6.40.*' \
    'gxx_linux-64' \
    && \
    mamba clean --all -f -y && \
    fix-permissions "${CONDA_DIR}"

# Thonny 5 — Tkinter-based rewrite (apt's `thonny` is stuck at 4.1.7 / Qt).
# The conda env already ships tkinter 8.6 + jedi/pylint/docutils/asttokens/
# send2trash; uv pip pulls the remaining 5.0.0 deps (mypy, pyserial, wheel).
# Runs as ${NB_UID} like every other `uv pip install --system` block in this
# stage (the conda env is ${NB_UID}-owned).
RUN uv pip install --system --no-cache 'thonny==5.0.*' \
    && /opt/conda/bin/python -c "import importlib.metadata as m; v=m.version('thonny'); assert v.startswith('5.0'), v; print('thonny', v)" \
    && fix-permissions "${CONDA_DIR}"

# Thonny 5 desktop entry + icon. The PyPI wheel ships neither, and the system
# dirs /usr/share/{pixmaps,applications} are root-owned, so this needs root
# (the block above runs as ${NB_UID} and cannot write them).
USER root
RUN SP=$(/opt/conda/bin/python -c "import site; print(site.getsitepackages()[0])") \
    && mkdir -p /usr/share/pixmaps \
    && cp "${SP}/thonny/res/thonny.png" /usr/share/pixmaps/thonny.png \
    && printf '%s\n' \
        '[Desktop Entry]' 'Type=Application' 'Version=1.0' 'Name=Thonny' \
        'Comment=Python IDE for beginners' \
        'Exec=/opt/conda/bin/thonny %F' 'Icon=thonny' 'Terminal=false' \
        'Categories=Development;IDE;Python;' 'MimeType=text/x-python;' \
      > /usr/share/applications/org.thonny.Thonny.desktop \
    && (update-desktop-database /usr/share/applications 2>/dev/null || true)
USER ${NB_UID}

# Copy local files (scripts + configs)
COPY start.sh /usr/local/bin/
COPY start-notebook.sh start-singleuser.sh /usr/local/bin/
COPY jupyter_server_config.py docker_healthcheck.py /etc/jupyter/
COPY --chown="${NB_UID}:${NB_GID}" ipython_config.py "${CONDA_DIR}/etc/ipython/ipython_config.py"
# dsh OpenAI proxy boot hook — start.sh's run-hooks() runs /usr/local/bin/
# before-notebook.d/* as the notebook user right before exec'ing the server.
# CRITICAL: run-hooks() *sources* *.sh files but *executes* other executable
# files, so this hook is `40-dsh-proxy` (NO .sh) — an `exit` in a sourced .sh
# would kill start.sh before the Jupyter server starts. It must be committed
# executable (100755) so COPY preserves the exec bit (no chmod step — the
# active user is NB_UID and can't chmod the root-owned COPY output). Starts the
# shim from ~/.dsh/proxy.conf (default LiteLLM — DiveAI 404s on
# /chat/completions so it is not a valid default; student-overridable via
# dsh-proxy use ...). See the hook header.
COPY before-notebook.d /usr/local/bin/before-notebook.d

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
COPY --chown="${NB_UID}:${NB_GID}" jupyterlab_code_formatter_settings.json "${CONDA_DIR}/share/jupyter/labextensions/jupyterlab_code_formatter/schemas/jupyterlab_code_formatter/settings.json"
COPY --chown="${NB_UID}:${NB_GID}" jupyterlab_code_formatter_settings.json "${CONDA_DIR}/share/jupyter/labextensions/@jupyter-lsp/jupyterlab-lsp/schemas/@jupyter-lsp/jupyterlab-lsp/diagnostics.json"
COPY --chown="${NB_UID}:${NB_GID}" jupyter_server_config.d/ "${CONDA_DIR}/etc/jupyter/jupyter_server_config.d/"

# Disable news and update announcements
RUN jupyter labextension disable "@jupyterlab/apputils-extension:announcements"

RUN fix-permissions "/usr/lib/code-server/lib/vscode/extensions"

# Add Emscripten, CosmoCC to PATH (CUDA removed from PATH — toolkit commented out)
ENV PATH="/opt/emsdk:/opt/emsdk/upstream/emscripten:${PATH}:/opt/cosmocc/bin"
RUN chmod a+w /opt/emsdk/upstream/emscripten/cache

# --- Fix jupyterlab-myst on JupyterLab 4.6 (ydoc 4 singleton) -------------------
# Upstream fix (manifest-only, no JS change) landed on main in 97be567 (2026-06-20)
# but is unreleased as of 2026-09-05 (latest PyPI: 2.7.0, still declares ydoc ^3).
# Bug: https://github.com/jupyter-book/jupyterlab-myst/issues/296
#
# Lab 4.6's @jupyter/ydoc is a module-federation singleton pinned to ^4.0.0-b1
# (resolves to 4.0.0). myst 2.7.0 declares ^3.0.0, so the server-side compat gate
# (get_app_info -> _validate_compatibility, pure semver overlap vs core singletons)
# reports the extension `status: "error"`, its view factory never registers, and
# every .md notebook spins forever on the loading screen. The shipped JS bundles
# carry no ydoc version of their own (0 federation refs in static/*.js) — they
# consume the Lab core ydoc 4 singleton at runtime, exactly the ydoc-3-era case
# Lab's 4.6 migration docs say works. So the fix is the range declaration only.
#
# Placed at the END of the base stage (after all labextension installs) so the
# guard below validates the COMPLETE federated-extension set, not a subset.
#
# (1) Patch the installed extension manifest's ydoc range to accept 3 or 4.
# (2) Gate the build: fail loudly if ANY federated extension (other than the
#     deliberately-excluded @jupyter/nbgrader, see §8 below) still reports an
#     incompatibility, so a future Lab or myst bump can't silently ship a
#     broken .md path again.
#
# When jupyterlab-myst ships a release containing 97be567 (expected 2.8.0+),
# delete the manifest patch and simply pin jupyterlab-myst>=2.8; keep the guard.
RUN python - "$CONDA_DIR/share/jupyter/labextensions/jupyterlab-myst/package.json" <<'PYEOF'
import json, os, shutil, sys
mf = sys.argv[1]
if not os.path.exists(mf + ".orig"):
    shutil.copy(mf, mf + ".orig")           # auditable backup + instant revert
d = json.load(open(mf))
old = d["dependencies"]["@jupyter/ydoc"]
d["dependencies"]["@jupyter/ydoc"] = "^3.0.0||^4.0.0"
with open(mf, "w") as fh:
    json.dump(d, fh, indent=2); fh.write("\n")
print(f"jupyterlab-myst ydoc range: {old} -> {d['dependencies']['@jupyter/ydoc']}")
PYEOF
# Build-time guard: assert every federated extension passes the Lab compat check
# (nbgrader excluded on purpose — it needs a real upstream fix, not a manifest
# nudge; see §8). Fails the build with the exact conflict tuple otherwise.
RUN python - <<'PYEOF'
import os
from jupyterlab.commands import get_app_info, _validate_compatibility
lab_ext_path = os.path.join(os.environ["CONDA_DIR"], "share/jupyter/labextensions")
i = get_app_info(app_options={"labextensions_path": [lab_ext_path]})
bad = {}
for n, d in i["federated_extensions"].items():
    if n == "@jupyter/nbgrader":            # known-broken, non-blocking (see §8)
        continue
    e = _validate_compatibility(n, d["dependencies"], i["core_data"])
    if e:
        bad[n] = e
assert not bad, f"JupyterLab extension(s) incompatible with Lab core: {bad}"
print(f"OK: {len(i['federated_extensions']) - 1} federated extensions pass Lab compat (nbgrader excluded)")
PYEOF
# ---------------------------------------------------------------------------


# ============================================================
# Runtime pip → uv: replace pip with a uv wrapper so that both
# interactive `pip install foo` and programmatic calls go through uv.
# `python -m pip` retains the original pip as an escape hatch.
# conda/mamba install are completely unaffected.
# ============================================================
RUN mv /opt/conda/bin/pip /opt/conda/bin/pip.real && \
    printf '#!/bin/bash\nexec uv pip "${1:-install}" --system "${@:2}"\n' > /opt/conda/bin/pip && \
    chmod +x /opt/conda/bin/pip && \
    mv /opt/conda/bin/pip3 /opt/conda/bin/pip3.real 2>/dev/null || true && \
    ln -sf /opt/conda/bin/pip /opt/conda/bin/pip3

# Add pip→uv wrapper for interactive shells.
# In base env: use uv (faster; base pip is already replaced with a uv wrapper).
# In a user conda env: defer to that env's real pip so uv is not forced.
# UV_LINK_MODE=copy in ENV: suppress hardlink warnings (cache on NFS, target may be overlay or NFS).
USER root
RUN cat <<'EOF' >> /etc/bash.bashrc
pip() {
    if [[ "$CONDA_DEFAULT_ENV" == "base" || -z "$CONDA_DEFAULT_ENV" ]]; then
        local cmd="$1"; shift
        command uv pip "$cmd" --system --python "$(command -v python)" "$@"
    else
        command pip "$@"
    fi
}
pip3() {
    if [[ "$CONDA_DEFAULT_ENV" == "base" || -z "$CONDA_DEFAULT_ENV" ]]; then
        local cmd="$1"; shift
        command uv pip "$cmd" --system --python "$(command -v python)" "$@"
    else
        command pip3 "$@"
    fi
}
EOF
USER ${NB_UID}

# Install jupyter-storage-usage from pre-built wheel (server extension)
COPY jupyter_storage_usage-0.1.0-py3-none-any.whl /tmp/
RUN uv pip install --system --no-cache /tmp/jupyter_storage_usage-0.1.0-py3-none-any.whl && \
    fix-permissions "${CONDA_DIR}"

WORKDIR "${HOME}"


FROM prod AS default

USER ${NB_USER}


FROM prod AS collab

USER ${NB_UID}
