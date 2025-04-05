import asyncio
from chat import utils_app_sync
import math
import numpy as np
import json
import random
import time
from mdlin import SyncAppRequest

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


def add_message(room_id, from_id, content, timestamp):
    room_key = f"room:{room_id}"
    message = {
        "from": from_id,
        "date": timestamp,
        "message": content,
        "roomId": room_id,
    }
    message_json = json.dumps(message)
    SyncAppRequest("ZADD", room_key, message_json, str(timestamp))


def create(clientid, explen):
    api = ["create_user", "create_private_room", "add_message", "get_messages"]
    t_end = int(time.time()) + int(explen)
    rampUp = 20
    rampDown = 10

    selector = 0
    
    while time.time() < t_end:
        app_request_type = np.random.uniform(0, 100)
        before = time.time_ns()

        if app_request_type < 2:
            selector = 0
            user = np.random.uniform(0, 1e9)
            password = np.random.uniform(0, 1e9)
            utils_app_sync.create_user(str(user), str(password))
        elif app_request_type < 10:
            selector = 1
            user1 = int(np.random.uniform(0, 1e9))
            user2 = int(np.random.uniform(0, 1e9))
            utils_app_sync.create_private_room(user1, user2)
        elif app_request_type < 50:
            selector = 2
            room_id = int(np.random.uniform(0, 1e9))
            from_id = 44
            content = "heyyy"
            timestamp = time.time()
            add_message(room_id, from_id, content, timestamp)
        else:
            selector = 3
            room_id = np.random.uniform(0, 1e9)
            utils_app_sync.get_messages(room_id)
        after = time.time_ns()
        if rampUp <= int(time.time()) and int(time.time()) < (t_end-rampDown):
            lat = after - before
            optype = api[selector]
            print(f"app,{lat}")
            print(f"{optype},{lat}")
