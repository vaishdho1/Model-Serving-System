#!/bin/bash
set -e

# --- Configuration ---
export AWS_REGION="us-east-1"
export INSTANCE_TYPE="t3.xlarge"
export KEY_NAME="my-gpu-vm"
export SECURITY_GROUP_NAME="head-controller-sg" 
export INSTANCE_NAME="head-controller"
export IMAGE_URI="768245436582.dkr.ecr.us-east-1.amazonaws.com/model-serving-controller:v1"
export IAM_ROLE_NAME="EC2ModelServingRole"

# --- Find Security Group ID by Name ---
echo "Step 1: Finding Security Group ID for '$SECURITY_GROUP_NAME'..."
SECURITY_GROUP_ID=$(aws ec2 describe-security-groups \
  --filters "Name=tag:Name,Values=$SECURITY_GROUP_NAME" \
  --query 'SecurityGroups[0].GroupId' \
  --output text \
  --region "$AWS_REGION")

if [ -z "$SECURITY_GROUP_ID" ]; then
    echo "Error: Could not find Security Group with Name tag '$SECURITY_GROUP_NAME'."
    exit 1
fi
echo "Found Security Group ID: $SECURITY_GROUP_ID"

# --- User Data Script to Run Container ---
USER_DATA=$(base64 <<EOF
#!/bin/bash
yum update -y
yum install -y docker
systemctl start docker
systemctl enable docker
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin ${IMAGE_URI%%/*}
docker pull $IMAGE_URI
docker run -d -p 8000:8000 -p 50056:50056 -p 50053:50053 $IMAGE_URI --http_port=8000 --node_port=50056 --grpc_port=50053
EOF
) 

# --- Launch EC2 Instance ---
echo "Step 2: Launching EC2 instance..."

INSTANCE_ID=$(aws ec2 run-instances \
  --region $AWS_REGION \
  --image-id ami-09e6f87a47903347c \
  --instance-type $INSTANCE_TYPE \
  --key-name $KEY_NAME \
  --security-group-ids $SECURITY_GROUP_ID \
  --iam-instance-profile Name=$IAM_ROLE_NAME \
  --block-device-mappings 'DeviceName=/dev/xvda,Ebs={VolumeSize=50,VolumeType=gp3}' \
  --user-data "$USER_DATA" \
  --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$INSTANCE_NAME}]" \
  --output text --query 'Instances[0].InstanceId')

echo "Waiting for instance to be running..."
aws ec2 wait instance-running --region $AWS_REGION --instance-ids $INSTANCE_ID

# --- Get Public IP ---
PUBLIC_IP=$(aws ec2 describe-instances \
  --instance-ids $INSTANCE_ID \
  --region $AWS_REGION \
  --query "Reservations[0].Instances[0].PublicIpAddress" \
  --output text)

echo "----------------------------------------------------"
echo "EC2 Instance Launched with Docker Container Running"
echo "Head Controller IP Address: $PUBLIC_IP"
echo "----------------------------------------------------"