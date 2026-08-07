"""Realtime engine: the socket.io server and the connection/event bus.

This module owns the process-wide realtime surface:

* the :mod:`socketio` ASGI server (mounted at ``/ws/socket.io`` on the
  root namespace) and its Redis-scaled variant,
* the three connection pools — per-session, per-user and per-model
  (usage) — stored in-process or in Redis depending on
  :envvar:`WEBSOCKET_MANAGER`,
* the inbound event handlers (``connect``, ``disconnect``, ``usage``,
  ``user-join``, ``join-channels``, ``channel-events``, ``user-list``),
* the outbound ``chat-events`` emitters used by chat generation,
  middleware and the pipeline machinery.

The legacy ``jyotigpt.socket.main`` / ``jyotigpt.socket.utils`` modules
re-export the public names here for backwards compatibility.
"""

import asyncio
import json
import logging
import sys
import time
import uuid

import socketio

from jyotigpt.core.environment import (
    ENABLE_WEBSOCKET_SUPPORT,
    GLOBAL_LOG_LEVEL,
    SRC_LOG_LEVELS,
    WEBSOCKET_MANAGER,
    WEBSOCKET_REDIS_LOCK_TIMEOUT,
    WEBSOCKET_REDIS_URL,
    WEBSOCKET_SENTINEL_HOSTS,
    WEBSOCKET_SENTINEL_PORT,
)
from jyotigpt.models.channels import Channels
from jyotigpt.models.chats import Chats
from jyotigpt.models.users import UserNameResponse, Users
from jyotigpt.utils.auth import decode_token
from jyotigpt.utils.redis import (
    get_redis_connection,
    get_sentinel_url_from_env,
    get_sentinels_from_env,
)


logging.basicConfig(stream=sys.stdout, level=GLOBAL_LOG_LEVEL)
log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["SOCKET"])

####################################
# Distributed primitives (Redis)
####################################


class RedisLock:
    """A mutual-exclusion lock: one Redis key, one holder, a TTL.

    ``nx`` acquisition and ``xx`` renewal keep the lock safe across
    multiple worker processes; releasing only works while the key still
    holds this instance's id.
    """

    def __init__(self, redis_url, lock_name, timeout_secs, redis_sentinels=[]):
        self.lock_name = lock_name
        self.lock_id = str(uuid.uuid4())
        self.timeout_secs = timeout_secs
        self.lock_obtained = False
        self.redis = get_redis_connection(
            redis_url, redis_sentinels, decode_responses=True
        )

    def aquire_lock(self):
        # Historical (sic) spelling — kept as the canonical entry point.
        # nx=True only sets the key if it is not already present.
        self.lock_obtained = self.redis.set(
            self.lock_name, self.lock_id, nx=True, ex=self.timeout_secs
        )
        return self.lock_obtained

    acquire_lock = aquire_lock  # corrected alias

    def renew_lock(self):
        # xx=True only sets the key if it is already present.
        return self.redis.set(
            self.lock_name, self.lock_id, xx=True, ex=self.timeout_secs
        )

    def release_lock(self):
        lock_value = self.redis.get(self.lock_name)
        if lock_value and lock_value == self.lock_id:
            self.redis.delete(self.lock_name)


class RedisDict:
    """A dict-like facade over a Redis hash, JSON-serializing values."""

    def __init__(self, name, redis_url, redis_sentinels=[]):
        self.name = name
        self.redis = get_redis_connection(
            redis_url, redis_sentinels, decode_responses=True
        )

    def __setitem__(self, key, value):
        serialized_value = json.dumps(value)
        self.redis.hset(self.name, key, serialized_value)

    def __getitem__(self, key):
        value = self.redis.hget(self.name, key)
        if value is None:
            raise KeyError(key)
        return json.loads(value)

    def __delitem__(self, key):
        result = self.redis.hdel(self.name, key)
        if result == 0:
            raise KeyError(key)

    def __contains__(self, key):
        return self.redis.hexists(self.name, key)

    def __len__(self):
        return self.redis.hlen(self.name)

    def keys(self):
        return self.redis.hkeys(self.name)

    def values(self):
        return [json.loads(v) for v in self.redis.hvals(self.name)]

    def items(self):
        return [(k, json.loads(v)) for k, v in self.redis.hgetall(self.name).items()]

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def clear(self):
        self.redis.delete(self.name)

    def update(self, other=None, **kwargs):
        if other is not None:
            for k, v in other.items() if hasattr(other, "items") else other:
                self[k] = v
        for k, v in kwargs.items():
            self[k] = v

    def setdefault(self, key, default=None):
        if key not in self:
            self[key] = default
        return self[key]

####################################
# Server
####################################


