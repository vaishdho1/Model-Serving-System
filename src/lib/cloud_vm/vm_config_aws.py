# vm_config_aws.py
from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class VMProfile:
    """Defines the configuration for an AWS EC2 instance using names and tags."""
    instance_type: str
    ami_name_pattern: str
    security_group_name: str
    iam_profile_name: str
    key_pair_name: str  # <-- NEW: The name of the EC2 Key Pair to use for SSH
    volume_size_gb: int
    min_cpu_cores: int 
    gpu_count: int     
    tags: List[Dict[str, str]] = field(default_factory=list)

# Define VM profiles, now including the key_pair_name
VM_PROFILES: Dict[str, VMProfile] = {
    "small": VMProfile(
        instance_type="g5.xlarge",
        ami_name_pattern="Deep Learning OSS Nvidia Driver AMI GPU PyTorch*Amazon Linux 2023*",
        security_group_name="scheduler-sg",
        iam_profile_name="EC2ModelServingRole",
        key_pair_name="my-gpu-vm", # <-- ADD THIS: Use the name you created in the AWS console
        volume_size_gb=100,
        min_cpu_cores=4,
        gpu_count=1,
        tags=[{"Key": "Service", "Value": "ModelScheduler"}]
    ),
    "a100": VMProfile(
        instance_type="p3.2xlarge",
        ami_name_pattern="Deep Learning OSS Nvidia Driver AMI GPU PyTorch*Amazon Linux 2023*",
        security_group_name="scheduler-sg",
        iam_profile_name="EC2ModelServingRole",
        key_pair_name="my-gpu-vm", # <-- ADD THIS
        volume_size_gb=150,
        min_cpu_cores=8,
        gpu_count=1,
        tags=[{"Key": "Service", "Value": "ModelScheduler"}]
    ),
    "cpu-only": VMProfile(
        instance_type="t3.large",
        ami_name_pattern="al2023-ami-2023.*-x86_64",
        security_group_name="scheduler-sg",
        iam_profile_name="EC2ModelServingRole",
        key_pair_name="my-gpu-vm", # <-- ADD THIS
        volume_size_gb=50,
        min_cpu_cores=2,
        gpu_count=0,
        tags=[{"Key": "Service", "Value": "ModelScheduler"}]
    )
}

# Model to VM profile mapping
MODEL_PROFILES: Dict[str, str] = {
    # Small models
    "TinyLlama/TinyLlama-1.1B-Chat-v1.0": "small",
    "gpt2": "small",
    "facebook/opt-1.3b": "small",
    
    # Medium models
    "meta-llama/Llama-2-7b-chat-hf": "medium",
    "tiiuae/falcon-7b-instruct": "medium",
    "mosaicml/mpt-7b-instruct": "medium",
    
    # Large models
    "meta-llama/Llama-2-13b-chat-hf": "a100",  # Updated to use A100
    "tiiuae/falcon-40b-instruct": "a100",      # Updated to use A100
    "mosaicml/mpt-30b-instruct": "a100",       # Updated to use A100
}

# The get_vm_profile_for_model function remains the same
def get_vm_profile_for_model(model_id: str) -> VMProfile:
    """Get the appropriate AWS VM profile for a given model ID."""
    profile_name = MODEL_PROFILES.get(model_id, "small")
    return VM_PROFILES[profile_name]