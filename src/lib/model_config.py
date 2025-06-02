"""
Model Configuration Mapping
Maps endpoints to Hugging Face model IDs and configuration
Shared configuration accessible by head controller and replicas
"""

import json
import os
from typing import Dict, Optional
from dataclasses import dataclass

@dataclass
class ModelConfig:
    model_id: str
    deployment_name: str
    endpoint: str
    max_length: int = 512
    temperature: float = 0.7
    top_p: float = 0.9
    device: str = "auto"  # "cpu", "cuda", "auto"

# Default model configurations - keyed by endpoint
MODEL_CONFIGS = {
    "/v1/chat/gpt2": ModelConfig(
        model_id="gpt2",
        deployment_name="gpt2-small",
        endpoint="/v1/chat/gpt2",
        max_length=256,
        temperature=0.7
    ),
    "/v1/chat/llama2": ModelConfig(
        model_id="meta-llama/Llama-2-7b-chat-hf",
        deployment_name="llama2-7b-chat", 
        endpoint="/v1/chat/llama2",
        max_length=512,
        temperature=0.8
    ),
    "/v1/chat/mistral": ModelConfig(
        model_id="mistralai/Mistral-7B-Instruct-v0.1",
        deployment_name="mistral-7b-instruct",
        endpoint="/v1/chat/mistral",
        max_length=512,
        temperature=0.7
    ),
    "/v1/code/codellama": ModelConfig(
        model_id="codellama/CodeLlama-7b-Python-hf",
        deployment_name="codellama-7b-python",
        endpoint="/v1/code/codellama",
        max_length=1024,
        temperature=0.2
    ),
    "/v1/chat/phi2": ModelConfig(
        model_id="microsoft/phi-2",
        deployment_name="phi2",
        endpoint="/v1/chat/phi2",
        max_length=512,
        temperature=0.7
    ),
    "/v1/chat/tinyllama": ModelConfig(
        model_id="TinyLlama/TinyLlama-1.1B-Chat-v1.0",
        deployment_name="tinyllama-1.1b-instruct",
        endpoint="/v1/chat/tinyllama",
        max_length=512,
        temperature=0.7
    )
}

class ModelConfigManager:
    def __init__(self, config_file: str = "model_configs.json"):
        self.config_file = config_file
        self.configs: Dict[str, ModelConfig] = {}  # endpoint -> ModelConfig
        self.load_configs()
    
    def load_configs(self):
        """Load model configurations from file or use defaults"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    
                for endpoint, config_dict in data.items():
                    self.configs[endpoint] = ModelConfig(**config_dict)
                    
                print(f"[ModelConfigManager] Loaded {len(self.configs)} model configs from {self.config_file}")
            except Exception as e:
                print(f"[ModelConfigManager] Error loading config file: {e}, using defaults")
                self.configs = MODEL_CONFIGS.copy()
        else:
            print(f"[ModelConfigManager] Config file {self.config_file} not found, using defaults")
            self.configs = MODEL_CONFIGS.copy()
            self.save_configs() 
    
    def save_configs(self):
        """Save current configurations to file"""
        try:
            data = {}
            for endpoint, config in self.configs.items():
                data[endpoint] = {
                    "model_id": config.model_id,
                    "deployment_name": config.deployment_name,
                    "endpoint": config.endpoint,
                    "max_length": config.max_length,
                    "temperature": config.temperature,
                    "top_p": config.top_p,
                    "device": config.device
                }
            
            with open(self.config_file, 'w') as f:
                json.dump(data, f, indent=2)
                
            print(f"[ModelConfigManager] Saved {len(self.configs)} model configs to {self.config_file}")
        except Exception as e:
            print(f"[ModelConfigManager] Error saving config file: {e}")
    
    def get_model_config_by_endpoint(self, endpoint: str) -> Optional[ModelConfig]:
        """Get model configuration by endpoint"""
        return self.configs.get(endpoint)
    
    def get_model_config_by_deployment_name(self, deployment_name: str) -> Optional[ModelConfig]:
        """Get model configuration by deployment name"""
        for config in self.configs.values():
            if config.deployment_name == deployment_name:
                return config
        return None
    
    def add_model_config(self, endpoint: str, config: ModelConfig):
        """Add a new model configuration"""
        self.configs[endpoint] = config
        self.save_configs()
    
    def remove_model_config(self, endpoint: str) -> bool:
        """Remove a model configuration"""
        if endpoint in self.configs:
            del self.configs[endpoint]
            self.save_configs()
            return True
        return False
    
    def list_models(self) -> Dict[str, ModelConfig]:
        """Get all model configurations"""
        return self.configs.copy()
    
    def get_huggingface_model_id(self, endpoint: str) -> Optional[str]:
        """Get the Hugging Face model ID for an endpoint"""
        config = self.get_model_config_by_endpoint(endpoint)
        return config.model_id if config else None
    
    def get_deployment_name(self, endpoint: str) -> Optional[str]:
        """Get the deployment name for an endpoint"""
        config = self.get_model_config_by_endpoint(endpoint)
        return config.deployment_name if config else None

# Global instance for easy access
model_config_manager = ModelConfigManager()

# Helper functions for easy access
def get_model_config_by_endpoint(endpoint: str) -> Optional[ModelConfig]:
    """Get model configuration by endpoint"""
    return model_config_manager.get_model_config_by_endpoint(endpoint)

def get_huggingface_model_id(endpoint: str) -> Optional[str]:
    """Get Hugging Face model ID by endpoint"""
    return model_config_manager.get_huggingface_model_id(endpoint)

def get_deployment_name(endpoint: str) -> Optional[str]:
    """Get deployment name by endpoint"""
    return model_config_manager.get_deployment_name(endpoint)

def list_available_models() -> Dict[str, ModelConfig]:
    """List all available models"""
    return model_config_manager.list_models() 