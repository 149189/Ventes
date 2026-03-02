"""Gunicorn production config."""
import multiprocessing

# Server socket
bind = '0.0.0.0:8000'

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = 'gthread'
threads = 2
worker_tmp_dir = '/dev/shm'  # Use RAM for temp files (faster heartbeat)

# Timeouts
timeout = 120
graceful_timeout = 30
keepalive = 5

# Restart workers after N requests to prevent memory leaks
max_requests = 2000
max_requests_jitter = 200

# Logging
accesslog = '-'
errorlog = '-'
loglevel = 'info'
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" %(D)sμs'

# Process naming
proc_name = 'salescount'

# Security
limit_request_line = 8190
limit_request_fields = 100
limit_request_field_size = 8190
