#!/bin/bash

# Docker Image Push Script
# Usage: ./scripts/push.sh [TAG_SUFFIX]
# If TAG_SUFFIX is not provided, it defaults to the current date and time in YYYYMMDD_HHMM format.

IMAGE_NAME="qwen2api"
LOCAL_TAG="local"
DOCKER_USER="rinch345"
REPO_NAME="${DOCKER_USER}/rinch_qwen2api"

# Get current timestamp if not provided as argument
if [ -z "$1" ]; then
    TIMESTAMP=$(date +"%Y%m%d_%H%M")
else
    TIMESTAMP="$1"
fi

VERSION_TAG="${TIMESTAMP}"

echo "Tagging ${IMAGE_NAME}:${LOCAL_TAG} as ${REPO_NAME}:${VERSION_TAG}"
docker tag ${IMAGE_NAME}:${LOCAL_TAG} ${REPO_NAME}:${VERSION_TAG}

echo "Tagging ${IMAGE_NAME}:${LOCAL_TAG} as ${REPO_NAME}:latest"
docker tag ${IMAGE_NAME}:${LOCAL_TAG} ${REPO_NAME}:latest

echo "Pushing ${REPO_NAME}:${VERSION_TAG}"
docker push ${REPO_NAME}:${VERSION_TAG}

echo "Pushing ${REPO_NAME}:latest"
docker push ${REPO_NAME}:latest

echo "Done!"