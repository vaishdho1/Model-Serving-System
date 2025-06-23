import logging
from typing import Dict, Optional
import time

# Import the sync client and necessary types from the library
from google.cloud import compute_v1
from google.cloud.compute_v1.services.instances import client as instances_client
from google.cloud.compute_v1.types import Instance
from google.api_core import exceptions
from src.lib.logging_config import setup_logger
# Assuming vm_config is in the same directory/package
from .vm_config import VMProfile, get_vm_profile_for_model
vm_manager_logger = setup_logger("VMManager", "logs/vm_manager.log")
logger = vm_manager_logger

class VMManager:
    """Manages the lifecycle of Google Cloud VMs in a synchronous manner."""

    def __init__(self, project_id: str, initial_zone: str):
        self.project_id = project_id
        self.initial_zone = initial_zone
        # Use the InstancesClient for synchronous operations
        self.compute_client: instances_client.InstancesClient = compute_v1.InstancesClient()
        self._vm_cache: Dict[str, Instance] = {}
    
    def _generate_startup_script(self, scheduler_id: int, head_controller_address: str, head_controller_port: str, num_cpus: int, num_gpus: int) -> str:
        """
        Generates a post-startup script for a Deep Learning VM.
        This script assumes Docker and NVIDIA drivers are pre-installed.
        It uses 'sudo' for commands requiring root privileges.
        """
        image = "us-east1-docker.pkg.dev/data-backup-457517-f5/my-docker-repo/model-serving-scheduler:v1"
        container_name = f"model-serving-scheduler-{scheduler_id}"
        return f'''#!/bin/bash
set -e

echo "Post-startup script started. Running as user: $(whoami)"

# Docker and NVIDIA drivers are pre-installed on Deep Learning VM images,
# so we can skip those installation steps.

# 1) Authenticate Docker to Google Artifact Registry.
# Use sudo because this configures Docker for all users on the system.
echo "Configuring Docker authentication for Artifact Registry..."
sudo gcloud auth configure-docker us-east1-docker.pkg.dev -q

# 2) Pull the latest version of the scheduler container.
# The 'jupyter' user is already in the 'docker' group on DLVM images,
# but using sudo is a safer, more explicit practice.
echo "Pulling scheduler image: {image}"
sudo docker pull {image}

# 3) Stop and remove any old running instances of this container.
echo "Cleaning up any existing containers..."
sudo docker stop {container_name} || true
sudo docker rm {container_name} || true

# 4) Run the new container.
echo "Starting new container: {container_name}"
sudo docker run -d \\
  --gpus all \\
  --network host \\
  --name {container_name} \\
  -e SCHEDULER_ID="{scheduler_id}" \\
  -e HEAD_HOST="{head_controller_address}" \\
  -e HEAD_PORT="{head_controller_port}" \\
  -e NUM_CPUS="{num_cpus}" \\
  -e NUM_GPUS="{num_gpus}" \\
  -e LOG_LEVEL="INFO" \\
  -v /var/log/model-serving:/var/log/model-serving \\
  {image}
 
echo "Post-startup script finished successfully."
'''

    def create_vm(self, scheduler_id: int, name: str, model_id: str, head_controller_address: str, head_controller_port: str) -> Optional[str]:
        """Create a new VM using a robust fire-and-poll strategy, trying multiple zones."""
        zones_to_try = ["us-east1-d", "us-east1-c", "us-east1-b"]
        
        for zone in zones_to_try:
            try:
                logger.info(f"Attempting to create VM {name} in zone {zone}...")
                profile = get_vm_profile_for_model(model_id)
                
                instance = compute_v1.Instance()
                instance.name = name
                instance.machine_type = f"zones/{zone}/machineTypes/{profile.machine_type.value}"
                
                disk = compute_v1.AttachedDisk(
                    boot=True,
                    auto_delete=True,
                    device_name=name,
                    initialize_params=compute_v1.AttachedDiskInitializeParams(
                        source_image=f"projects/{profile.image_project}/global/images/family/{profile.image_family}",
                        disk_size_gb=profile.boot_disk_size_gb
                    )
                )
                instance.disks = [disk]

                instance.network_interfaces = [compute_v1.NetworkInterface(
                    network="global/networks/default",
                    access_configs=[compute_v1.AccessConfig(name="external-nat", type_="ONE_TO_ONE_NAT")]
                )]

                if profile.gpu_type:
                    instance.guest_accelerators = [compute_v1.AcceleratorConfig(
                        accelerator_type=f"projects/{self.project_id}/zones/{zone}/acceleratorTypes/{profile.gpu_type.value}",
                        accelerator_count=profile.gpu_count
                    )]

                instance.scheduling = compute_v1.Scheduling(on_host_maintenance=profile.maintenance_policy)

                if profile.tags:
                    instance.tags = compute_v1.Tags(items=profile.tags)
                
                startup_script = self._generate_startup_script(scheduler_id, head_controller_address, head_controller_port, profile.min_cpu_cores, profile.gpu_count)
                
                instance.metadata = compute_v1.Metadata(items=[
                    compute_v1.Items(key="install-nvidia-driver", value="True"),
                    compute_v1.Items(key="startup-script", value=startup_script)
                    
                ])

                # Add the default Compute Engine service account for pulling images from Google Artifact Registry
                instance.service_accounts = [
                    compute_v1.ServiceAccount(
                        email="default",  # Use the default Compute Engine service account
                        scopes=["https://www.googleapis.com/auth/cloud-platform"]
                    )
                ]

                # Create the VM
                operation = self.compute_client.insert(project=self.project_id, zone=zone, instance_resource=instance)
                operation.result()  # Wait for the operation to complete

                # Poll for the VM to be ready
                logger.info(f"VM creation for {name} requested. Waiting for it to become RUNNING...")
                is_ready = self.wait_for_vm_ready(name, zone=zone, timeout=300)

                if not is_ready:
                    logger.error(f"VM {name} did not become ready in zone {zone}. Trying next zone.")
                    # Attempt a cleanup in case it's stuck
                    self.delete_vm(name, zone=zone)
                    continue

                logger.info(f"Successfully created and verified VM {name} in zone {zone}.")

                # Get the instance details now that we know it's ready
                created_instance = self.get_instance(name, zone=zone)
                if created_instance:
                    self._vm_cache[name] = created_instance
                    return created_instance.network_interfaces[0].access_configs[0].nat_i_p
                else:
                    logger.error(f"VM {name} was ready but could not be fetched.")
                    continue

            except exceptions.GoogleAPICallError as e:
                logger.error(f"API Error during creation request for VM {name} in zone {zone}: {e}")
                if 'QUOTA' in str(e):
                    logger.warning(f"Quota exceeded in {zone}. Trying next available zone.")
                continue
            except Exception as e:
                logger.error(f"Generic Error creating VM {name} in zone {zone}: {e}")
                continue
        
        logger.error(f"Failed to create VM {name} in all attempted zones.")
        return None

    def _find_vm_zone(self, name: str) -> Optional[str]:
        """Iterates through zones in a region to find a VM."""
        region = self.initial_zone.rsplit('-', 1)[0]
        # Common zone letters for GCP regions
        for zone_letter in ['a', 'b', 'c', 'd', 'f']:
            zone = f"{region}-{zone_letter}"
            try:
                self.compute_client.get(project=self.project_id, zone=zone, instance=name)
                return zone
            except exceptions.NotFound:
                continue
        return None

    def get_instance(self, name: str, zone: Optional[str] = None) -> Optional[Instance]:
        """Gets the full instance object, finding the zone if not provided."""
        if not zone:
            zone = self._find_vm_zone(name)
        
        if zone:
            try:
                instance = self.compute_client.get(project=self.project_id, zone=zone, instance=name)
                return instance
            except exceptions.NotFound:
                logger.warning(f"Instance {name} not found in zone {zone} during get call.")
                return None
            except exceptions.GoogleAPICallError as e:
                logger.error(f"Error fetching instance {name} from zone {zone}: {e}")
                return None
        return None

    def delete_vm(self, name: str, zone: Optional[str] = None) -> bool:
        """Delete a VM instance, finding its zone if not provided."""
        if not zone:
            zone = self._find_vm_zone(name)
        
        if not zone:
            logger.warning(f"Could not find VM {name} to delete. It may already be gone.")
            if name in self._vm_cache:
                del self._vm_cache[name]
            return True

        try:
            logger.info(f"Requesting deletion of VM {name} from zone {zone}.")
            operation = self.compute_client.delete(project=self.project_id, zone=zone, instance=name)
            operation.result()  # Wait for the operation to complete

            if name in self._vm_cache:
                del self._vm_cache[name]
            logger.info(f"Successfully deleted VM {name} from zone {zone}.")
            return True
        except exceptions.NotFound:
            logger.warning(f"VM {name} was not found in zone {zone} for deletion. Assuming it's already gone.")
            if name in self._vm_cache:
                del self._vm_cache[name]
            return True
        except Exception as e:
            logger.error(f"Failed to delete VM {name}: {e}")
            return False

    def get_vm_status(self, name: str, zone: Optional[str] = None) -> Optional[str]:
        """Get the status of a VM instance, finding its zone if necessary."""
        try:
            instance = self.get_instance(name, zone=zone)
            print(f"Instance: {instance}")
            if instance:
                self._vm_cache[name] = instance
                return instance.status
            else:
                if name in self._vm_cache:
                    del self._vm_cache[name]
                return None
        except Exception as e:
            logger.error(f"Failed to get status for VM {name}: {e}")
            return None

    def list_vms(self) -> Dict[str, Instance]:
        """List all VM instances in the project's initial zone."""
        self._vm_cache.clear()
        try:
            instance_list = self.compute_client.list(project=self.project_id, zone=self.initial_zone)
            self._vm_cache = {instance.name: instance for instance in instance_list}
            return self._vm_cache
        except Exception as e:
            logger.error(f"Failed to list VMs: {e}")
            return {}

    def wait_for_vm_ready(self, name: str, zone: str, timeout: int = 300) -> bool:
        """Wait for a VM to enter the 'RUNNING' state."""
        start_time = time.time()
        while True:
            status = self.get_vm_status(name, zone=zone)
            if status == "RUNNING":
                return True
            if status in ("TERMINATED", "STOPPED"):
                logger.error(f"VM {name} entered state '{status}' while waiting to become ready.")
                return False
            if time.time() - start_time > timeout:
                logger.error(f"Timed out waiting for VM {name} to be ready.")
                return False
            time.sleep(10)