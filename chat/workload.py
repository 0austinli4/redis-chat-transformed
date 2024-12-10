import asyncio
from chat import utils
import math
import numpy as np
import json
import random
import time
from mdlin import AppRequest, AppResponse

demo_users = ['Pablo', 'Joe', 'Mary', 'Alex']
greetings = ['Hello', 'Hi', 'Yo', 'Hola']
demo_password = 'password123'
messages = ['Hello!', 'Hi, How are you? What about our next meeting?', 'Yeah everything is fine', 'Next meeting tomorrow 10.00AM', "Wow that's great"]

def math_random():
    return random.uniform(0, 1)

def get_greeting():
    return greetings[math.floor(math_random() * len(greetings))]

def add_message(room_id, from_id, content, timestamp):
    pending_awaits = {*()}
    room_key = f'room:{room_id}'
    message = {'from': from_id, 'date': timestamp, 'message': content, 'roomId': room_id}

    future_0 = AppRequest('ZADD', room_key, {json.dumps(message): int(message['date'])})
    pending_awaits.add(future_0)
    for future in pending_awaits:
        AppResponse(future)
    return (pending_awaits, None)

def create():
    num_minutes = 1
    t_end = time.time() + 60 * num_minutes
    while time.time() < t_end:
        app_request_type = random.randint(1, 100) 
        if app_request_type <= 2:
            user = np.random.zipf(2, 1)
            password = np.random.zipf(2, 1)
            utils.create_user(str(user), str(password))
        elif app_request_type <= 8:
            user1 = np.random.zipf(2, 1)
            user2 = np.random.zipf(2, 1)
            utils.create_private_room(user1, user2)
        elif app_request_type <= 40:
            room_id = int(np.random.zipf(2, 1))
            from_id = 44
            content = 'heyyy'
            timestamp = time.time()
            add_message(room_id, from_id, content, timestamp)
        else:
            room_id = np.random.zipf(2, 1)
            utils.get_messages(room_id)
