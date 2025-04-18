import asyncio
import json
import math
import random
import sys
import bcrypt
from chat import demo_data, workload
from chat.config import get_config

SERVER_ID = random.uniform(0, 322321)
redis_client = get_config().redis_client
from mdlin import AppRequest, AppResponse


def make_username_key(username):
    return f"username:{username}"


def create_user(username, password):
    pending_awaits = {*()}
    username_key = make_username_key(username)
    hashed_password = bcrypt.hashpw(str(password).encode("utf-8"), bcrypt.gensalt(10))

    # Convert bytes to string for storage
    hashed_password_str = hashed_password.decode("utf-8")

    future_0 = AppRequest("INCR", "total_users")

    pending_awaits.add(future_0)

    next_id = AppResponse(future_0)

    pending_awaits.remove(future_0)

    user_key = f"user:{next_id}"

    future_1 = AppRequest("SET", username_key, user_key)
    pending_awaits.add(future_1)

    future_2 = AppRequest(
        "HMSET", user_key, {"username": username, "password": hashed_password_str}
    )
    pending_awaits.add(future_2)

    future_3 = AppRequest("SADD", f"user:{next_id}:rooms", "0")
    pending_awaits.add(future_3)

    for future in pending_awaits:
        AppResponse(future)

    return (pending_awaits, {"id": next_id, "username": username})


def get_messages(room_id=0, offset=0, size=50):
    pending_awaits = {*()}
    room_key = f"room:{room_id}"
    future_0 = AppRequest("EXISTS", room_key)
    pending_awaits.add(future_0)
    room_exists = AppResponse(future_0)
    pending_awaits.remove(future_0)
    if not room_exists:
        for future in pending_awaits:
            AppResponse(future)
        return (pending_awaits, [])
    else:
        future_1 = AppRequest("ZREVRANGE", room_key, offset, offset + size)
        pending_awaits.add(future_1)
        values = AppResponse(future_1)
        pending_awaits.remove(future_1)

        for future in pending_awaits:
            AppResponse(future)
        return (
            pending_awaits,
            list(map(lambda x: json.loads(x.decode("utf-8")), values)),
        )

    for future in pending_awaits:
        AppResponse(future)
    return (pending_awaits, None)


def hmget(key, key2):
    pending_awaits = {*()}
    "Wrapper around hmget to unpack bytes from hmget"
    future_0 = AppRequest("HMGET", key, key2)
    pending_awaits.add(future_0)
    result = AppResponse(future_0)
    pending_awaits.remove(future_0)
    return (pending_awaits, list(map(lambda x: x.decode("utf-8"), result)))


def get_private_room_id(user1, user2):
    if user1 == user2:
        return None
    min_user_id = user2 if user1 > user2 else user1
    max_user_id = user1 if user1 > user2 else user2
    return f"{min_user_id}:{max_user_id}"


def create_private_room(user1, user2):
    pending_awaits = {*()}
    "Create a private room and add users to it"
    room_id = get_private_room_id(user1, user2)
    if not room_id:
        raise RuntimeError("ROOM ID DID NOT RETURN")
        return (pending_awaits, (None, True))
    future_0 = AppRequest("SADD", f"user:{user1}:rooms", room_id)
    pending_awaits.add(future_0)
    future_1 = AppRequest("SADD", f"user:{user2}:rooms", room_id)
    pending_awaits.add(future_1)
    pending_awaits_hmget, user1 = hmget(f"user:{user1}", "username")
    pending_awaits.update(pending_awaits_hmget)
    pending_awaits_hmget, user2 = hmget(f"user:{user2}", "username")
    pending_awaits.update(pending_awaits_hmget)
    for future in pending_awaits:
        AppResponse(future)
    return (pending_awaits, ({"id": room_id, "names": [user1, user2]}, False))


def init_redis(clientid, explen):
    print("in MDL python", file=sys.stderr)
    # workload.simple_workload()
    pending_awaits = {*()}
    if int(clientid) == 0:
        future_0 = AppRequest("EXISTS", "total_users")
        pending_awaits.add(future_0)
        total_users_exist = AppResponse(future_0)
        pending_awaits.remove(future_0)
        if total_users_exist == "0":
            future_1 = AppRequest("SET", "total_users", 0)
            pending_awaits.add(future_1)
            future_2 = AppRequest("SET", f"room:0:name", "General")
            pending_awaits.add(future_2)
            AppResponse(future_1)
            AppResponse(future_2)
            pending_awaits.remove(future_1)
            pending_awaits.remove(future_2)
    elif int(clientid) > 0:
        while True:
            future_0 = AppRequest("EXISTS", "total_users")
            pending_awaits.add(future_0)
            total_users_exist = AppResponse(future_0)
            pending_awaits.remove(future_0)
            if total_users_exist != "0":
                break
    workload.create(clientid, explen)


def event_stream():
    pending_awaits = {*()}
    "Handle message formatting, etc."
    future_0 = AppRequest("SUBSCRIBE", "MESSAGES")
    pending_awaits.add(future_0)
    future_1 = AppRequest("LISTEN")
    pending_awaits.add(future_1)
    messages = AppResponse(future_1)
    pending_awaits.remove(future_1)
    for message in messages:
        data = f"data: {str(message)}\n\n"
        yield data
    return (pending_awaits, None)