def _create_server():
    """Construct the socket.io server, routing through Redis when scaled."""
    transports = (
        ["websocket"] if ENABLE_WEBSOCKET_SUPPORT else ["polling"]
    )
    if WEBSOCKET_MANAGER == "redis":
        log.debug("Using Redis to manage websockets.")
        if WEBSOCKET_SENTINEL_HOSTS:
            manager = socketio.AsyncRedisManager(
                get_sentinel_url_from_env(
                    WEBSOCKET_REDIS_URL,
                    WEBSOCKET_SENTINEL_HOSTS,
                    WEBSOCKET_SENTINEL_PORT,
                )
            )
        else:
            manager = socketio.AsyncRedisManager(WEBSOCKET_REDIS_URL)
        return socketio.AsyncServer(
            cors_allowed_origins=[],
            async_mode="asgi",
            transports=transports,
            allow_upgrades=ENABLE_WEBSOCKET_SUPPORT,
            always_connect=True,
            client_manager=manager,
        )
    return socketio.AsyncServer(
        cors_allowed_origins=[],
        async_mode="asgi",
        transports=transports,
        allow_upgrades=ENABLE_WEBSOCKET_SUPPORT,
        always_connect=True,
    )


sio = _create_server()

app = socketio.ASGIApp(
    sio,
    socketio_path="/ws/socket.io",
)

####################################
# Connection pools
####################################


def _redis_pool(name, redis_sentinels):
    """A Redis-backed pool for the given ``jyotigpt:<name>`` key."""
    return RedisDict(
        f"jyotigpt:{name}",
        redis_url=WEBSOCKET_REDIS_URL,
        redis_sentinels=redis_sentinels,
    )


if WEBSOCKET_MANAGER == "redis":
    _redis_sentinels = get_sentinels_from_env(
        WEBSOCKET_SENTINEL_HOSTS, WEBSOCKET_SENTINEL_PORT
    )
    SESSION_POOL = _redis_pool("session_pool", _redis_sentinels)
    USER_POOL = _redis_pool("user_pool", _redis_sentinels)
    USAGE_POOL = _redis_pool("usage_pool", _redis_sentinels)

    _cleanup_lock = RedisLock(
        redis_url=WEBSOCKET_REDIS_URL,
        lock_name="usage_cleanup_lock",
        timeout_secs=WEBSOCKET_REDIS_LOCK_TIMEOUT,
        redis_sentinels=_redis_sentinels,
    )
    _pool_lock = _cleanup_lock.aquire_lock
    _pool_lock_renew = _cleanup_lock.renew_lock
    _pool_lock_release = _cleanup_lock.release_lock
else:
    SESSION_POOL = {}
    USER_POOL = {}
    USAGE_POOL = {}
    _pool_lock = _pool_lock_renew = _pool_lock_release = lambda: True

#: Seconds a model may sit idle in the usage pool before it is dropped.
TIMEOUT_DURATION = 3


def get_models_in_use():
    """Model ids currently connected to at least one session."""
    return list(USAGE_POOL.keys())


async def periodic_usage_pool_cleanup():
    """Every few seconds, evict stale sessions from the usage pool.

    The Redis lock ensures only one worker runs the sweep at a time.
    """
    if not _pool_lock():
        log.debug("Usage pool cleanup lock already exists. Not running it.")
        return
    log.debug("Running periodic_usage_pool_cleanup")
    try:
        while True:
            if not _pool_lock_renew():
                log.error("Unable to renew cleanup lock. Exiting usage pool cleanup.")
                raise Exception("Unable to renew usage pool cleanup lock.")

            now = int(time.time())
            send_usage = False
            for model_id, connections in list(USAGE_POOL.items()):
                expired_sids = [
                    sid
                    for sid, details in connections.items()
                    if now - details["updated_at"] > TIMEOUT_DURATION
                ]

                for sid in expired_sids:
                    del connections[sid]

                if not connections:
                    log.debug(f"Cleaning up model {model_id} from usage pool")
                    del USAGE_POOL[model_id]
                else:
                    USAGE_POOL[model_id] = connections

                send_usage = True

            if send_usage:
                # Emit updated usage information after cleaning
                await sio.emit("usage", {"models": get_models_in_use()})

            await asyncio.sleep(TIMEOUT_DURATION)
    finally:
        _pool_lock_release()

####################################
# Inbound events
####################################


def _register_session(user, sid):
    """Associate ``sid`` with ``user`` in the session and user pools."""
    SESSION_POOL[sid] = user.model_dump()
    if user.id in USER_POOL:
        USER_POOL[user.id] = USER_POOL[user.id] + [sid]
    else:
        USER_POOL[user.id] = [sid]


async def _join_user_channels(user, sid):
    """Enter every room for the user's channels (``channel:<id>``)."""
    channels = Channels.get_channels_by_user_id(user.id)
    log.debug(f"{channels=}")
    for channel in channels:
        await sio.enter_room(sid, f"channel:{channel.id}")


@sio.on("usage")
async def usage(sid, data):
    model_id = data["model"]
    # Record the timestamp for the last update
    current_time = int(time.time())

    USAGE_POOL[model_id] = {
        **(USAGE_POOL[model_id] if model_id in USAGE_POOL else {}),
        sid: {"updated_at": current_time},
    }

    # Broadcast the usage data to all clients
    await sio.emit("usage", {"models": get_models_in_use()})


