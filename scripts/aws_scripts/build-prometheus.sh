#!/bin/bash
set -e
cd "$(dirname "$0")/../.."
# --- Configuration ---
export AWS_REGION="us-east-1"
export AWS_ACCOUNT_ID="768245436582"
export ECR_REPO_NAME="monitoring-prometheus" # A new repo for your custom image
export IMAGE_TAG="v1"
export DOCKERFILE_NAME="docker/Dockerfile.prometheus"

# Ensure the prometheus.yml file exists in the infra directory before building
if [ ! -f infra/prometheus.yml ]; then
    echo "Error: infra/prometheus.yml not found."
    exit 1
fi

# --- Script ---
echo "--- Building and Pushing Custom Prometheus Image ---"

# 1. Check for ECR repository and create if it doesn't exist
echo "Step 1: Checking for ECR repository '${ECR_REPO_NAME}'..."
if ! aws ecr describe-repositories --repository-names "${ECR_REPO_NAME}" --region "${AWS_REGION}" > /dev/null 2>&1; then
  echo "Repository does not exist. Creating repository '${ECR_REPO_NAME}'..."
  aws ecr create-repository \
      --repository-name "${ECR_REPO_NAME}" \
      --region "${AWS_REGION}" \
      --image-scanning-configuration scanOnPush=true \
      --image-tag-mutability MUTABLE
else
  echo "Repository '${ECR_REPO_NAME}' already exists."
fi

# 2. Build the image locally
echo "Step 2: Building Docker image..."
docker build --platform linux/amd64 -t ${ECR_REPO_NAME}:${IMAGE_TAG} -f ${DOCKERFILE_NAME} .

# 3. Authenticate to ECR
echo "Step 3: Checking ECR authentication..."
ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
if ! docker info 2>/dev/null | grep -q "${ECR_REGISTRY}"; then
    echo "Not logged in. Authenticating to ECR..."
    aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_REGISTRY}
else
    echo "Already logged in to ECR."
fi

# 4. Tag the image for ECR
FULL_IMAGE_NAME="${ECR_REGISTRY}/${ECR_REPO_NAME}:${IMAGE_TAG}"
echo "Step 4: Tagging image as ${FULL_IMAGE_NAME}..."
docker tag ${ECR_REPO_NAME}:${IMAGE_TAG} ${FULL_IMAGE_NAME}

# 5. Push the image to ECR
echo "Step 5: Pushing image to ECR..."
docker push ${FULL_IMAGE_NAME}

echo "Custom Prometheus image pushed successfully."