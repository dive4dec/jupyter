ARG ROOT_CONTAINER=ubuntu:24.04

FROM $ROOT_CONTAINER as foundation

# Fix the UID conflict with user ubuntu when jovyan needs to be created later. 
# See https://bugs.launchpad.net/cloud-images/+bug/2005129
RUN touch /var/mail/ubuntu && chown ubuntu /var/mail/ubuntu && userdel -r ubuntu

# Fix: https://github.com/hadolint/hadolint/wiki/DL4006
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Avoid prompt for user input for installation of dependencies
ENV DEBIAN_FRONTEND noninteractive

ARG NB_USER="jovyan"
ARG NB_UID="1000"
ARG NB_GID="100"

# Configure environment
ENV CONDA_DIR=/opt/conda \
    SHELL=/bin/bash \
    NB_USER="${NB_USER}" \
    NB_UID=${NB_UID} \
    NB_GID=${NB_GID} \
    LC_ALL=en_US.UTF-8 \
    LANG=en_US.UTF-8 \
    LANGUAGE=en_US.UTF-8 \
    TZ=Hongkong
ENV PATH="${CONDA_DIR}/bin:${PATH}" \
    HOME="/home/${NB_USER}"

    
USER root
FROM foundation as base

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
    locale-gen && \
    ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone


# A script to correct permissions after running certain commands
COPY fix-permissions /usr/local/bin/fix-permissions
RUN chmod a+rx /usr/local/bin/fix-permissions

# Enable prompt color in the skeleton .bashrc before creating the default NB_USER
# hadolint ignore=SC2016
RUN sed -i 's/^#force_color_prompt=yes/force_color_prompt=yes/' /etc/skel/.bashrc && \
   # Add call to conda init script see https://stackoverflow.com/a/58081608/4413446
   echo 'eval "$(command conda shell.bash hook 2> /dev/null)"' >> /etc/skel/.bashrc

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

# Pin python version here, or set it to "default"
ARG PYTHON_VERSION=3.12

# Download and install Micromamba, and initialize Conda prefix.
#   <https://github.com/mamba-org/mamba#micromamba>
# Install Python, Mamba and jupyter_core
COPY --chown="${NB_UID}:${NB_GID}" initial-condarc "${CONDA_DIR}/.condarc"
WORKDIR /tmp
RUN set -x && \
    arch=$(uname -m) && \
    if [ "${arch}" = "x86_64" ]; then \
        # Should be simpler, see <https://github.com/mamba-org/mamba/issues/1437>
        arch="64"; \
    fi &&  \
    wget --progress=dot:giga -O /tmp/micromamba.tar.bz2 \
        "https://micromamba.snakepit.net/api/micromamba/linux-${arch}/latest" && \
    tar -xvjf /tmp/micromamba.tar.bz2 --strip-components=1 bin/micromamba && \
    rm /tmp/micromamba.tar.bz2 && \
    PYTHON_SPECIFIER="python=${PYTHON_VERSION}" && \
    if [[ "${PYTHON_VERSION}" == "default" ]]; then PYTHON_SPECIFIER="python"; fi && \
    # Install the packages
    ./micromamba install \
        --root-prefix="${CONDA_DIR}" \
        --prefix="${CONDA_DIR}" \
        --yes \
        "${PYTHON_SPECIFIER}" \
        'mamba' \
        'jupyter_core' && \
    rm micromamba && \
    # Pin major.minor version of python
    mamba list python | grep '^python ' | tr -s ' ' | cut -d ' ' -f 1,2 >> "${CONDA_DIR}/conda-meta/pinned" && \
    # mamba clean --all -f -y && \
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
    'nodejs==20.12.*' \
    'notebook==7.2.*' \
    'jupyterlab==4.2.*' \
    'jupyterhub==5.0.*' \
    && \
    jupyter notebook --generate-config && \
    mamba clean --all -f -y && \
    npm cache clean --force && \
    jupyter lab clean && \
    rm -rf "/home/${NB_USER}/.cache/yarn" && \
    fix-permissions "${CONDA_DIR}" && \
    fix-permissions "/home/${NB_USER}"

USER root

ENV JUPYTER_PORT=8888
EXPOSE $JUPYTER_PORT

# fix https://github.com/jupyter/docker-stacks/issues/815
RUN cat /etc/skel/.bashrc >> /etc/bash.bashrc

### code-server ###
RUN apt-get update --yes && \
    apt-get install --yes --no-install-recommends \
    curl \
    && \
    wget -q https://code-server.dev/install.sh -O /tmp/install.sh && \
    sh /tmp/install.sh --version 4.90.0 && \
    # apt-get clean && rm -rf /var/lib/apt/lists/*
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
    'python-lsp-server=1.11.*' \
    'jupyter-resource-usage==1.0.*' \
    && \
    pip install --quiet --no-cache-dir \
    'jupyterlab-git==0.50.*' \    
    'jupyterlab_filesystem_access==0.6.*' \
    'jupyter-www-proxy' \
    && \
    mamba clean --all -f -y && \
    fix-permissions "${CONDA_DIR}"

USER root

# Programming languages backends
RUN \
    apt-get update --yes && \
    apt-get install --yes --no-install-recommends \
    # C, C++
    build-essential \
    unzip \
    gdb \
    fpc-source \
    # SQL
    sqlite3 \
    pdf2svg \
    && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# JAVA
RUN \
    apt-get update --yes && \
    apt-get install --yes --no-install-recommends \
    default-jdk default-jre

# MIT Scheme
COPY mit-scheme/ /tmp/mit-scheme/
RUN bash /tmp/mit-scheme/buildscript.sh

