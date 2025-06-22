#!/bin/bash
set -e # Exit immediately if a command exits with a non-zero status.

# --- Configuration: UPDATE THESE VARIABLES ---
export PROJECT_ID="data-backup-457517-f5"
export ZONE="us-east1-d" 
export VM_NAME="head-controller"
export MACHINE_TYPE="e2-medium" 
export NETWORK_TAGS="http-server,https-server" # Tags for firewall rules

# This is the full path to the image you pushed to Artifact Registry
# The ":v1" tag is an example; you can use ":latest" or a git commit hash
export IMAGE_PATH="us-east1-docker.pkg.dev/$PROJECT_ID/my-docker-repo/model-serving-controller:v1"

# --- End of Configuration ---

# --- IAM PERMISSION FIX ---
# This section ensures the VM's service account has permission to pull Docker images.
echo "Step 1: Ensuring VM has permission to pull images..."

# Get the project number, which is part of the default service account's name
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")

# Construct the full email of the default Compute Engine service account
SERVICE_ACCOUNT_EMAIL="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

# Grant the "Artifact Registry Reader" role to the service account.
# This command is idempotent - it's safe to run multiple times.
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
    --role="roles/artifactregistry.reader" \
    --condition=None # Required for gcloud versions > 460
echo "IAM permissions are set correctly."


echo "Step 2: Starting deployment for VM: $VM_NAME..."
echo "Using Image: $IMAGE_PATH"

# Check if the VM instance already exists
if gcloud compute instances describe "$VM_NAME" --zone="$ZONE" --project="$PROJECT_ID" &> /dev/null; then
    # --- UPDATE EXISTING VM ---
    echo "VM '$VM_NAME' already exists. Updating container to the new image..."
    gcloud compute instances update-container "$VM_NAME" \
        --zone="$ZONE" \
        --project="$PROJECT_ID" \
        --container-image="$IMAGE_PATH"
    echo "VM container updated successfully."
else
    # --- CREATE NEW VM ---
    echo "VM '$VM_NAME' not found. Creating a new instance..."
    # 'create-with-container' is the easiest way to launch a single container
    gcloud compute instances create-with-container "$VM_NAME" \
        --zone="$ZONE" \
        --project="$PROJECT_ID" \
        --machine-type="$MACHINE_TYPE" \
        --tags="$NETWORK_TAGS" \
        --image-project="cos-cloud" \
        --image-family="cos-stable" \
        --boot-disk-size=50GB \
        --container-image="$IMAGE_PATH" \
        --container-restart-policy="always" \
        --scopes=cloud-platform \
        --container-arg="--http_port=8000" \
        --container-arg="--node_port=50056" \
        --container-arg="--grpc_port=50053"

    echo "VM created and container is running."
fi

# Fetch and display the external IP address of the VM
EXTERNAL_IP=$(gcloud compute instances describe "$VM_NAME" \
    --zone="$ZONE" \
    --project="$PROJECT_ID" \
    --format='get(networkInterfaces[0].accessConfigs[0].natIP)')

echo "----------------------------------------------------"
echo "Head Controller IP Address: $EXTERNAL_IP"
echo "----------------------------------------------------"
