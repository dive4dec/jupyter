ARG ROOT_CONTAINER=ubuntu:24.04

FROM $ROOT_CONTAINER AS foundation

# Fix the UID conflict with user ubuntu when jovyan needs to be created later. 
# See https://bugs.launchpad.net/cloud-images/+bug/2005129
RUN touch /var/mail/ubuntu && chown ubuntu /var/mail/ubuntu && userdel -r ubuntu

# Fix: https://github.com/hadolint/hadolint/wiki/DL4006
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Avoid prompt for user input for installation of dependencies
ENV DEBIAN_FRONTEND=noninteractive

ARG NB_USER="jovyan"
ARG NB_UID="1000"
ARG NB_GID="100"

ENV CONDA_DIR=/opt/conda \
    SHELL=/bin/bash \
    NB_USER="${NB_USER}" \
    NB_UID=${NB_UID} \
    NB_GID=${NB_GID} \
    LC_ALL=C.UTF-8 \
    LANG=C.UTF-8 \
    LANGUAGE=C.UTF-8 \
    TZ=Asia/Hong_Kong
ENV PATH="${CONDA_DIR}/bin:${PATH}" \
    HOME="/home/${NB_USER}"

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


# A script to correct permissions after running certain commands
COPY fix-permissions /usr/local/bin/fix-permissions
RUN chmod a+rx /usr/local/bin/fix-permissions

# Create NB_USER with name jovyan user with UID=1000 and in the 'users' group
# and make sure these dirs are writable by the `users` group.
RUN echo "auth requisite pam_deny.so" >> /etc/pam.d/su && \
    sed -i.bak -e 's/^%admin/#%admin/' /etc/sudoers && \
    sed -i.bak -e 's/^%sudo/#%sudo/' /etc/sudoers && \
    useradd -l -m -s /bin/bash -N -u "${NB_UID}" "${NB_USER}" && \
    mkdir -p "${CONDA_DIR}" && \
    chown "${NB_USER}:${NB_GID}" "${CONDA_DIR}" && \
    chmod g+w /etc/passwd && \
    fix-permissions "${HOME}" && \
    fix-permissions "${CONDA_DIR}"

USER ${NB_UID}

# Pin python version here, or leave it empty for the latest version
ARG PYTHON_VERSION=3.11

# Pin micromamba version here, or leave it empty for the latest version
ARG MICROMAMBA_VERSION=2.0.0-0

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
    curl "${RELEASE_URL}" -o "${BIN_FOLDER}/mamba" -fsSL --compressed && \
    chmod +x "${BIN_FOLDER}/mamba"

USER root

ENV MAMBA_ROOT_PREFIX=${CONDA_DIR}

# Enable prompt color in the skeleton .bashrc before creating the default NB_USER
# hadolint ignore=SC2016
RUN sed -i 's/^#force_color_prompt=yes/force_color_prompt=yes/' /etc/skel/.bashrc && \
    # Add call to micromamba init script
    echo 'eval "$(mamba shell hook --shell bash)"' >> /etc/skel/.bashrc && \
    # fix https://github.com/jupyter/docker-stacks/issues/815
    cat /etc/skel/.bashrc >> /etc/bash.bashrc


USER ${NB_UID}

RUN if [ "${PYTHON_VERSION:-}" = "" ]; then PYTHON_SPECIFIER="python"; else PYTHON_SPECIFIER="python=${PYTHON_VERSION}"; fi && \
        mamba install --yes \
        "${PYTHON_SPECIFIER}" \
        'jupyter_core' \
        && \
        # Pin major.minor version of python
        mamba list python | sed 's/^[[:space:]]*//' | grep '^python ' | tr -s ' ' | cut -d ' ' -f 1,2 >> "${CONDA_DIR}/conda-meta/pinned" && \
        mamba clean --all -f -y && \
        fix-permissions "${CONDA_DIR}" && \
        fix-permissions "/home/${NB_USER}"

USER root

# Install all OS dependencies for notebook server that starts but lacks all
# features (e.g., download as all possible file formats)
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
    # Enable clipboard on Linux host systems
    xclip && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

### Desktop ###
RUN \
    apt-get update --yes && \
    apt-get install --yes --no-install-recommends \
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
    ;

# Install Jupyter Notebook, Lab, and Hub
WORKDIR /tmp

USER ${NB_UID}

RUN mamba install --yes \
    # code-server requirement
    'nodejs==22.9.*' \
    'notebook==7.2.*' \
    'jupyterlab==4.2.*' \
    'jupyterhub==5.0.*' \
    && \
    jupyter notebook --generate-config && \
    mamba clean --all -f -y && \
    npm cache clean --force && \
    jupyter lab clean && \
    fix-permissions "${CONDA_DIR}" && \
    fix-permissions "/home/${NB_USER}"

