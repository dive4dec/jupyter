		SHELL=/bin/bash

# Docker registry
registry ?= localhost:32000

# Docker image information
jhub := jhub^4.0.0b
deephub := deephub^4.0.0a
deepnb := deepnb^0.1.4e
cs1302nb := cs1302nb^0.1.7d
cs5483nb := cs5483nb^0.1.6a
cs5483nb_collab := $(cs5483nb)^collab
cs1302nb_collab := $(cs1302nb)^collab
cs1302nb_core := $(cs1302nb)^^core
deepnb_collab := $(deepnb)^collab
vllm := vllm^0.1.1a

test.%: 
	$(MAKE) parse-image-info.$($*) resgistry=chungc IMAGE_TAG=latest

# Prepare a docker image
image.%:
	@ $(MAKE) docker-build.$($*) && \
	$(MAKE) docker-push.$($*)

# Publish a docker image
publish-image.%:
	@ $(MAKE) docker-multiarch.$($*) registry=chungc

publish-image-as-latest.%:
	@ $(MAKE) docker-multiarch.$($*) registry=chungc IMAGE_TAG=latest

docker-multiarch.%: parse-image-info.%
	$(docker-multiarch)

define docker-multiarch
@echo "Building multiarch docker image..." && \
cd $(IMAGE_NAME) && docker buildx build . \
--builder=container \
--platform linux/amd64,linux/arm64 \
$(if $(DOCKERFILE_SUFFIX),-f Dockerfile.$(DOCKERFILE_SUFFIX)) \
$(if $(BUILD_TARGET),--target $(BUILD_TARGET)) \
-t "$(registry)/$(IMAGE_NAME):$(IMAGE_TAG)" \
--push
endef


# Test a docker image
test-image.%:
	$(MAKE) docker-run.$($*)

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
$(eval _tokenized ?= $(subst ^, ^,$*))
$(eval IMAGE_NAME ?= $(word 1,$(_tokenized)))
$(eval IMAGE_VERSION ?= $(subst ^,,$(word 2,$(_tokenized))))
$(eval BUILD_TARGET ?= $(subst ^,,$(word 3,$(_tokenized))))
$(eval DOCKERFILE_SUFFIX ?= $(subst ^,,$(word 4,$(_tokenized))))
$(eval IMAGE_TAG ?= $(if $(IMAGE_VERSION),$(IMAGE_VERSION)$(if $(BUILD_TARGET),-$(BUILD_TARGET))$(if $(DOCKERFILE_SUFFIX),.$(DOCKERFILE_SUFFIX)),latest))
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
cd $(IMAGE_NAME) && docker buildx build . \
-t "$(IMAGE_NAME):$(IMAGE_TAG)" \
$(if $(DOCKERFILE_SUFFIX),-f Dockerfile.$(DOCKERFILE_SUFFIX)) \
$(if $(BUILD_TARGET),--target $(BUILD_TARGET))
endef

# Test run a docker image at a port
docker-run.%: parse-image-info.%; #@ $(info $(docker-run)) :
	$(docker-run)

define docker-run
@ docker run --gpus all -it -p 8888:8888/tcp \
	-v $(PWD):/home/jovyan/work \
	-v /models:/models \
	"$(IMAGE_NAME):$(IMAGE_TAG)" start-notebook.sh --IdentityProvider.token='' --Application.log_level=0
endef

# Push a docker image to a registry
docker-push.%: parse-image-info.%; #@ $(info $(docker-push)) :
	$(docker-push)

define docker-push
@echo "Pushing docker image..."
docker tag "$(IMAGE_NAME):$(IMAGE_TAG)" "$(registry)/$(IMAGE_NAME):$(IMAGE_TAG)" && \
docker push "$(registry)/$(IMAGE_NAME):$(IMAGE_TAG)"
endef
