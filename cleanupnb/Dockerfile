ARG ROOT_CONTAINER=ubuntu:26.04

FROM $ROOT_CONTAINER AS foundation

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

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Fix the UID conflict with user ubuntu
RUN touch /var/mail/ubuntu && chown ubuntu /var/mail/ubuntu && userdel -r ubuntu && \
    useradd -l -m -s /bin/bash -N -u "${NB_UID}" "${NB_USER}"

USER root
FROM foundation AS base

RUN apt-get update --yes && \
    apt-get install --yes --no-install-recommends \
    bzip2 ca-certificates locales sudo tini wget less curl && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

RUN echo "en_US.UTF-8 UTF-8" > /etc/locale.gen && \
    echo "C.UTF-8 UTF-8" >> /etc/locale.gen && \
    locale-gen && \
    ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

COPY fix-permissions /usr/local/bin/fix-permissions
RUN chmod a+rx /usr/local/bin/fix-permissions

RUN echo "auth requisite pam_deny.so" >> /etc/pam.d/su && \
    sed -i.bak -e 's/^%admin/#%admin/' /etc/sudoers && \
    sed -i.bak -e 's/^%sudo/#%sudo/' /etc/sudoers && \
    mkdir -p "${CONDA_DIR}" && \
    chown "${NB_USER}:${NB_GID}" "${CONDA_DIR}" && \
    chmod g+w /etc/passwd && \
    fix-permissions "${HOME}" && \
    fix-permissions "${CONDA_DIR}"

USER ${NB_UID}

ARG PYTHON_VERSION=3.12
ARG MICROMAMBA_VERSION=2.3.0-1

COPY --chown="${NB_UID}:${NB_GID}" initial-condarc "${CONDA_DIR}/.condarc"
WORKDIR /tmp
RUN set -x && \
    case "$(uname)" in Linux) PLATFORM="linux" ;; *) echo "unsupported" >&2 && exit 1 ;; esac && \
    ARCH="$(uname -m)" && case "$ARCH" in aarch64|arm64) ;; *) ARCH="64" ;; esac && \
    RELEASE_URL="https://github.com/mamba-org/micromamba-releases/releases/download/${MICROMAMBA_VERSION}/micromamba-${PLATFORM}-${ARCH}" && \
    BIN_FOLDER="${CONDA_DIR}/bin" && \
    mkdir -p "${BIN_FOLDER}" && \
    curl "${RELEASE_URL}" -o "${BIN_FOLDER}/micromamba" -fsSL --compressed && \
    chmod +x "${BIN_FOLDER}/micromamba" && \
    ln -s ${BIN_FOLDER}/micromamba ${BIN_FOLDER}/mamba && \
    ln -s ${BIN_FOLDER}/micromamba ${BIN_FOLDER}/conda

ENV MAMBA_ROOT_PREFIX=${CONDA_DIR}

USER root
RUN cat <<'EOF' >> /etc/bash.bashrc
eval "$(mamba shell hook --shell bash)"
alias conda="mamba"
EOF

USER ${NB_UID}

RUN if [ "${PYTHON_VERSION:-}" = "" ]; then PYTHON_SPECIFIER="python"; else PYTHON_SPECIFIER="python=${PYTHON_VERSION}"; fi && \
    mamba install --yes "${PYTHON_SPECIFIER}" 'uv' && \
    mkdir -p "${CONDA_DIR}/conda-meta" && \
    mamba list python | sed 's/^[[:space:]]*//' | grep '^python ' | tr -s ' ' | cut -d ' ' -f 1,2 >> "${CONDA_DIR}/conda-meta/pinned" && \
    mamba clean --all -f -y && \
    fix-permissions "${CONDA_DIR}" && \
    fix-permissions "/home/${NB_USER}"

# Install jupyter-server + jupyterhub (NO jupyterlab, NO kernels — minimal image)
# jupyterhub is required so the notebook server can respond to the hub's
# version check — without it, the hub detects a "redirect loop".
RUN mamba install --yes --quiet \
    'jupyter_server==2.20.*' \
    'notebook==7.6.*' \
    'jupyterhub==5.5.*' \
    && \
    mamba clean --all -f -y && \
    fix-permissions "${CONDA_DIR}"

# Install jupyter-storage-usage from pre-built wheel
COPY jupyter_storage_usage-0.1.0-py3-none-any.whl /tmp/
RUN pip install --no-cache-dir /tmp/jupyter_storage_usage-0.1.0-py3-none-any.whl && \
    fix-permissions "${CONDA_DIR}" && \
    fix-permissions "/home/${NB_USER}"

# Enable the jupyterhub server extension (required so the hub can verify
# the notebook server version and avoid redirect loops).
RUN jupyter server extension enable --sys-prefix jupyterhub && \
    jupyter server extension enable --sys-prefix jupyter_storage_usage && \
    fix-permissions "${CONDA_DIR}"

# Cleanup mode is set by JupyterHub via extraEnv at spawn time.
# The entrypoint runs jupyter-server which auto-loads our extension.
ENV JUPYTER_PORT=8888
EXPOSE $JUPYTER_PORT

ENTRYPOINT ["tini", "-g", "--"]
CMD ["python", "-m", "jupyter_server", "--ServerApp.ip=0.0.0.0"]

USER ${NB_UID}
WORKDIR "${HOME}"
