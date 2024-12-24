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

# Install all OS dependencies
RUN apt-get update --yes && \
    apt-get install --yes --no-install-recommends \
    git \
    nano-tiny \
    tzdata \
    unzip \
    vim-tiny \
    && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

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
ARG PYTHON_VERSION=3.12

# Pin micromamba version here, or leave it empty for the latest version
ARG MICROMAMBA_VERSION=2.0.5-0

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

# Set MAMBA_ROOT_PREFIX environment variable for the Docker build process and runtime
ENV MAMBA_ROOT_PREFIX=${CONDA_DIR}

# Enable prompt color in the skeleton .bashrc before creating the default NB_USER
# hadolint ignore=SC2016
RUN sed -i 's/^#force_color_prompt=yes/force_color_prompt=yes/' /etc/skel/.bashrc && \
    cat /etc/skel/.bashrc >> /etc/bash.bashrc

# Add call to micromamba init script
RUN cat <<'EOF' >> /etc/bash.bashrc
eval "$(mamba shell hook --shell bash)"
alias conda="mamba"
EOF

RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends \
        # requirement for pycurl
        libcurl4 \
        # requirement for using postgres database
        libpq5 \
        libpq-dev \
        libcurl4-openssl-dev \
        # requirement for using a local sqlite database
        sqlite3 \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

USER ${NB_UID}

RUN if [ "${PYTHON_VERSION:-}" = "" ]; then PYTHON_SPECIFIER="python"; else PYTHON_SPECIFIER="python=${PYTHON_VERSION}"; fi && \
        mamba install --yes \
        "${PYTHON_SPECIFIER}" \
        && \
        # Pin major.minor version of python
        mamba list python | sed 's/^[[:space:]]*//' | grep '^python ' | tr -s ' ' | cut -d ' ' -f 1,2 >> "${CONDA_DIR}/conda-meta/pinned" && \
        mamba clean --all -f -y && \
        fix-permissions "${CONDA_DIR}" && \
        fix-permissions "/home/${NB_USER}"

COPY --chown="${NB_UID}:${NB_GID}" requirements.txt /tmp/requirements.txt

RUN pip wheel \
    --wheel-dir=/tmp/wheels \
    # pycurl 7.45.3 has wheels, but they aren't portable
    # https://github.com/pycurl/pycurl/issues/834
    --no-binary pycurl \
    -r /tmp/requirements.txt \
    # Additional wheels for default-stage. Updates below should be repeated
    # in default-stage.
    #
    py-spy

RUN \
    pip install --no-cache-dir --quiet -r \
    /tmp/requirements.txt && \
    fix-permissions "${CONDA_DIR}" && \
    fix-permissions "/home/${NB_USER}"

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

# -----------------
# For LDAP & RADIUS
RUN apt-get update && \
    apt-get upgrade --yes && \
    apt-get install --yes --no-install-recommends \
    libnss-ldap \
    libpam-ldap \
    libpam-radius-auth \
    ldap-utils \
    sudo \
    && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

COPY etc/libnss-ldap.conf /etc/libnss-ldap.conf
COPY etc/libnss-ldap.conf /etc/ldap.conf
COPY etc/nsswitch.conf /etc/nsswitch.conf
COPY etc/pam_radius_auth.conf /etc/pam_radius_auth.conf
COPY etc/pam.d /etc/pam.d

WORKDIR /srv/jupyterhub
RUN chown ${NB_USER}:${NB_GID} /srv/jupyterhub
USER ${NB_USER}

EXPOSE 8081
ENTRYPOINT ["tini", "-g", "--"]
CMD ["jupyterhub", "--config", "/usr/local/etc/jupyterhub/jupyterhub_config.py"]

USER ${NB_USER}