import time
from chat import utils
from chat import workload
from redisstore import AsyncSendRequest, AsyncGetResponse

SESSION_ID = None


def one_op_workload():
    user_key = "123"

    print(f"DEBUG: Performing HMSET for user_key: {user_key}")

    future = AsyncSendRequest("HMSET", user_key, "user", "1234567")
    res = AsyncGetResponse(future)
    print("DEBUG: HMSET result: ", res)

    print(f"DEBUG: Starting HMGET iterations for user_key: {user_key}")

    for i in range(100):
        future = AsyncSendRequest("HMGET", user_key, "user")
        res = AsyncGetResponse(future)
        if i == 0:
            print("Received answer from HMGET: ", res)

    print("DEBUG: Completed HMGET iterations")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Short sample app")
    parser.add_argument("--clientid", action="store", dest="clientid", default=0)
    parser.add_argument("--explen", action="store", dest="explen", default=0)
    args = parser.parse_args()

    one_op_workload()


def init_redis(session_id, clientid):
    print("using mdl client utils!!")
    global SESSION_ID
    SESSION_ID = session_id
    pending_awaits = set()
    future_0 = AsyncSendRequest(SESSION_ID, "SET", "total_users", 0)
    pending_awaits.add(future_0)
    future_1 = AsyncSendRequest(SESSION_ID, "SET", f"room:0:name", "General")
    pending_awaits.add(future_1)
    for future in pending_awaits:
        AsyncGetResponse(SESSION_ID, future)
    print("Completed init")


def test_redis_correctness():
    # Initialize Redis for client 0
    init_redis(0)

    # Create users
    user1 = utils.create_user("alice", "password123")
    print("Created User 1:", user1)

    user2 = utils.create_user("bob", "securepass")
    print("Created User 2:", user2)

    # Fetch user keys
    print("Alice's user key:", utils.make_username_key("alice"))
    print("Bob's user key:", utils.make_username_key("bob"))

    # Create a private room
    room, error = utils.create_private_room(user1["id"], user2["id"])
    if not error:
        print("Created Private Room:", room)

    # Send a message from Alice to the private room
    timestamp = int(time.time())  # Current UNIX timestamp
    workload.add_message(room["id"], user1["id"], "Hello, Bob!", timestamp)
    print(f"Alice sent a message at {timestamp}")

    # Fetch messages (should be empty initially)
    messages = utils.get_messages(room_id=room["id"])
    print("Messages in Room:", messages)


import asyncio
import json
import math
import random
import sys
import bcrypt
import time
from chat.config import get_config
from redisstore import AsyncSendRequest, AsyncGetResponse, SyncAppRequest

SERVER_ID = random.uniform(0, 322321)
redis_client = get_config().redis_client


def create(client_type):
    num_minutes = 0.2
    t_end = time.time() + 60 * num_minutes

    while time.time() < t_end:
        before = time.time_ns()
        optype = "test"
        if client_type == "mdl":
            optype = "mdl"
            add_message()
        else:
            optype = "multi_paxos"
            add_message_sync()
        after = time.time_ns()
        lat = after - before
        print(f"app,{lat}")
        print(f"{optype},{lat}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        client_type = sys.argv[1]
        create(client_type)
    else:
        print("Usage: python script.py <client_type>")


def add_message():
    room_id = 1
    content = "Hello"

    pending_awaits = []

    for _ in range(1000):
        future = AsyncSendRequest("ZADD", room_id, content)
        pending_awaits.append(future)

    for future_await in pending_awaits:
        AsyncGetResponse(future_await)


def add_message_sync():
    room_id = 1
    content = "Hello"

    results = []

    # Perform 4 AppRequests
    for _ in range(1000):
        res = SyncAppRequest("ZADD", room_id, content)
        results.append(res)
