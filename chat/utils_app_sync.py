import asyncio
import json
import math
import random
import bcrypt
from chat import workload_app_sync
from chat.config import get_config
from mdlin import SyncAppRequest
import sys

SERVER_ID = random.uniform(0, 322321)
redis_client = get_config().redis_client


def make_username_key(username):
    return f"username:{username}"


def create_user(username, password):
    username_key = make_username_key(username)
    hashed_password = bcrypt.hashpw(str(password).encode("utf-8"), bcrypt.gensalt(10))
    next_id = SyncAppRequest("INCR", "total_users")
    user_key = f"user:{next_id}"

    hashed_password_str = hashed_password.decode("utf-8")

    SyncAppRequest("SET", username_key, user_key)
    SyncAppRequest(
        "HMSET", user_key, {"username": username, "password": hashed_password_str}
    )
    SyncAppRequest("SADD", f"user:{next_id}:rooms", "0")
    return {"id": next_id, "username": username}


def get_messages(room_id=0, offset=0, size=50):
    """Check if room with id exists; fetch messages limited by size"""
    room_key = f"room:{room_id}"
    room_exists = SyncAppRequest("EXISTS", room_key)
    if not room_exists:
        return []
    else:
        values = SyncAppRequest("ZREVRANGE", room_key, offset, offset + size)
        return list(map(lambda x: json.loads(x.decode("utf-8")), values))


def hmget(key, key2):
    """Wrapper around hmget to unpack bytes from hmget"""
    result = SyncAppRequest("HMGET", key, key2)
    return list(map(lambda x: x.decode("utf-8"), result))


def get_private_room_id(user1, user2):
    if user1 == user2:
        return None
    min_user_id = user2 if user1 > user2 else user1
    max_user_id = user1 if user1 > user2 else user2
    return f"{min_user_id}:{max_user_id}"


def create_private_room(user1, user2):
    """Create a private room and add users to it"""
    room_id = get_private_room_id(user1, user2)
    if not room_id:
        raise RuntimeError("ROOM ID DID NOT RETURN")
        return (None, True)
    SyncAppRequest("SADD", f"user:{user1}:rooms", room_id)
    SyncAppRequest("SADD", f"user:{user2}:rooms", room_id)
    user1 = hmget(f"user:{user1}", "username")
    user2 = hmget(f"user:{user2}", "username")
    return ({"id": room_id, "names": [user1, user2]}, False)


def init_redis(clientid, explen):
    print("using paxos client utils!!", file=sys.stderr)
    if int(clientid) == 0:
        total_users_exist = SyncAppRequest("EXISTS", "total_users")
        if total_users_exist == "0":
            SyncAppRequest("SET", "total_users", 0)
            SyncAppRequest("SET", f"room:0:name", "General")
    elif int(clientid) > 0:
        while True:
            total_users_exist = SyncAppRequest("EXISTS", "total_users")
            if total_users_exist != "0":
                break
    workload_app_sync.create(clientid, explen)


def event_stream():
    """Handle message formatting, etc."""
    SyncAppRequest("SUBSCRIBE", "MESSAGES")
    messages = SyncAppRequest("LISTEN")
    for message in messages:
        data = f"data: {str(message)}\n\n"
        yield data
