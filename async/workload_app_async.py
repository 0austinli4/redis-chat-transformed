import asyncio
import math
import numpy as np
import json
import random
import time
import sys
import os

# Add the parent directory to Python path to find iocl module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from iocl.iocl_utils import send_request, await_request
import utils

demo_users = ["Pablo", "Joe", "Mary", "Alex"]
greetings = ["Hello", "Hi", "Yo", "Hola"]
demo_password = "password123"
messages = [
    "Hello!",
    "Hi, How are you? What about our next meeting?",
    "Yeah everything is fine",
    "Next meeting tomorrow 10.00AM",
    "Wow that's great",
]


def math_random():
    return random.uniform(0, 1)


def get_greeting():
    return greetings[math.floor(math_random() * len(greetings))]


def add_message(session_id, room_id, from_id, content, timestamp):
    pending_awaits = {*()}
    room_key = f"room:{room_id}"
    message = {
        "from": from_id,
        "date": timestamp,
        "message": content,
        "roomId": room_id,
    }

    future_0 = send_request(session_id, "ZADD", room_key, {json.dumps(message): int(message["date"])})
    pending_awaits.add(future_0)
    for future in pending_awaits:
        await_request(future)
    return (pending_awaits, None)


def create(session_id, client_id, explen):
    api = ["create_user", "create_private_room", "add_message", "get_messages"]
    t_end = int(time.time()) + int(explen)
    rampUp = 20
    rampDown = 10

    selector = 0
    while time.time() < t_end:
        app_request_type = np.random.uniform(0, 100)
        before = int(time.time() * 1e9)

        if app_request_type < 2:
            selector = 0
            user = np.random.uniform(0, 1e9)
            password = np.random.uniform(0, 1e9)
            utils.create_user(session_id, str(user), str(password))
        elif app_request_type < 10:
            selector = 1
            user1 = np.random.uniform(0, 1e9)
            user2 = np.random.uniform(0, 1e9)
            utils.create_private_room(session_id, user1, user2)
        elif app_request_type < 50:
            selector = 2
            room_id = int(np.random.uniform(0, 1e9))
            from_id = 44
            content = "heyyy"
            timestamp = time.time()
            add_message(session_id, room_id, from_id, content, timestamp)
        else:
            selector = 3
            room_id = np.random.uniform(0, 1e9)
            utils.get_messages(session_id, room_id)

        after = int(time.time() * 1e9)
        if rampUp <= int(time.time()) and int(time.time()) < (t_end-rampDown):
            lat = after - before
            optype = api[selector]
            print(f"app,{lat}")
            print(f"{optype},{lat}")
