# Running Guide (AWS)

This project currently provides an AWS‑oriented build and deploy flow.This is the guide I used prepare the flow.The current reqirement is having access to G/VT(GPU) instances with a quota of 16vCPUS.

## 1) Prerequisites
- Docker on your workstation (Linux/macOS recommended)
- AWS account with IAM permissions to create/manage EC2 resources
- AWS CLI installed and configured:
  ```bash
  aws configure  # sets AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY / default region
  ```
- Network access to the required ports (e.g., 8000 for HTTP proxy, 8001 for metrics)

## 2) Configuration
Review and adjust configuration as needed:
- Infrastructure and deployment settings under `infra/` and `deploy/aws/`
- Build/deploy scripts: `scripts/aws_scripts/build-aws`, `deploy/aws/deploy_prometheus`
- Model configuration: `model_configs.json` (deployment names → model IDs)

If your account requires specific VPC/Subnet/Security Group/Key Pair IDs, update the scripts or export the required environment variables before running.

## 3) Build and deploy
From the repository root:
```bash
cd scripts/aws_scripts
./build-aws-controller.sh
./build-aws-scheduler.sh
./build-aws-prometheus.sh
cd scripts/deploy/aws
./deploy-controller-aws.sh
./deploy-proetheus_vm_aws.sh
```
> These scripts will build the controller + proxy image and deploy the necessary services on AWS.

## 4) Verify
Once the deployment reports healthy:
```bash
# Replace <public-hostname-or-ip> with your endpoint
curl -N -X POST http://<public-hostname-or-ip>:8000/v1/chat/tinyllama \
  -H "Content-Type: text/plain" \
  --data "Hello"
```
---
When a local, non‑AWS bootstrap flow becomes available, it will be documented here.