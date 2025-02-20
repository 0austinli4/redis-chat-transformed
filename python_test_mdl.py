import asyncio
import json
import math
import random
import bcrypt
import time
from chat.config import get_config
from mdlin import AppRequest, AppResponse, SyncAppRequest

SERVER_ID = random.uniform(0, 322321)
redis_client = get_config().redis_client


def create():
    num_minutes = 1
    t_end = time.time() + 20 * num_minutes

    while time.time() < t_end:
        before = time.time_ns()
        add_message()
        after = time.time_ns()
        lat = after - before
        optype = "test"
        print(f"app,{lat}")
        print(f"{optype},{lat}")


if __name__ == "__main__":
    create()


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
