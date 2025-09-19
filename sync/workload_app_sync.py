import asyncio
import sync.utils_app_sync as utils
import iocl.utils as redis_sync_utils
import math
import numpy as np
import json
import random
import time

try:
    import redisstore
except ImportError:
    redisstore = None
    print(
        "Warning: redisstore module could not be imported. Make sure redisstore.cpython-311-darwin.so is available."
    )

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
    room_key = f"room:{room_id}"
    message = {
        "from": from_id,
        "date": timestamp,
        "message": content,
        "roomId": room_id,
    }
    message_json = json.dumps(message)
    # print("about to call add message")
    utils.send_request_and_await(
        session_id, "PUT", room_key, message_json, ""
    )


def create(session_id, clientid, explen):
    print("SESSION ID", session_id)

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
            user = np.random.uniform(0, 100)
            password = np.random.uniform(0, 100)
            utils_app_sync.create_user(session_id, str(user), str(password))
        elif app_request_type < 10:
            selector = 1
            user1 = int(np.random.uniform(0, 100))
            user2 = int(np.random.uniform(0, 100))
            utils_app_sync.create_private_room(session_id, user1, user2)
        elif app_request_type < 50:
            selector = 2
            room_id = int(np.random.uniform(0, 100))
            from_id = 44
            content = "heyyy"
            timestamp = time.time()
            # Debug: log add_message params
            try:
                import sys
                print(f"[DEBUG] add_message params: room_id={room_id}, from_id={from_id}, content={content}, ts={timestamp}", file=sys.stderr)
            except Exception:
                pass
            add_message(session_id, room_id, from_id, content, timestamp)
        else:
            selector = 3
            room_id = int(np.random.uniform(0, 100))
            # Debug: log before fetching messages
            try:
                import sys
                print(f"[DEBUG] get_messages call: room_id={room_id}", file=sys.stderr)
            except Exception:
                pass
            utils_app_sync.get_messages(session_id, room_id)
        
        after = int(time.time() * 1e9)
        if rampUp <= int(time.time()) and int(time.time()) < (t_end - rampDown):
            lat = after - before
            optype = api[selector]
            print(f"app,{lat}")
            print(f"{optype},{lat}")