@sio.event
async def connect(sid, environ, auth):
    user = None
    if auth and "token" in auth:
        data = decode_token(auth["token"])

        if data is not None and "id" in data:
            user = Users.get_user_by_id(data["id"])

        if user:
            _register_session(user, sid)
            await sio.emit("user-list", {"user_ids": list(USER_POOL.keys())})
            await sio.emit("usage", {"models": get_models_in_use()})


@sio.on("user-join")
async def user_join(sid, data):
    auth = data["auth"] if "auth" in data else None
    if not auth or "token" not in auth:
        return

    data = decode_token(auth["token"])
    if data is None or "id" not in data:
        return

    user = Users.get_user_by_id(data["id"])
    if not user:
        return

    _register_session(user, sid)
    await _join_user_channels(user, sid)

    await sio.emit("user-list", {"user_ids": list(USER_POOL.keys())})
    return {"id": user.id, "name": user.name}


@sio.on("join-channels")
async def join_channel(sid, data):
    auth = data["auth"] if "auth" in data else None
    if not auth or "token" not in auth:
        return

    data = decode_token(auth["token"])
    if data is None or "id" not in data:
        return

    user = Users.get_user_by_id(data["id"])
    if not user:
        return

    await _join_user_channels(user, sid)


@sio.on("channel-events")
async def channel_events(sid, data):
    room = f"channel:{data['channel_id']}"
    participants = sio.manager.get_participants(
        namespace="/",
        room=room,
    )

    sids = [sid for sid, _ in participants]
    if sid not in sids:
        return

    event_data = data["data"]
    event_type = event_data["type"]

    if event_type == "typing":
        await sio.emit(
            "channel-events",
            {
                "channel_id": data["channel_id"],
                "message_id": data.get("message_id", None),
                "data": event_data,
                "user": UserNameResponse(**SESSION_POOL[sid]).model_dump(),
            },
            room=room,
        )


@sio.on("user-list")
async def user_list(sid):
    await sio.emit("user-list", {"user_ids": list(USER_POOL.keys())})


@sio.event
async def disconnect(sid):
    if sid in SESSION_POOL:
        user = SESSION_POOL[sid]
        del SESSION_POOL[sid]

        user_id = user["id"]
        USER_POOL[user_id] = [_sid for _sid in USER_POOL[user_id] if _sid != sid]

        if len(USER_POOL[user_id]) == 0:
            del USER_POOL[user_id]

        await sio.emit("user-list", {"user_ids": list(USER_POOL.keys())})

####################################
# Outbound event emitters
####################################


def get_event_emitter(request_info, update_db=True):
    """Build an async emitter that streams ``chat-events`` to a user."""

    async def __event_emitter__(event_data):
        user_id = request_info["user_id"]

        session_ids = list(
            set(
                USER_POOL.get(user_id, [])
                + (
                    [request_info.get("session_id")]
                    if request_info.get("session_id")
                    else []
                )
            )
        )

        for session_id in session_ids:
            await sio.emit(
                "chat-events",
                {
                    "chat_id": request_info.get("chat_id", None),
                    "message_id": request_info.get("message_id", None),
                    "data": event_data,
                },
                to=session_id,
            )

        if update_db:
            if "type" in event_data and event_data["type"] == "status":
                Chats.add_message_status_to_chat_by_id_and_message_id(
                    request_info["chat_id"],
                    request_info["message_id"],
                    event_data.get("data", {}),
                )

            if "type" in event_data and event_data["type"] == "message":
                message = Chats.get_message_by_id_and_message_id(
                    request_info["chat_id"],
                    request_info["message_id"],
                )

                if message:
                    content = message.get("content", "")
                    content += event_data.get("data", {}).get("content", "")

                    Chats.upsert_message_to_chat_by_id_and_message_id(
                        request_info["chat_id"],
                        request_info["message_id"],
                        {
                            "content": content,
                        },
                    )

            if "type" in event_data and event_data["type"] == "replace":
                content = event_data.get("data", {}).get("content", "")

                Chats.upsert_message_to_chat_by_id_and_message_id(
                    request_info["chat_id"],
                    request_info["message_id"],
                    {
                        "content": content,
                    },
                )

    return __event_emitter__


def get_event_call(request_info):
    """Build an async caller that invokes ``chat-events`` on a session."""

    async def __event_caller__(event_data):
        response = await sio.call(
            "chat-events",
            {
                "chat_id": request_info.get("chat_id", None),
                "message_id": request_info.get("message_id", None),
                "data": event_data,
            },
            to=request_info["session_id"],
        )
        return response

    return __event_caller__


get_event_caller = get_event_call

####################################
# Pool queries
####################################


def get_user_id_from_session_pool(sid):
    user = SESSION_POOL.get(sid)
    if user:
        return user["id"]
    return None


def get_user_ids_from_room(room):
    active_session_ids = sio.manager.get_participants(
        namespace="/",
        room=room,
    )

    active_user_ids = list(
        set(
            [SESSION_POOL.get(session_id[0])["id"] for session_id in active_session_ids]
        )
    )
    return active_user_ids


def get_active_status_by_user_id(user_id):
    if user_id in USER_POOL:
        return True
    return False
