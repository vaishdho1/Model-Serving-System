# Define constants for timeout and retry settings for various services and clients
# Values for health updates
head_store_timeout = 5
head_store_max_retries = 3
head_store_retry_delay = 1
scheduler_replica_heartbeat_interval_seconds = 3
scheduler_health_update_interval = 3

# Values for worker node
worker_ping_timeout = 1
worker_ping_max_retries = 2
worker_ping_retry_delay = 1
