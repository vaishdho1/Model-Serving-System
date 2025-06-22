import logging
import sys
import os

def setup_logger(name: str, log_file: str = None) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # IMPORTANT: Prevent duplicate messages by not propagating to root logger
    logger.propagate = False

    if not logger.hasHandlers():
        formatter = logging.Formatter(
            fmt="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        # Console handler
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

        # File handler if provided
        if log_file:
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

    return logger

# Create log directory if not exists
os.makedirs("logs", exist_ok=True)

# Global loggers per component (these can be imported and reused)
headcontroller_logger = setup_logger("HeadController", "logs/headcontroller.log")
proxymanager_logger = setup_logger("ProxyManager", "logs/proxy.log")
deployment_logger = setup_logger("DeploymentManager", "logs/deployment.log")
health_logger = setup_logger("HealthManager", "logs/health.log")
autoscale_logger = setup_logger("AutoScaleManager", "logs/autoscale.log")
nodeinfo_logger = setup_logger("NodeInfo", "logs/nodeinfo.log")

