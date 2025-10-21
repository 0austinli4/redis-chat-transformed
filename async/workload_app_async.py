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
    message_json = json.dumps(message)
    future_0 = send_request(session_id, "PUT", room_key, message_json)
    pending_awaits.add(future_0)
    for future in pending_awaits:
        await_request(session_id, future)
    return (pending_awaits, None)


import sys


def create(session_id, clientid, explen):
    api = ["create_user", "create_private_room", "add_message", "get_messages"]
    t_start = time.time()
    t_end = t_start + int(explen)
    # ramp-up and ramp-down windows in seconds
    rampUp = 10
    rampDown = 10
    # start time marker not required beyond printing
    print("#start,0,0")

    while time.time() < t_end:
        app_request_type = np.random.uniform(0, 100)
        # use nanoseconds for latency only
        before = int(time.time() * 1e9)

        if app_request_type < 2:
            selector = 0
            user = np.random.uniform(0, 100)
            password = np.random.uniform(0, 100)
            utils.create_user(session_id, str(user), str(password))
        elif app_request_type < 10:
            selector = 1
            user1 = int(np.random.uniform(0, 100))
            user2 = int(np.random.uniform(0, 100))
            utils.create_private_room(session_id, user1, user2)
        elif app_request_type < 50:
            selector = 2
            room_id = int(np.random.uniform(0, 100))
            from_id = 44
            content = "heyyy"
            timestamp = time.time()
            add_message(session_id, room_id, from_id, content, timestamp)
        else:
            selector = 3
            room_id = int(np.random.uniform(0, 100))
            utils.get_messages(session_id, room_id)

        after = int(time.time() * 1e9)
        lat = after - before  # latency in nanoseconds
        optime = int((time.time() - t_start) * 1e9)  # time since start in nanoseconds
        optype = api[selector]

        # Only record/print latencies during steady-state (after rampUp and before rampDown)
        now = time.time()
        if now >= (t_start + rampUp) and now < (t_end - rampDown):
            print(f"app,{lat},{optime},{clientid}")
            print(f"{optype},{lat},{optime},{clientid}")

    # end marker exactly compatible with current parser
    elapsed = time.time() - t_start
    end_sec = int(elapsed)
    end_usec = int((elapsed - end_sec) * 1e6)
    print(f"#end,{end_sec},{end_usec},{clientid}")
