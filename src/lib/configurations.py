# Define constants for timeout and retry settings for various services and clients
# Values for health updates
head_store_timeout = 5
head_store_max_retries = 3
head_store_retry_delay = 1
scheduler_replica_heartbeat_interval_seconds = 5
scheduler_health_update_interval = 5

# Values for worker node
worker_ping_timeout = 1
worker_ping_max_retries = 2
worker_ping_retry_delay = 1

#Values for proxy manager
proxy_ping_timeout = 1
proxy_ping_max_retries = 2
proxy_ping_retry_delay = 1
proxy_ping_interval = 2
proxy_heartbeat_interval = 10

# Values for queue size of replicas
min_queue_size = 2
max_queue_size = 10

#Health checks for workers
worker_ping_interval = 10

#Values for autoscaling
autoscaling_interval = 10
scheduling_interval = 10