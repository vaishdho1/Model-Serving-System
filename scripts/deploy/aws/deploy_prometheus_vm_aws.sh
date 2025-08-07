#!/bin/bash
set -e

# --- Configuration ---
# Updated to use Amazon Linux 2023 (AL2023) with Python 3.9 pre-installed
export AWS_REGION="us-east-1"
export INSTANCE_NAME="monitoring-server"
export INSTANCE_TYPE="t3.medium"
export KEY_NAME="my-gpu-vm"
export IAM_ROLE_NAME="EC2ModelServingRole"
export DISK_SIZE_GB=40
export SECURITY_GROUP_NAME="monitoring-sg"
export AWS_ACCOUNT_ID="768245436582"
DOCKER_COMPOSE_VERSION="1.29.2"

# --- Security Group Lookup ---
echo "Step 1: Finding Security Group ID for '$SECURITY_GROUP_NAME'..."
SECURITY_GROUP_ID=$(aws ec2 describe-security-groups \
  --filters "Name=tag:Name,Values=$SECURITY_GROUP_NAME" \
  --query 'SecurityGroups[0].GroupId' \
  --output text \
  --region "$AWS_REGION")

if [[ -z "$SECURITY_GROUP_ID" || "$SECURITY_GROUP_ID" == "None" ]]; then
  echo "ERROR: Security group '$SECURITY_GROUP_NAME' not found in region '$AWS_REGION'"
  exit 1
fi

# --- Prepare Docker Compose Config ---
DOCKER_COMPOSE_CONFIG=$(base64 < infra/docker-compose.yaml)

# --- User Data (cloud-init) ---
USER_DATA=$(cat <<EOF
#!/bin/bash
echo "--- Starting Monitoring VM User Data ---"

# Update system first
dnf update -y

# Install Docker first
dnf install -y docker

# Start Docker service
systemctl start docker
usermod -a -G docker ec2-user
systemctl enable docker

# Install pip3 (Python 3.9 is pre-installed on AL2023)
dnf install -y python3-pip

# Install Docker Compose - try multiple methods for AL2023 compatibility
echo "Installing Docker Compose..."

# Method 1: Try pip3 install with user flag to avoid system package conflicts
# Install compatible versions to avoid SSL/TLS API conflicts
pip3 install --user 'docker-compose==1.29.2' 'docker>=5.0.0,<6.0.0' && {
    # Since we're running as root, docker-compose is installed to /root/.local/bin
    # Create symlink to make it accessible system-wide
    if [ -f /root/.local/bin/docker-compose ]; then
        ln -sf /root/.local/bin/docker-compose /usr/local/bin/docker-compose
        echo "Docker Compose installed via pip to /root/.local/bin and symlinked to /usr/local/bin"
    else
        echo "Docker Compose not found in expected location"
        exit 1
    fi
} || {
    echo "User pip install failed, trying direct binary download..."
    # Method 2: Download specific version binary directly (not using 'latest' redirect)
    curl -L "https://github.com/docker/compose/releases/download/1.29.2/docker-compose-Linux-x86_64" -o /usr/local/bin/docker-compose || {
        echo "Direct download failed, trying wget..."
        # Method 3: Try with wget if curl fails
        wget -O /usr/local/bin/docker-compose "https://github.com/docker/compose/releases/download/1.29.2/docker-compose-Linux-x86_64"
    }
chmod +x /usr/local/bin/docker-compose
}

# Verify Docker Compose installation
docker-compose --version || { echo "Docker Compose installation failed"; exit 1; }

# Login to ECR to pull your custom Prometheus image
aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com

# Create the docker-compose.yml file on the instance
mkdir -p /opt/monitoring
cd /opt/monitoring
echo "${DOCKER_COMPOSE_CONFIG}" | base64 -d > docker-compose.yml

# Start the monitoring stack using Docker Compose
echo "Starting Prometheus and Grafana..."
docker-compose up -d
echo "--- Monitoring Stack Deployed ---"
EOF
)

# --- Launch EC2 Instance ---
echo "Step 2: Launching Monitoring EC2 instance..."
INSTANCE_ID=$(aws ec2 run-instances \
  --region "$AWS_REGION" \
  --image-id resolve:ssm:/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64 \
  --instance-type "$INSTANCE_TYPE" \
  --key-name "$KEY_NAME" \
  --security-group-ids "$SECURITY_GROUP_ID" \
  --iam-instance-profile Name="$IAM_ROLE_NAME" \
  --block-device-mappings "[{\"DeviceName\":\"/dev/xvda\",\"Ebs\":{\"VolumeSize\":$DISK_SIZE_GB}}]" \
  --user-data "$USER_DATA" \
  --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$INSTANCE_NAME}]" \
  --output text --query 'Instances[0].InstanceId')

echo "Waiting for instance to be running..."
aws ec2 wait instance-running --region "$AWS_REGION" --instance-ids "$INSTANCE_ID"

PUBLIC_IP=$(aws ec2 describe-instances --instance-ids "$INSTANCE_ID" --region "$AWS_REGION" --query "Reservations[0].Instances[0].PublicIpAddress" --output text)

echo "----------------------------------------------------"
echo " Monitoring Server Launched"
echo "Grafana UI:     http://$PUBLIC_IP:3000"
echo "Prometheus UI:  http://$PUBLIC_IP:9090"
echo "----------------------------------------------------"