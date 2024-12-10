import asyncio
from chat import utils
import math
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
    print("Creating data")
    pending_awaits = {*()}
    'Create demo data with the default users'
    users = []
    for demo_user in demo_users:
        pending_awaits_create_user, user = utils.create_user(demo_user, demo_password)
        pending_awaits.update(pending_awaits_create_user)
        user['id'] = int(user['id'])
        users.append(user)
    rooms = {}

    print("Finished creating users")
    print("USERS", users)
    print("\n\n\n")

    for user in users:
        other_users = filter(lambda x: x['id'] != user['id'], users)
        for other_user in other_users:
            private_room_id = utils.get_private_room_id(int(user['id']), int(other_user['id']))
            if private_room_id not in rooms:
                print("Creating private room for users")
                pending_awaits_create_private_room, res = utils.create_private_room(user['id'], other_user['id'])
                pending_awaits.update(pending_awaits_create_private_room)
                room = res[0]
                rooms[private_room_id] = room
            pending_awaits_add_message, _ = add_message(private_room_id, other_user['id'], get_greeting(), time.time() - math_random() * 222)
            pending_awaits.update(pending_awaits_add_message)

    def random_user_id():
        return users[math.floor(len(users) * math_random())]['id']
    for key, message in enumerate(messages):
        pending_awaits_add_message, _ = add_message('0', random_user_id(), message, time.time() - (len(messages) - key) * 200)
        pending_awaits.update(pending_awaits_add_message)
    return (pending_awaits, None)
