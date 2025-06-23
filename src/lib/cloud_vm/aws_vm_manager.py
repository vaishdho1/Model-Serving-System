# aws_vm_manager.py
import logging
import time
from typing import Dict, Optional

import boto3
from botocore.exceptions import ClientError, WaiterError

from .vm_config_aws import get_vm_profile_for_model

logger = logging.getLogger("AWSVMManager")

class AWSVMManager:
    """Manages the lifecycle of AWS EC2 instances, finding resources dynamically."""

    def __init__(self, region_name: str):
        self.region_name = region_name
        self.ec2_client = boto3.client("ec2", region_name=self.region_name)
        self._vm_cache: Dict[str, Dict] = {}
    
    def _find_security_group_id_by_name(self, sg_name: str) -> Optional[str]:
        """Finds a security group's ID using its Name tag."""
        logger.info(f"Searching for Security Group with Name tag: {sg_name}...")
        try:
            response = self.ec2_client.describe_security_groups(
                Filters=[{'Name': 'tag:Name', 'Values': [sg_name]}]
            )
            groups = response.get('SecurityGroups')
            if not groups:
                logger.error(f"No Security Group found with Name tag '{sg_name}'.")
                return None
            if len(groups) > 1:
                logger.warning(f"Multiple Security Groups found with Name tag '{sg_name}'. Using the first one.")
            
            sg_id = groups[0]['GroupId']
            logger.info(f"Found Security Group '{sg_name}' with ID: {sg_id}")
            return sg_id
        except ClientError as e:
            logger.error(f"API Error searching for Security Group '{sg_name}': {e}")
            return None

    # NEW: Helper method to find the latest AMI by a name pattern
    def _find_latest_ami_id_by_name(self, name_pattern: str) -> Optional[str]:
        """Finds the most recent AMI ID that matches a name pattern."""
        logger.info(f"Searching for latest AMI with pattern: {name_pattern}...")
        try:
            
            response = self.ec2_client.describe_images(
                Owners=['amazon'],
                Filters=[{'Name': 'name', 'Values': [name_pattern]}]
            )
            if not response.get('Images'):
                logger.error(f"No AMI found matching pattern '{name_pattern}'.")
                return None
            
            # Sort images by creation date in descending order to find the latest
            latest_image = sorted(response['Images'], key=lambda x: x['CreationDate'], reverse=True)[0]
            ami_id = latest_image['ImageId']
            logger.info(f"Found latest AMI '{latest_image['Name']}' with ID: {ami_id}")
            return ami_id
        except ClientError as e:
            logger.error(f"API Error searching for AMI pattern '{name_pattern}': {e}")
            return None


    def _generate_user_data_script(self, scheduler_id: int, head_controller_address: str, head_controller_port: str, num_cpus: int, num_gpus: int) -> str:
        """Generates a user data script to run the scheduler container on an EC2 instance."""
        image = "768245436582.dkr.ecr.us-east-1.amazonaws.com/model-serving-scheduler:v1"
        container_name = f"model-serving-scheduler-{scheduler_id}"
        aws_region = self.region_name

        return f'''#!/bin/bash
set -e
# Log to a file and to the console
exec > /var/log/userdata.log 2>&1


echo "User data script started."
sudo yum update -y
sudo yum install -y docker
sudo systemctl start docker
sudo systemctl enable docker
echo "Docker installed"
# 1) Authenticate Docker to AWS Elastic Container Registry (ECR).
echo "Configuring Docker authentication for AWS ECR in region {aws_region}..."
aws ecr get-login-password --region {aws_region} | sudo docker login --username AWS --password-stdin {image.split('/')[0]}

# 2) Pull the latest version of the scheduler container.
echo "Pulling scheduler image: {image}"
sudo docker pull {image}

# 3) Clean up any old running instances of this container.
echo "Cleaning up any existing containers named {container_name}..."
sudo docker stop {container_name} >/dev/null 2>&1 || true
sudo docker rm {container_name} >/dev/null 2>&1 || true

# 4) Run the new container.
echo "Starting new container: {container_name}"
sudo docker run -d --gpus all --network host --name {container_name} \
  -e SCHEDULER_ID="{scheduler_id}" \
  -e HEAD_HOST="{head_controller_address}" \
  -e HEAD_PORT="{head_controller_port}" \
  -e NUM_CPUS="{num_cpus}" \
  -e NUM_GPUS="{num_gpus}" \
  {image} || echo "docker run failed"
 
echo "User data script finished successfully."
'''
    
    def create_vm(self, scheduler_id: int, name: str, model_id: str, head_controller_address: str, head_controller_port: str) -> Optional[str]:
        """Create a new EC2 instance, dynamically finding its AMI and Security Group."""
        profile = get_vm_profile_for_model(model_id)
        
        # These dynamic lookups remain the same
        security_group_id = self._find_security_group_id_by_name(profile.security_group_name)
        ami_id = self._find_latest_ami_id_by_name(profile.ami_name_pattern)

        if not security_group_id or not ami_id:
            logger.error(f"Failed to find resources for VM {name}. Aborting.")
            return None

        user_data = self._generate_user_data_script(
            scheduler_id, head_controller_address, head_controller_port, 
            profile.min_cpu_cores, profile.gpu_count
        )

        try:
            logger.info(f"Requesting creation of instance {name}...")
            
            # The run_instances call is where we add the KeyName parameter
            response = self.ec2_client.run_instances(
                ImageId=ami_id,
                InstanceType=profile.instance_type,
                KeyName=profile.key_pair_name,  # <-- ADD THIS LINE to specify the key pair
                MinCount=1,
                MaxCount=1,
                UserData=user_data,
                IamInstanceProfile={'Name': profile.iam_profile_name},
                SecurityGroupIds=[security_group_id],
                BlockDeviceMappings=[
                    {
                        'DeviceName': '/dev/xvda', # This is the standard root device name for most Linux AMIs
                        'Ebs': {
                            'VolumeSize': profile.volume_size_gb,
                            'DeleteOnTermination': True,    
                            'VolumeType': 'gp3'  # General Purpose SSD v3 (recommended)
                        },
                    },
                ],
                TagSpecifications=[
                    {'ResourceType': 'instance', 'Tags': [{'Key': 'Name', 'Value': name}] + profile.tags}
                ]
            )
            instance_id = response['Instances'][0]['InstanceId']
            logger.info(f"Instance {name} ({instance_id}) is being created. Waiting for it to run...")

            waiter = self.ec2_client.get_waiter('instance_running')
            waiter.wait(InstanceIds=[instance_id])

            logger.info(f"Instance {instance_id} is running. Fetching details.")
            desc = self.ec2_client.describe_instances(InstanceIds=[instance_id])
            instance_details = desc['Reservations'][0]['Instances'][0]
            self._vm_cache[name] = instance_details
            return instance_details.get('PublicIpAddress')

        except (ClientError, WaiterError) as e:
            logger.error(f"Failed to create or verify instance {name}: {e}")
            if 'InvalidKeyPair.NotFound' in str(e):
                logger.error(f"FATAL: The key pair '{profile.key_pair_name}' was not found in region {self.region_name}. Please create it or check the name.")
            if 'instance_id' in locals():
                self.delete_vm(name, instance_id=instance_id)
            return None

    
    def delete_vm(self, name: str, instance_id: Optional[str] = None) -> bool:
        """Terminate an EC2 instance by its Name tag or instance ID."""
        if not instance_id:
            instance = self._find_instance_by_name(name)
            if not instance:
                logger.warning(f"Could not find instance '{name}' to delete.")
                return True
            instance_id = instance['InstanceId']
        
        try:
            logger.info(f"Requesting termination of instance {name} ({instance_id}).")
            self.ec2_client.terminate_instances(InstanceIds=[instance_id])
            
            waiter = self.ec2_client.get_waiter('instance_terminated')
            waiter.wait(InstanceIds=[instance_id])

            if name in self._vm_cache: del self._vm_cache[name]
            logger.info(f"Successfully terminated instance {name} ({instance_id}).")
            return True
        except ClientError as e:
            logger.error(f"Failed to delete instance {instance_id}: {e}")
            return False

    def _find_instance_by_name(self, name: str) -> Optional[Dict]:
        # ... (implementation from previous response to find instance by tag) ...
        pass