USER root

ENV JUPYTER_PORT=8888
EXPOSE $JUPYTER_PORT

### code-server ###
RUN wget -q https://code-server.dev/install.sh -O /tmp/install.sh && \
    sh /tmp/install.sh --version 4.93.1 && \
    fix-permissions "${HOME}" && \
    fix-permissions /usr/lib/code-server/ && \
    rm -rf ~/.cache/code-server/ && \
    rm -rf /tmp/install.sh

USER ${NB_UID}

RUN mamba install --quiet --yes \
    'websockify=0.11.*' \
    'jupyter-vscode-proxy=0.6' \
    'jupytext=1.16.*' \
    'nbgitpuller=1.2.*' \
    'black=24.4.*' \
    'jupyterlab_code_formatter=2.2.*' \
    'jupyterlab-lsp=5.1.*' \
    'python-lsp-server=1.11.*' \
    'jupyter-resource-usage==1.0.*' \
    && \
    pip install --quiet --no-cache-dir \
    'jupyterlab-git==0.50.*' \    
    'jupyterlab_filesystem_access==0.6.*' \
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

USER root

# Programming languages backends
RUN \
    apt-get update --yes && \
    apt-get install --yes --no-install-recommends \
    # C, C++
    build-essential \
    gdb \
    fpc-source \
    # SQL
    sqlite3 \
    # JAVA
    default-jdk default-jre \
    && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# MIT Scheme
COPY mit-scheme/ /tmp/mit-scheme/
RUN bash /tmp/mit-scheme/buildscript.sh

# For installing some jupyter kernels
RUN apt-get update --yes && \
    apt-get install --yes --no-install-recommends libzmq3-dev

USER ${NB_USER}

# Documentations with MyST
RUN \
    npm install -g \
    mystmd \
    && \
    npm cache clean --force

# Programming languages support
RUN \
    mamba install --quiet --yes \
    # C, C++
    'xeus-cling=0.15.*' \
    # Java
    'openjdk=22.0.*' \
    # Documentations
    'jupyterlite=0.4.*' \
    && \
    pip install --quiet --no-cache-dir \
    'calysto-scheme==1.4.*' \
    'jupyterlab-myst==2.4.*' \
    # Documentations
    'jupyterlite-sphinx==0.16.*' \ 
    'nbdev==2.3.*' \
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
    'manim=0.18.*' \
    'manimpango=0.5.*' \
    'pandas=2.2.*' \
    'matplotlib-base=3.8.*' \
    'ipympl=0.9.*' \
    'sympy=1.*' \
    && \
    pip install --quiet --no-cache-dir \
    'divewidgets' \
    'nbgrader==0.9.*' \
    && \
    mamba clean --all -f -y && \
    fix-permissions "${CONDA_DIR}"

USER root

# Maxima
COPY maxima/ /tmp/maxima/
RUN bash /tmp/maxima/buildscript.sh

COPY --chown=${NB_USER}:${NB_GID} quicklisp /tmp/quicklisp
RUN mkdir -p /opt/quicklisp && chown -R ${NB_USER} $_ && fix-permissions $_ && \
    mv /tmp/quicklisp/sbclrc /etc/
    
USER ${NB_USER}
RUN bash /tmp/quicklisp/buildscript.sh

