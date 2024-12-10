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
    print("Add message")
    pending_awaits = {*()}
    room_key = f'room:{room_id}'
    message = {'from': from_id, 'date': timestamp, 'message': content, 'roomId': room_id}

    future_0 = AppRequest('ZADD', room_key, {json.dumps(message): int(message['date'])})
    pending_awaits.add(future_0)
    return (pending_awaits, None)

def create():
    num_minutes = 1
    api = ['create_user', 'create_private_room', 'add_message', 'get_messages']
    t_end = time.time() + 60 * num_minutes
    file1 = open("/users/akalaba/asynch_latencies.txt", "w+")
    selector = 0
    while time.time() < t_end:
        app_request_type = random.randint(1, 100) 
        before = time.time_ns()
        if app_request_type <= 2:
            selector = 0
            user = np.random.zipf(2, 1)
            password = np.random.zipf(2, 1)
            utils.create_user(str(user), str(password))
        elif app_request_type <= 10:
            selector = 1
            user1 = np.random.zipf(2, 1)
            user2 = np.random.zipf(2, 1)
            utils.create_private_room(user1, user2)
        elif app_request_type <= 50:
            selector = 2
            room_id = int(np.random.zipf(2, 1))
            from_id = 44
            content = 'heyyy'
            timestamp = time.time()
            add_message(room_id, from_id, content, timestamp)
        else:
            selector = 3
            room_id = np.random.zipf(2, 1)
            utils.get_messages(room_id)
        
        after = time.time_ns()
        lat = after - before
        optype = api[selector]
        file1.write(f'app,{lat}')
        file1.write(f'{optype},{lat}')

