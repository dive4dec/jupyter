# CS5495 singleuser image — thin course layer on the standard DIVE notebook base.
#
# The base (divenb) already provides: JupyterLab + code-server/VS Code,
# torch 2.11 (cu130 wheels), transformers, langchain, the full science/data-
# science stack, language kernels, nbgrader, Hermes, etc.
#
# This layer adds only what CS5495 (deep learning / XAI) needs on top:
#   - torch-lucent          : CNN activation/gradient visualisations
#                             (2022-era; pins kornia<=0.4.1 — the one compat risk,
#                             gated by the import check below)
#   - inseq                 : LLM interpretability (attribution, probing, inspection)
#                             (pulls its own nvidia-*-cu11 runtimes on Linux —
#                             coexists with torch's cu130, ~2-3 GB)
#   - xgboost, shap, lime, captum, eli5   : classic XAI set (was in cs5495nb 0.1.0)
#   - langchain-community   : was in cs5495nb 0.1.0, not in current divenb
#   - isort, gh             : were in cs5495nb 0.1.0, not in current divenb
# transformers is already in the base (5.14.x) — deliberately NOT reinstalled.
# torch-tensorrt is deliberately omitted (multi-GB TensorRT 11 runtime; the
# torch-2.11-matched release is torch-tensorrt==2.11.0 — re-add only if the
# course needs TRT engine export).
ARG BASE_CONTAINER=registry.dive4dec.svc.cluster.local/divenb:0.2.40

FROM $BASE_CONTAINER AS prod

RUN uv pip install --system --no-cache \
    'torch-lucent' \
    'inseq' \
    'xgboost' \
    'shap' \
    'lime' \
    'captum' \
    'eli5' \
    'langchain-community' \
    'isort' \
    'gh' \
    && mamba clean --all -f -y \
    && fix-permissions /opt/conda

# Build gate: fail if any course package fails to import on the base stack
# (Python 3.14 / torch 2.11). torch-lucent is the highest risk (2022 pin).
RUN python -c "import torch_lucent, inseq, xgboost, shap, lime, eli5, captum, langchain_community, isort" \
    && python -c "import torch; print('torch', torch.__version__)"

FROM prod AS default

USER ${NB_USER}

FROM prod AS collab

USER ${NB_UID}
