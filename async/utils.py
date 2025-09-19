import asyncio
import json
import random
import sys
import redisstore
from chat import workload
from chat.config import get_config
from sync.redis_sync_utils import send_request_and_await

SESSION_ID = None
SERVER_ID = random.uniform(0, 322321)
redis_client = get_config().redis_client


def make_username_key(username):
    return f"username:{username}"


def create_user(session_id, username, password):
    username_key = make_username_key(username)
    hashed_password = bcrypt.hashpw(str(password).encode("utf-8"), bcrypt.gensalt(10))

    # Convert bytes to string for storage
    hashed_password_str = hashed_password.decode("utf-8")

    next_id = send_request_and_await(SESSION_ID, "INCR", "total_users", None, None)

    user_key = f"user:{next_id}"

    send_request_and_await(SESSION_ID, "SET", username_key, user_key, None)
    send_request_and_await(
        SESSION_ID, "HMSET", user_key, {"username": username, "password": hashed_password_str}, None
    )
    send_request_and_await(SESSION_ID, "SADD", f"user:{next_id}:rooms", "0", None)

    return {"id": next_id, "username": username}


def get_messages(room_id=0, offset=0, size=50):
    pending_awaits = {*()}
    room_key = f"room:{room_id}"
    future_0 = AsyncSendRequest(SESSION_ID, "EXISTS", room_key)
    pending_awaits.add(future_0)
    room_exists = AsyncGetResponse(SESSION_ID, future_0)
    pending_awaits.remove(future_0)
    if not room_exists:
        for future in pending_awaits:
            AsyncGetResponse(SESSION_ID, future)
        return (pending_awaits, [])
    else:
        future_1 = AsyncSendRequest(SESSION_ID, "ZREVRANGE", room_key, offset, offset + size)
        pending_awaits.add(future_1)
        values = AsyncGetResponse(SESSION_ID, future_1)
        pending_awaits.remove(future_1)

        for future in pending_awaits:
            AsyncGetResponse(SESSION_ID, future)
        return (
            pending_awaits,
            list(map(lambda x: json.loads(x.decode("utf-8")), values)),
        )

    for future in pending_awaits:
        AsyncGetResponse(SESSION_ID, future)
    return (pending_awaits, None)


def hmget(key, key2):
    pending_awaits = {*()}
    "Wrapper around hmget to unpack bytes from hmget"
    future_0 = AsyncSendRequest(SESSION_ID, "HMGET", key, key2)
    pending_awaits.add(future_0)
    result = AsyncGetResponse(SESSION_ID, future_0)
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
    future_0 = AsyncSendRequest(SESSION_ID, "SADD", f"user:{user1}:rooms", room_id, "")
    pending_awaits.add(future_0)
    future_1 = AsyncSendRequest(SESSION_ID, "SADD", f"user:{user2}:rooms", room_id, "")
    pending_awaits.add(future_1)
    pending_awaits_hmget, user1 = hmget(f"user:{user1}", "username")
    pending_awaits.update(pending_awaits_hmget)
    pending_awaits_hmget, user2 = hmget(f"user:{user2}", "username")
    pending_awaits.update(pending_awaits_hmget)
    for future in pending_awaits:
        AsyncGetResponse(SESSION_ID, future)
    return (pending_awaits, ({"id": room_id, "names": [user1, user2]}, False))


def init_redis(clientid, explen):
    print("in MDL python", file=sys.stderr)
    global SESSION_ID
    SESSION_ID = session_id
    # workload.simple_workload()
    pending_awaits = {*()}
    if int(clientid) == 0:
        future_0 = AsyncSendRequest(SESSION_ID, "EXISTS", "total_users")
        pending_awaits.add(future_0)
        total_users_exist = AsyncGetResponse(SESSION_ID, future_0)
        pending_awaits.remove(future_0)
        if total_users_exist == "0":
            future_1 = AsyncSendRequest(SESSION_ID, "SET", "total_users", 0)
            pending_awaits.add(future_1)
            future_2 = AsyncSendRequest(SESSION_ID, "SET", f"room:0:name", "General")
            pending_awaits.add(future_2)
            AsyncGetResponse(SESSION_ID, future_1)
            AsyncGetResponse(SESSION_ID, future_2)
            pending_awaits.remove(future_1)
            pending_awaits.remove(future_2)
    elif int(clientid) > 0:
        while True:
            future_0 = AsyncSendRequest(SESSION_ID, "EXISTS", "total_users")
            pending_awaits.add(future_0)
            total_users_exist = AsyncGetResponse(SESSION_ID, future_0)
            pending_awaits.remove(future_0)
            if total_users_exist != "0":
                break
    workload.create(clientid, explen)


def event_stream():
    pending_awaits = {*()}
    "Handle message formatting, etc."
    future_0 = AsyncSendRequest(SESSION_ID "SUBSCRIBE", "MESSAGES")
    pending_awaits.add(future_0)
    future_1 = AsyncSendRequest(SESSION_ID, "LISTEN")
    pending_awaits.add(future_1)
    messages = AsyncGetResponse(SESSION_ID, future_1)
    pending_awaits.remove(future_1)
    for message in messages:
        data = f"data: {str(message)}\n\n"
        yield data
    return (pending_awaits, None)
