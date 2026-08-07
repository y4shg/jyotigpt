"""Redis connection helpers.

Provides URL parsing for Redis Sentinel configurations, connection factory
functions, and Sentinel URL construction from environment variables.
"""

import redis
from redis import asyncio as aioredis
from urllib.parse import urlparse


def parse_redis_service_url(redis_url):
    """Parse a ``redis://`` URL into Sentinel connection parameters.

    Returns a dict with ``username``, ``password``, ``service`` (hostname,
    defaults to ``mymaster``), ``port``, and ``db``.
    """
    parsed_url = urlparse(redis_url)
    if parsed_url.scheme != "redis":
        raise ValueError("Invalid Redis URL scheme. Must be 'redis'.")

    return {
        "username": parsed_url.username or None,
        "password": parsed_url.password or None,
        "service": parsed_url.hostname or "mymaster",
        "port": parsed_url.port or 6379,
        "db": int(parsed_url.path.lstrip("/") or 0),
    }


def get_redis_connection(redis_url, redis_sentinels, decode_responses=True):
    """Return a Redis client, routing through Sentinel when sentinels are set."""
    if redis_sentinels:
        redis_config = parse_redis_service_url(redis_url)
        sentinel = redis.sentinel.Sentinel(
            redis_sentinels,
            port=redis_config["port"],
            db=redis_config["db"],
            username=redis_config["username"],
            password=redis_config["password"],
            decode_responses=decode_responses,
        )
        return sentinel.master_for(redis_config["service"])
    else:
        return redis.Redis.from_url(redis_url, decode_responses=decode_responses)


def get_sentinels_from_env(sentinel_hosts_env, sentinel_port_env):
    """Build a list of ``(host, port)`` tuples from env-style config strings."""
    if sentinel_hosts_env:
        sentinel_hosts = sentinel_hosts_env.split(",")
        sentinel_port = int(sentinel_port_env)
        return [(host, sentinel_port) for host in sentinel_hosts]
    return []


def get_sentinel_url_from_env(redis_url, sentinel_hosts_env, sentinel_port_env):
    """Construct a ``redis+sentinel://`` URL from env variables and a base URL."""
    redis_config = parse_redis_service_url(redis_url)
    username = redis_config["username"] or ""
    password = redis_config["password"] or ""
    auth_part = ""
    if username or password:
        auth_part = f"{username}:{password}@"
    hosts_part = ",".join(
        f"{host}:{sentinel_port_env}" for host in sentinel_hosts_env.split(",")
    )
    return f"redis+sentinel://{auth_part}{hosts_part}/{redis_config['db']}/{redis_config['service']}"
