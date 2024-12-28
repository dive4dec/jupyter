# ==============================
# Jupyter Docker Images for DIVE
# ==============================
# Note: To build multiarch images, you need to have Docker with Buildx and container build support.
# You may also need to install QEMU for emulating different architectures.
# See: https://docs.docker.com/build/building/multi-platform/


# Current information for different docker images
# ===============================================
cs1302nb := cs1302nb^0.1.11c
cs1302nb_collab := $(cs1302nb)^collab
cs1302nb_core := $(cs1302nb)^^core
jhub := jhub^4.0.0e
deephub := deephub^4.0.0a
deepnb := deepnb^0.1.4e
cs5483nb := cs5483nb^0.2.0f
cs5483nb_collab := $(cs5483nb)^collab
deepnb_collab := $(deepnb)^collab
#
# Syntax guide:
# --------------------------------
#   VARIABLE_NAME := IMAGE_NAME[^IMAGE_VERSION[^BUILD_TARGET[^DOCKEFILE_SUFFIX]]]
# translates to the docker image tag:
#   IMAGE_NAME:[IMAGE_VERSION[-DOCKERFILE_SUFFIX[-BUILD_TARGET]]]
# assigned to an image built [as the target BUILD_TARGET] from the dockerfile located at:
#   IMAGE_NAME/Dockerfile[.DOCKER_SUFFIX]
# The image information can be printed using the variable name or its value:
#   make image-info.VARIABLE_NAME
# 	make parse-image-info.IMAGE_NAME[^IMAGE_VERSION[^BUILD_TARGET[^DOCKEFILE_SUFFIX]]]
# 
# Example 1:
# --------------------------------
#  cs1302nb = cs1302nb^0.1.9
# corresponds to the information:
#   ==============================
#   Docker image
#   ------------------------------
#   Name: cs1302nb
#   Tag: 0.1.9
#   Version: 0.1.9
#   Dockerfile: cs1302nb/Dockerfile.
#   Build target: 
#   ==============================
# This information can be printed with:
#   make image-info.cs1302nb
#   make parse-image-info.cs1302nb^0.1.9
#
# Example 2:
# --------------------------------
#   cs1302nb_collab := $(cs1302nb)^collab
# corresponds to the information:
#   ==============================
#   Docker image
#   ------------------------------
#   Name: cs1302nb
#   Tag: 0.1.9-collab
#   Version: 0.1.9
#   Dockerfile: cs1302nb/Dockerfile.
#   Build target: collab
#   ==============================
#
# Example 3:
# --------------------------------
#   cs1302nb_core := $(cs1302nb)^^core
# corresponds to the information:
#   ==============================
#   Docker image
#   ------------------------------
#   Name: cs1302nb
#   Tag: 0.1.9.core
#   Version: 0.1.9
#   Dockerfile: cs1302nb/Dockerfile.core
#   Build target: 
#   ==============================

# Registries
# ==========
# Private docker registry for managing docker images
private_registry ?= localhost:32000
# Public docker registry for publishing docker images
public_registry ?= chungc
# Default docker registry for managing docker images
registry ?= 

# Commands
# ========
# Default shell for running commands
SHELL := /bin/bash

# Show image information
image-info.%: 
	@ $(MAKE) parse-image-info.$($*)

# Prepare a docker image by building and pushing it to the registry (if non-empty)
image.%:
	@ $(MAKE) docker-build.$($*) && \
	$(if $(strip $(registry)),$(MAKE) docker-push.$($*))

# Publish a docker image to the public registry
public-image.%:
	@ $(MAKE) docker-multiarch.$($*) registry=$(public_registry)

# Publish a docker image as latest to the public registry
public-image-as-latest.%:
	@ $(MAKE) docker-multiarch.$($*) registry=$(public_registry) IMAGE_TAG=latest

# Build a multiarch docker image for publishing to the public registry
docker-multiarch.%: parse-image-info.%
	$(docker-multiarch)

