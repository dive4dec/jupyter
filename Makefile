SHELL=/bin/bash

# Application name:
#   - Used to define part of the helm release name, e.g., in the make command helm-upgrade.%.
#   - Used to define part of the kubernetes namespace, e.g., in the make command helm-upgrade.%.
#   - Must be unique among all jupyterhub instances deployed in the cluster because 
#     resources of the helm deployment are identified by namespace and/or release name.
main=24a

# Directory containing the values yaml files for helm release
yaml_dir := deploy
# JupyterHub chart version
jupyterhub_chart_version := 4.0.0-0.dev.git.6635.hecbe9b5b
# Docker registry
registry = localhost:32000

# Docker image information
jhub := jhub^4.0.0a
cs1302nb := cs1302nb^0.1.4a
# cs1302nb_alpine := cs1302nb^0.1.3c^^alpine
cs5483nb := cs5483nb^0.1.6a
cs5483nb_collab := $(cs5483nb)^collab
cs1302nb_collab := $(cs1302nb)^collab

cs1302: image.jhub image.cs1302nb image.cs1302nb_collab hub.cs1302

cs1302t: image.jhub image.cs1302nb image.cs1302nb_collab hub.cs1302t

cs5483: image.jhub image.cs5483nb image.cs5483nb_collab hub.cs5483

cs5483t: image.jhub image.cs5483nb image.cs5483nb_collab hub.cs5483t

# Prepare a docker image
image.%:
	@ make docker-build.$($*) && \
	make docker-push.$($*)

# Test a docker image
test-image.%:
	make docker-run.$($*)

# Deploy a jupyterhub instance
# NOTE: The necesary hub and notebook images should be built and pushed to the registry beforehand.
hub.%:  helm-upgrade.%
	@echo "Deploying $*..."

# Parse docker image information
# The make command 
#   make parse-image-info.IMAGE_NAME[^IMAGE_VERSION[^BUILD_TARGET[^DOCKEFILE_SUFFIX]]]
# extract different values for IMAGE_NAME, IMAGE_VERSION, BUILD_TARGET, DOCKERFILE_SUFFIX
# and set IMAGE_TAG to [IMAGE_VERSION[-DOCKERFILE_SUFFIX[-BUILD_TARGET]]|latest]
# 
# These values will be used by docker-related make commands to build or run the image. 
#
# Example 1:
# ----------
#   make parse-image-info.cs1302nb^0.1^prod^alpine
# will give
#   ==============================
#   Docker image
#   ------------------------------
#   Name: cs1302nb
#   Tag: 0.1-prod.alpine
#   Version: 0.1
#   Dockerfile suffix: alpine
#   Build target: prod
#   ==============================
#
# Example 2:
# ----------
#   make parse-image-info.cs1302nb^^prod^alpine
# will give
#   ==============================
#   Docker image
#   ------------------------------
#   Name: cs1302nb
#   Tag: latest
#   Version: 
#   Dockerfile suffix: alpine
#   Build target: prod
#   ==============================
parse-image-info.%:
	$(call parse-image-info,$*)
	$(info $(image-info))
	@:

define parse-image-info
$(eval _tokenized := $(subst ^, ^,$*))
$(eval IMAGE_NAME := $(word 1,$(_tokenized)))
$(eval IMAGE_VERSION := $(subst ^,,$(word 2,$(_tokenized))))
$(eval BUILD_TARGET := $(subst ^,,$(word 3,$(_tokenized))))
$(eval DOCKERFILE_SUFFIX := $(subst ^,,$(word 4,$(_tokenized))))
$(eval IMAGE_TAG := $(if $(IMAGE_VERSION),$(IMAGE_VERSION)$(if $(BUILD_TARGET),-$(BUILD_TARGET))$(if $(DOCKERFILE_SUFFIX),.$(DOCKERFILE_SUFFIX)),latest))
endef

define image-info
==============================
Docker image
------------------------------	
Name: $(IMAGE_NAME)
Tag: $(IMAGE_TAG)
Version: $(IMAGE_VERSION)
Dockerfile suffix: $(DOCKERFILE_SUFFIX)
Build target: $(BUILD_TARGET)
==============================
endef

# Build a docker image
docker-build.%: parse-image-info.%; #@ $(info $(docker-build)) :
	$(docker-build)

define docker-build
@echo "Building docker image..."
cd $(IMAGE_NAME) && docker build . \
-t "$(IMAGE_NAME):$(IMAGE_TAG)" \
$(if $(DOCKERFILE_SUFFIX),-f Dockerfile.$(DOCKERFILE_SUFFIX)) \
$(if $(BUILD_TARGET),--target $(BUILD_TARGET))
endef

# Test run a docker image at a port
docker-run.%: parse-image-info.%; #@ $(info $(docker-run)) :
	$(docker-run)

define docker-run
@docker run -it -p 8888:8888/tcp \
	-v $(PWD):/home/jovyan/work \
	"$(IMAGE_NAME):$(IMAGE_TAG)" start-notebook.sh --NotebookApp.token='' --Application.log_level=0
endef


# Push a docker image to a registry
docker-push.%: parse-image-info.%; #@ $(info $(docker-push)) :
	$(docker-push)

define docker-push
@echo "Pushing docker image..."
docker tag "$(IMAGE_NAME):$(IMAGE_TAG)" "$(registry)/$(IMAGE_NAME):$(IMAGE_TAG)" && \
docker push "$(registry)/$(IMAGE_NAME):$(IMAGE_TAG)"
endef


# Helm upgrade a jupyterhub instance
helm-upgrade.%:
	$(helm-upgrade)

test-helm-upgrade.%:
	$(helm-upgrade) --dry-run --debug 

define helm-upgrade
@echo "Upgrading/installing jupyterhub with $*.yaml in the Kubernetes cluster..."
cd $(yaml_dir) && \
helm upgrade --cleanup-on-fail --create-namespace -i -n jh-$(main)-$* $(main)-$* jupyterhub/jupyterhub \
	--version=$(jupyterhub_chart_version) -f $*.yaml --atomic
endef

# Helm list a jupyterhub instance
helm-list.%:
	@helm list -n jh-$(main)-$* && kubectl get all -n jh-$(main)-$*

# Helm rollback a jupyterhub instance
helm-rollback.%:
	@echo "Rolling back release in the Kubernetes cluster..."
	helm rollback -n jh-$(main)-$* $(main)-$* --wait

# Helm history of a jupyterhub instance
helm-history.%:
	@echo "Rolling back release in the Kubernetes cluster..."
	helm history -n jh-$(main)-$* $(main)-$*

# Helm uninstall a jupyterhub instance
helm-uninstall.%:
	@echo "Uninstalling release from the Kubernetes cluster..."
	helm uninstall -n jh-$(main)-$* $(main)-$* --wait

# Add/update helm repo
helm-repo:
	helm repo add jupyterhub https://jupyterhub.github.io/helm-chart/ --force-update


.PHONY: parse-image-info.% docker-build.% docker-push.% image.% test-image.% hub.% helm-upgrade.% test-helm-upgrade.% helm-list.% helm-uninstall.% helm-repo envsubst.%