# For installing some jupyter kernels
RUN apt-get update --yes && \
    apt-get install --yes --no-install-recommends libzmq3-dev

USER ${NB_USER}

# # Programming languages supports
RUN npm install -g npm@^10.8.0 && \
    npm install -g \
    # Documentations with MyST
    mystmd \
    # Javascript and Typescript
    tslab && \
    tslab install --sys-prefix \
    && \
    mamba install --quiet --yes \
    # C, C++
    'xeus-cling=0.15.*' \
    # Java
    'openjdk=22.0.*' \
    # Documentations
    'jupyterlite=0.3.*' \
    && \
    pip install --quiet --no-cache-dir \
    'calysto-scheme==1.4.*' \
    'jupyterlab-myst==2.4.*' \
    # Documentations
    'itikz==0.1.*' \
    'nbdev==2.3.*' \
    'jupyterlab-quarto==0.3.*' \
    && \
    # scheme kernel
    python3 -m calysto_scheme install --sys-prefix && \
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
RUN wget -q "https://sourceforge.net/projects/turbovnc/files/3.1/turbovnc_3.1_amd64.deb/download" \
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

# AI
USER root

RUN curl -fsSL https://ollama.com/install.sh | sh

USER ${NB_USER}

# PyTorch & tensorflow
RUN mamba install --quiet --yes \
    'pytorch=2.3.*' \
    'torchvision=0.18.*' \
    'torchaudio=2.3.*' \
    'pytorch-cuda=12.1' \
    -c pytorch -c nvidia \
    && \
    pip install --quiet --no-cache-dir \
    'tensorflow==2.16.*' \
    'tensorflow-datasets==4.9.*' \
    && \
    mamba clean --all -f -y && \
    fix-permissions "${CONDA_DIR}"

# Other AI tools
RUN pip install --quiet --no-cache-dir \
    'jupyter_ai' \
    'openai' \
    'ollama' \
    && \
    fix-permissions "${CONDA_DIR}"

RUN pip install --quiet --no-cache-dir \
    'transformers' \
    'torchtune' \
    'accelerate' \
    'evaluate' \
    'scikit-learn' \
    && \
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
    sqlalchemy \
    statsmodels \
    xlrd \
    && \
    pip install --quiet --no-cache-dir \
    'nvitop' \
    'gpustat' \
    'jdc' \
    'jupyterlab-tensorboard-pro' && \
    mamba clean --all -f -y && \
    fix-permissions "${CONDA_DIR}"

# Other UI enhancements
RUN \
    mamba install --quiet --yes \
    'jupyter-archive=3.4.*' \
    && \
    pip install --quiet --no-cache-dir \
    'jupyterlab-unfold==0.3.*' \
    'jupyterlab-favorites==3.2.*' \
    'lckr_jupyterlab_variableinspector==3.2.*' \
    && \
    mamba clean --all -f -y && \    
    fix-permissions "${CONDA_DIR}"

# Themes
RUN pip install --quiet --no-cache-dir \
    'jupyterlab_theme_solarized_dark' \
    'jupyterlab-night' \
    'jupyterlab_theme_solarized_dark' \
    'theme-darcula' && \
    fix-permissions "${CONDA_DIR}"

# Slideshow
RUN pip install --quiet --no-cache-dir \
    # not compatible with jupyterlab-myst
    # 'jupyterlab_rise==0.42.*' \
    'jupyterlab-deck==0.2.*' && \
    fix-permissions "${CONDA_DIR}"

COPY dive_ai-0.0.1-py3-none-any.whl /tmp/dive_ai-0.0.1-py3-none-any.whl

# Local ai
RUN \
    pip install --quiet --no-cache-dir \
    'dive_ai-0.0.1-py3-none-any.whl' && \
    mamba clean --all -f -y && \
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
        ms-toolsai.jupyter \
        ms-toolsai.vscode-jupyter-powertoys \
        ms-python.black-formatter \
        streetsidesoftware.code-spell-checker \
        sugatoray.vscode-git-extension-pack \
        Kelvin.vscode-sshfs \
        hediet.vscode-drawio \
        ; do \
        code-server --extensions-dir /usr/lib/code-server/lib/vscode/extensions --install-extension "$ext"; \
    done

RUN for ext in \
    DanielSanMedium.dscodegpt@3.3.39 \
    GitHub.copilot-chat@0.16.1 \
    GitHub.copilot@1.200.0 \
    ; do \
    install-vscode-extension "$ext" --extensions-dir /usr/lib/code-server/lib/vscode/extensions; \
    done

# ----------------------------------------------------------

FROM foundation as prod

COPY --from=base /etc/ /etc/
COPY --from=base /usr/ /usr/
COPY --from=base /var/ /var/
COPY --from=base /home/ /home/
COPY --from=base /opt/ /opt/

USER root

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
ENV XLA_FLAGS=--xla_gpu_cuda_data_dir=${CONDA_DIR}/lib
ENV LD_LIBRARY_PATH="/opt/conda/lib/:${CONDA_DIR}/lib/python3.12/site-packages/nvidia/cudnn/lib/"

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

# Disable news and update
# See https://jupyterlab.readthedocs.io/en/stable/user/announcements.html
RUN jupyter labextension disable "@jupyterlab/apputils-extension:announcements"

WORKDIR "${HOME}"

# ----------------------------------------------------------

FROM prod as collab

USER ${NB_USER}

# Collaboration
RUN mamba install --quiet --yes \
    'jupyter-collaboration=2.1.*' \
    && \
    mamba clean --all -f -y && \
    fix-permissions "${CONDA_DIR}"

FROM prod as default

USER ${NB_USER}