define docker-multiarch
@echo "Building multiarch docker image..." && \
cd $(IMAGE_NAME) && docker buildx build . \
--builder=container \
--platform linux/amd64,linux/arm64 \
$(if $(DOCKERFILE_SUFFIX),-f Dockerfile.$(DOCKERFILE_SUFFIX)) \
$(if $(BUILD_TARGET),--target $(BUILD_TARGET)) \
-t "$(FULL_IMAGE_NAME):$(IMAGE_TAG)" \
--push
endef

# Run the latest published docker image
run.%:
	@read -p "Do you want to pull the latest image? (yes/no): " pull_latest; \
	case "$$pull_latest" in \
		[yY][eE][sS]|[yY]) \
			$(MAKE) docker-pull.$($*) registry=$(public_registry) IMAGE_TAG=latest; \
			;; \
	esac && \
	$(MAKE) docker-run.$($*) registry=$(public_registry) IMAGE_TAG=latest

# Run a docker image that is built
run-image.%:
	$(MAKE) docker-run.$($*)

# Parse docker image information
parse-image-info.%:
	$(call parse-image-info,$*)
	$(info $(image-info))
	@:

define parse-image-info
$(eval _tokenized ?= $(subst ^, ^,$*))
$(eval IMAGE_NAME ?= $(word 1,$(_tokenized)))
$(eval IMAGE_VERSION ?= $(subst ^,,$(word 2,$(_tokenized))))
$(eval BUILD_TARGET ?= $(subst ^,,$(word 3,$(_tokenized))))
$(eval DOCKERFILE_SUFFIX ?= $(subst ^,,$(word 4,$(_tokenized))))
$(eval IMAGE_TAG ?= $(if $(IMAGE_VERSION),$(IMAGE_VERSION)$(if $(BUILD_TARGET),-$(BUILD_TARGET))$(if $(DOCKERFILE_SUFFIX),.$(DOCKERFILE_SUFFIX)),latest))
$(eval FULL_IMAGE_NAME ?= $(if $(strip $(registry)),$(registry)/$(IMAGE_NAME),$(IMAGE_NAME)))
endef

define image-info
==============================
Docker image
------------------------------	
Name: $(FULL_IMAGE_NAME)
Tag: $(IMAGE_TAG)
Version: $(IMAGE_VERSION)
Dockerfile: $(IMAGE_NAME)/Dockerfile.$(DOCKERFILE_SUFFIX)
Build target: $(BUILD_TARGET)
==============================
endef

# Build a docker image
docker-build.%: parse-image-info.%; #@ $(info $(docker-build)) :
	$(docker-build)

define docker-build
@echo "Building docker image..."
cd $(IMAGE_NAME) && docker buildx build . \
-t "$(IMAGE_NAME):$(IMAGE_TAG)" \
$(if $(DOCKERFILE_SUFFIX),-f Dockerfile.$(DOCKERFILE_SUFFIX)) \
$(if $(BUILD_TARGET),--target $(BUILD_TARGET))
endef

# Pull a docker image
docker-pull.%: parse-image-info.%; #@ $(info $(docker-run)) :
	$(docker-pull)

define docker-pull
@ docker pull \
	"$(FULL_IMAGE_NAME):$(IMAGE_TAG)"
endef

# Run a docker image
docker-run.%: parse-image-info.%; #@ $(info $(docker-run)) :
	$(docker-run)

define docker-run
@ docker run -it \
	-p 8888:8888/tcp \
	-p 8000:8000/tcp \
	-v $(PWD):/home/jovyan/work \
	"$(FULL_IMAGE_NAME):$(IMAGE_TAG)"
endef

# Push a docker image to the registry
docker-push.%: parse-image-info.%; #@ $(info $(docker-push)) :
	$(docker-push)

define docker-push
@echo "Pushing docker image..."
docker tag "$(IMAGE_NAME):$(IMAGE_TAG)" "$(FULL_IMAGE_NAME):$(IMAGE_TAG)" && \
docker push "$(FULL_IMAGE_NAME):$(IMAGE_TAG)"
endef