# Dependencies for mystmd
USER root

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
RUN wget -q "https://github.com/TurboVNC/turbovnc/releases/download/3.1.2/turbovnc_3.1.2_amd64.deb" \
    -O /tmp/turbovnc_amd64.deb && \
    apt-get update --yes && \
    apt-get install --yes --no-install-recommends \
    /tmp/turbovnc_amd64.deb \
    && \
    rm /tmp/turbovnc_amd64.deb && \
    ln -s /opt/TurboVNC/bin/* /usr/local/bin/ && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

USER ${NB_USER}

RUN pip install --quiet --no-cache-dir \
    'jupyter-remote-desktop-proxy==2.0.*' \
    # git+https://github.com/b-data/jupyter-remote-desktop-proxy.git@QGIS \
    && \
    mamba clean --all -f -y && \
    fix-permissions "${CONDA_DIR}"

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
    mamba clean --all -f -y && \
    fix-permissions "${CONDA_DIR}"

# CUDA
RUN MAMBA_NO_LOW_SPEED_LIMIT=1 mamba install --quiet --yes \
    'cuda' \
    && \
    mamba clean --all -f -y && \
    fix-permissions "${CONDA_DIR}"

 

# Tensorflow
RUN pip install --quiet --no-cache-dir \
    'tensorflow==2.15.*' \
    'tensorflow-datasets==4.9.*' \
    'flax==0.8.*' \
    'tensorflow-hub==0.16.*' \
    'tensorflow-decision-forests==1.8.*' \
    && \
    pip install --quiet --no-cache-dir --no-deps \
    'tensorflowjs==4.20.*' \
    && \
    fix-permissions "${CONDA_DIR}"

# PyTorch
RUN pip install --quiet --no-cache-dir \
    'torch==2.3.*' \
    'torchvision==0.18.*' \
    'torchaudio==2.3.*' \
    && \
    fix-permissions "${CONDA_DIR}"

# Deep learning tools
RUN pip install --quiet --no-cache-dir \
    'nvitop' \
    'gpustat' \
    'jdc' \
    'jupyterlab-tensorboard-pro' \
    && \
    fix-permissions "${CONDA_DIR}"

# LLM
USER root

RUN curl -fsSL https://ollama.com/install.sh | sh

USER ${NB_USER}

RUN pip install --quiet --no-cache-dir --pre -U -f https://mlc.ai/wheels mlc-llm-nightly-cu121 mlc-ai-nightly-cu121 && \
    pip install --quiet --no-cache-dir \
    'langchain_openai' \
    'jupyter_ai' \
    'openai' \
    'ollama' \
    'vllm' \
    'chromadb' \
    'tiktoken' \
    'nvitop' \
    'gpustat' \
    'jdc' \
    'jupyterlab-tensorboard-pro' \
    && \
    mamba install --quiet --yes \
    'git-lfs' \
    && \
    mamba clean --all -f -y && \
    fix-permissions "${CONDA_DIR}"

RUN pip install --quiet --no-cache-dir \
    'transformers' \
    'torchtune' \
    'accelerate' \
    'evaluate' \
    && \
    fix-permissions "${CONDA_DIR}"

# Other UI enhancements
RUN \
    mamba install --quiet --yes \
    'jupyter-archive=3.4.*' \
    && \
    pip install --quiet --no-cache-dir \
    # 'jupyterlab-unfold==0.3.*' \
    # 'jupyterlab-favorites==3.2.*' \
    'jupyterlab-scenes==2.0.*' \
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

# needed for nbgrader
RUN pip install --quiet --no-cache-dir \
    'tornado==6.4.*' \
    && \
    fix-permissions "${CONDA_DIR}"

# Copy local files as late as possible to avoid cache busting
COPY start.sh /usr/local/bin/
COPY start-notebook.sh start-singleuser.sh install-vscode-extension /usr/local/bin/
# Currently need to have both jupyter_notebook_config and jupyter_server_config to support classic and lab
COPY jupyter_server_config.py docker_healthcheck.py /etc/jupyter/

# Code extensions
RUN for ext in \
        ms-python.python \
        ms-python.pylint \
        ms-toolsai.jupyter \
        ms-toolsai.vscode-jupyter-powertoys \
        ms-python.black-formatter \
        streetsidesoftware.code-spell-checker@4.0.13 \
        hediet.vscode-drawio \
        eamodio.gitlens \
        donjayamanne.githistory \
        mhutchie.git-graph \
        waderyan.gitblame \
        codezombiech.gitignore \
        ziyasal.vscode-open-in-github \
        alefragnani.project-manager \
        ziyasal.vscode-open-in-github \
        ; do \
        code-server --extensions-dir /usr/lib/code-server/lib/vscode/extensions --install-extension "$ext"; \
    done

RUN for ext in \
    GitHub.copilot-chat@0.20.3 \
    GitHub.copilot@1.234.0 \
    Continue.continue@0.8.52 \
    ; do \
    install-vscode-extension "$ext" --extensions-dir /usr/lib/code-server/lib/vscode/extensions; \
    done

# Other UI enhancements
RUN \
    mamba install --quiet --yes \
    'gh' \
    && \
    mamba clean --all -f -y && \    
    fix-permissions "${CONDA_DIR}"

# ----------------------------------------------------------

FROM foundation AS prod

COPY --from=base /etc/ /etc/
COPY --from=base /usr/ /usr/
COPY --from=base /var/ /var/
COPY --from=base /home/ /home/
COPY --from=base /opt/ /opt/

# set Mamba root prefix
ENV MAMBA_ROOT_PREFIX=${CONDA_DIR}

USER root

# Install VS Code
RUN wget -qO- https://go.microsoft.com/fwlink/?LinkID=760868 -O /tmp/vscode.deb && \
    echo "code code/add-microsoft-repo boolean true" | sudo debconf-set-selections && \
    apt-get update --yes && \
    apt-get install --yes --no-install-recommends gnupg /tmp/vscode.deb && \
    apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/vscode.deb

# Install Google Chrome
RUN wget -qO- https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb -O /tmp/google-chrome.deb && \
    apt-get update --yes && \
    apt-get install --yes --no-install-recommends /tmp/google-chrome.deb && \
    apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/google-chrome.deb

# Modify code.desktop to include --no-sandbox
RUN sed -i 's|Exec=/usr/share/code/code|Exec=/usr/share/code/code --no-sandbox|' /usr/share/applications/code.desktop && \
    sed -i 's|Exec=/usr/bin/google-chrome-stable|Exec=/usr/bin/google-chrome-stable --no-sandbox|' /usr/share/applications/google-chrome.desktop

# Add alias to /etc/bash.bashrc to include --no-sandbox
RUN cat <<EOF >> /etc/bash.bashrc
alias code='code --no-sandbox'
alias google-chrome='google-chrome --no-sandbox'
alias google-chrome-stable='google-chrome-stable --no-sandbox'
EOF

# Create a wrapper script for Google Chrome with --no-sandbox
RUN echo -e '#!/bin/bash\nexec /usr/bin/google-chrome-stable --no-sandbox "$@"' > /usr/local/bin/google-chrome-stable-no-sandbox && \
    chmod +x /usr/local/bin/google-chrome-stable-no-sandbox && \
    # Set Google Chrome as the default browser with --no-sandbox
    update-alternatives --install /usr/bin/x-www-browser x-www-browser /usr/local/bin/google-chrome-stable-no-sandbox 200 && \
    update-alternatives --set x-www-browser /usr/local/bin/google-chrome-stable-no-sandbox && \
    update-alternatives --install /usr/bin/gnome-www-browser gnome-www-browser /usr/local/bin/google-chrome-stable-no-sandbox 200 && \
    update-alternatives --set gnome-www-browser /usr/local/bin/google-chrome-stable-no-sandbox

# Configure container startup
ENTRYPOINT ["tini", "-g", "--"]
# Configure container startup
CMD ["start-notebook.sh"]

# ### Tensorflow
# # minor issues: 
# # https://stackoverflow.com/questions/44232898/memoryerror-in-tensorflow-and-successful-numa-node-read-from-sysfs-had-negativ
# # tested with:
# # https://docs.vmware.com/en/VMware-vSphere-Bitfusion/4.0/Example-Guide/GUID-8F6BF9A8-DC1A-4ACD-A2FF-C9CD0B50A9DC.html

ENV TF_CPP_MIN_LOG_LEVEL=2
ENV XLA_FLAGS=--xla_gpu_cuda_data_dir=${CONDA_DIR}
ENV LD_LIBRARY_PATH="${CONDA_DIR}/lib/:${CONDA_DIR}/lib/python3.12/site-packages/nvidia/cudnn/lib/"

# https://github.com/tensorflow/tensorboard/pull/3674
ENV TENSORBOARD_PROXY_URL="/proxy/%PORT%/"

# NbGrader
ENV NBGRADER_UID=2000 \
    NBGRADER_USER=nbgrader \
    COURSE_ID=cs1302_24a

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

COPY --chown=${NB_USER}:${NB_GID} nbgrader_config.py ${CONDA_DIR}/etc/jupyter/nbgrader_config.py

COPY --chown="${NB_UID}:${NB_GID}" initial-condarc "${CONDA_DIR}/.condarc"
COPY --chown="${NB_UID}:${NB_GID}" kernel.json "${CONDA_DIR}/share/jupyter/kernels/python3/kernel.json"

# Disable news and update
# See https://jupyterlab.readthedocs.io/en/stable/user/announcements.html
RUN jupyter labextension disable "@jupyterlab/apputils-extension:announcements"

USER ${NB_UID}

RUN \
    pip install --quiet --no-cache-dir \
    'git+https://github.com/dive4dec/dive_ai@3b9e78f5adaa7c633c8eaf5c0ae392b1627683d6#subdirectory=dive_ai' && \
    fix-permissions "${CONDA_DIR}"

RUN fix-permissions "/usr/lib/code-server/lib/vscode/extensions"

WORKDIR "${HOME}"

# ----------------------------------------------------------

FROM prod AS collab

USER ${NB_USER}

# Collaboration
RUN \
    # mamba install --quiet --yes \
    # 'jupyter-collaboration=2.1.*' \
    # && \
    pip install --pre --quiet --no-cache-dir \
    'jupyter-collaboration==3.0.0beta6' \
    'jupyterlab-collaborative-chat' \
    && \
    mamba clean --all -f -y && \
    fix-permissions "${CONDA_DIR}"

FROM prod AS default

USER ${NB_USER}