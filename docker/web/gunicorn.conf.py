"""Gunicorn configuration."""

import multiprocessing
import os

bind = "0.0.0.0:8000"

# gthread rather than sync: this workload is IO-bound (Postgres, Redis), so
# threads absorb concurrency far more cheaply than extra processes.
worker_class = "gthread"
workers = min(multiprocessing.cpu_count() * 2 + 1, 5)
threads = 4

# Gunicorn's heartbeat file lives in worker_tmp_dir. On Docker the default
# /tmp is often a disk-backed overlay, and the resulting stalls look like
# random worker timeouts. /dev/shm is memory-backed.
worker_tmp_dir = "/dev/shm"  # noqa: S108

timeout = 30
graceful_timeout = 30
keepalive = 5

# Recycle workers to bound the impact of any slow leak. The jitter stops every
# worker from restarting on the same request count.
max_requests = 1000
max_requests_jitter = 100

# Deliberately NOT preload_app: with preload the SQLAlchemy engine is created
# before fork and children would share socket file descriptors. Enabling it
# requires disposing the engine in post_fork; the memory saving is not worth
# that footgun at this scale.
preload_app = False

# gunicorn accepts literal addresses or "*" here -- NOT CIDR ranges, which it
# rejects at startup. Container IPs are assigned dynamically, so pinning exact
# addresses is impractical.
#
# "*" is safe in this topology and is not where the trust boundary sits:
#   - the web container publishes no host port in production, so only nginx on
#     the internal compose network can reach it at all;
#   - nginx *appends* to X-Forwarded-For, and ProxyFix(x_for=1) reads the
#     rightmost entry -- the hop nginx itself wrote. A client-supplied header
#     lands further left and is ignored.
# Override with an explicit address if the app is ever exposed directly.
forwarded_allow_ips = os.environ.get("FORWARDED_ALLOW_IPS", "*")

accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("LOG_LEVEL", "info").lower()
# The application emits structured JSON logs with request IDs; keep gunicorn's
# own access log minimal and correlate on request_id.
access_log_format = '{"src":"gunicorn","method":"%(m)s","path":"%(U)s","status":"%(s)s","ms":"%(M)s","rid":"%({x-request-id}i)s"}'
