import asyncio
import json
import math
import random
import sys
import bcrypt
import time
from chat.config import get_config
from mdlin import AppRequest, AppResponse, SyncAppRequest

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

    # Perform 4 AppRequests
    for _ in range(4):
        future = AppRequest("ZADD", room_id, content)
        pending_awaits.append(future)

    for future_await in pending_awaits:
        AppResponse(future_await)


def add_message_sync():
    room_id = 1
    content = "Hello"

    results = []

    # Perform 4 AppRequests
    for _ in range(4):
        res = SyncAppRequest("ZADD", room_id, content)
        results.append(res)
