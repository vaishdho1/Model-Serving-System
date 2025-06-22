#!/bin/bash
set -e

cd "$(dirname "$0")/../.."
# --- Configuration ---
export AWS_REGION="us-east-1"
export AWS_ACCOUNT_ID="768245436582" #AWS Account ID
export ECR_REPO_NAME="model-serving-controller"
export IMAGE_TAG="v1"
export DOCKERFILE_NAME="docker/Dockerfile.head"


# --- Script ---

# 1. Build the image locally
echo "Step 1: Building Docker image..."
docker build --platform linux/amd64 -t ${ECR_REPO_NAME}:${IMAGE_TAG} -f ${DOCKERFILE_NAME} .

# 2. Check authentication and login if necessary
echo "Step 2: Checking ECR authentication..."
ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

# Check if not logged in
if ! docker info 2>/dev/null | grep -q "${ECR_REGISTRY}"; then
    echo "Not logged in. Authenticating to ECR..."
    aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_REGISTRY}
else
    echo "Already logged in to ECR. Skipping authentication."
fi

# 3. Construct the full ECR image URI
FULL_IMAGE_NAME="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO_NAME}:${IMAGE_TAG}"

# 4. Tag the local image with the ECR URI
echo "Tagging image as ${FULL_IMAGE_NAME}..."
docker tag ${ECR_REPO_NAME}:${IMAGE_TAG} ${FULL_IMAGE_NAME}

# 5. Push the image to ECR
echo "Pushing image to ECR..."
docker push ${FULL_IMAGE_NAME}

echo "Push complete."