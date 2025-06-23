from typing import Dict, Optional
from dataclasses import dataclass
from enum import Enum

class GPUType(Enum):
    T4 = "nvidia-tesla-t4"
    A100_40GB = "nvidia-tesla-a100-40gb" 
    A100_80GB = "nvidia-tesla-a100-80gb"

class MachineType(Enum):
    # CPU-only machines
    N1_STANDARD_4 = "n1-standard-4"    # 4 vCPUs, 15 GB memory
    N1_STANDARD_8 = "n1-standard-8"    # 8 vCPUs, 30 GB memory
    N1_STANDARD_16 = "n1-standard-16"  # 16 vCPUs, 60 GB memory
    
    # GPU machines
    N1_STANDARD_4_GPU = "n1-standard-4"  # 4 vCPUs, 15 GB memory + GPU
    N1_STANDARD_8_GPU = "n1-standard-8"  # 8 vCPUs, 30 GB memory + GPU
    N1_STANDARD_16_GPU = "n1-standard-16"  # 16 vCPUs, 60 GB memory + GPU
    
    # A2 GPU machines
    A2_HIGHGPU_1G = "a2-highgpu-1g"    # 12 vCPUs, 85 GB memory + 1x A100
    A2_HIGHGPU_2G = "a2-highgpu-2g"    # 24 vCPUs, 170 GB memory + 2x A100
    A2_HIGHGPU_4G = "a2-highgpu-4g"    # 48 vCPUs, 340 GB memory + 4x A100
   

@dataclass
class VMProfile:
    name: str
    machine_type: MachineType
    gpu_type: Optional[GPUType]
    gpu_count: int
    min_cpu_cores: int
    min_memory_gb: int
    volume_size_gb: int
    image_family: str = "ubuntu-2004-lts"
    image_project: str = "ubuntu-os-cloud"
    startup_script_path: str = "/opt/model-serving-system/startup_script.sh"
    description: str = ""
    maintenance_policy: str = "TERMINATE"
    tags: list = None

# Define VM profiles for different use cases
VM_PROFILES: Dict[str, VMProfile] = {
    # Small models (e.g., TinyLlama, GPT-2)
    "small": VMProfile(
        name="small",
        machine_type=MachineType.N1_STANDARD_4_GPU,
        gpu_type=GPUType.T4,
        gpu_count=1,
        min_cpu_cores=4,
        min_memory_gb=15,
        volume_size_gb=100,
        image_family="pytorch-latest-gpu-debian-11",
        image_project="deeplearning-platform-release",
        maintenance_policy="TERMINATE",
        tags=["scheduler","http-server","https-server"],
        description="For small models like TinyLlama, GPT-2"
    ),

    

    # Large models (e.g., Llama-13B, Falcon-40B)
    "large": VMProfile(
        name="large",
        machine_type=MachineType.A2_HIGHGPU_1G,
        gpu_type=GPUType.A100_40GB,
        gpu_count=1,
        min_cpu_cores=12,
        min_memory_gb=85,
        volume_size_gb=150,
        image_family="pytorch-latest-gpu-debian-11",
        image_project="deeplearning-platform-release",
        maintenance_policy="TERMINATE",
        tags=["scheduler","http-server","https-server"],
        description="For large models like Llama-13B, Falcon-40B"
    ),

    # A100-specific profile for large models
    "a100": VMProfile(
        name="a100",
        machine_type=MachineType.A2_HIGHGPU_1G,
        gpu_type=GPUType.A100_80GB,
        gpu_count=1,
        min_cpu_cores=12,
        min_memory_gb=85,
        volume_size_gb=150,
        image_family="pytorch-latest-gpu-debian-11",
        image_project="deeplearning-platform-release",
        maintenance_policy="TERMINATE",
        tags=["scheduler","http-server","https-server"],
        description="For large models requiring A100 GPU"
    ),

    # CPU-only profile for lightweight tasks
    "cpu-only": VMProfile(
        name="cpu-only",
        machine_type=MachineType.N1_STANDARD_4,
        gpu_type=None,
        gpu_count=0,
        min_cpu_cores=4,
        min_memory_gb=15,
        volume_size_gb=50,
        image_family="pytorch-latest-cpu-debian-11",
        image_project="deeplearning-platform-release",
        maintenance_policy="TERMINATE",
        tags=["scheduler","http-server","https-server"],
        description="For CPU-only tasks or very small models"
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

def get_vm_profile_for_model(model_id: str) -> VMProfile:
    """Get the appropriate VM profile for a given model ID."""
    profile_name = MODEL_PROFILES.get(model_id, "small")  # Default to small if model not found
    return VM_PROFILES[profile_name]

def get_vm_profile(profile_name: str) -> VMProfile:
    """Get a VM profile by name."""
    if profile_name not in VM_PROFILES:
        raise ValueError(f"Unknown VM profile: {profile_name}")
    return VM_PROFILES[profile_name]

def list_available_profiles() -> Dict[str, str]:
    """List all available VM profiles with their descriptions."""
    return {name: profile.description for name, profile in VM_PROFILES.items()}

def list_model_profiles() -> Dict[str, str]:
    """List all model-to-profile mappings."""
    return MODEL_PROFILES 