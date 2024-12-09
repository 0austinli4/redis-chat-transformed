import asyncio
import json
import math
import random
import bcrypt
from chat import demo_data
from chat.config import get_config
SERVER_ID = random.uniform(0, 322321)
redis_client = get_config().redis_client
from mdlin import AppRequest


def make_username_key(username):
    return f'username:{username}'

def create_user(username, password):
    pending_awaits = {*()}
    username_key = make_username_key(username)
    hashed_password = bcrypt.hashpw(str(password).encode('utf-8'), bcrypt.gensalt(10))
    future_0 = AppRequest('INCR', 'total_users')
    pending_awaits.add(future_0)
    next_id = AppResponse(future_0)
    pending_awaits.remove(future_0)
    user_key = f'user:{next_id}'
    future_1 = AppRequest('SET', username_key, user_key)
    pending_awaits.add(future_1)
    future_2 = AppRequest('HMSET', user_key, {'username': username, 'password': hashed_password})
    pending_awaits.add(future_2)
    future_3 = AppRequest('SADD', f'user:{next_id}:rooms', '0')
    pending_awaits.add(future_3)
    next_id = AppResponse(future_0)
    pending_awaits.remove(future_0)
    return (pending_awaits, {'id': next_id, 'username': username})

def get_messages(room_id=0, offset=0, size=50):
    pending_awaits = {*()}
    'Check if room with id exists; fetch messages limited by size'
    room_key = f'room:{room_id}'
    future_0 = AppRequest('EXISTS', room_key)
    pending_awaits.add(future_0)
    room_exists = AppResponse(future_0)
    pending_awaits.remove(future_0)
    if not room_exists:
        return (pending_awaits, [])
    else:
        future_1 = AppRequest('ZREVRANGE', room_key, offset, offset + size)
        pending_awaits.add(future_1)
        values = AppResponse(future_1)
        pending_awaits.remove(future_1)
        return (pending_awaits, list(map(lambda x: json.loads(x.decode('utf-8')), values)))
    return (pending_awaits, None)

def hmget(key, key2):
    pending_awaits = {*()}
    'Wrapper around hmget to unpack bytes from hmget'
    future_0 = AppRequest('HMGET', key, key2)
    pending_awaits.add(future_0)
    result = AppResponse(future_0)
    pending_awaits.remove(future_0)
    return (pending_awaits, list(map(lambda x: x.decode('utf-8'), result)))

def get_private_room_id(user1, user2):
    if math.isnan(user1) or math.isnan(user2) or user1 == user2:
        return None
    min_user_id = user2 if user1 > user2 else user1
    max_user_id = user1 if user1 > user2 else user2
    return f'{min_user_id}:{max_user_id}'

def create_private_room(user1, user2):
    pending_awaits = {*()}
    'Create a private room and add users to it'
    room_id = get_private_room_id(user1, user2)
    if not room_id:
        return (pending_awaits, (None, True))
    future_0 = AppRequest('SADD', f'user:{user1}:rooms', room_id)
    pending_awaits.add(future_0)
    future_1 = AppRequest('SADD', f'user:{user2}:rooms', room_id)
    pending_awaits.add(future_1)
    pending_awaits_hmget, user1 = hmget(f'user:{user1}', 'username')
    pending_awaits.update(pending_awaits_hmget)
    pending_awaits_hmget, user2 = hmget(f'user:{user2}', 'username')
    pending_awaits.update(pending_awaits_hmget)
    return (pending_awaits, ({'id': room_id, 'names': [user1, user2]}, False))

def init_redis():
    pending_awaits = {*()}
    future_0 = AppRequest('EXISTS', 'total_users')
    pending_awaits.add(future_0)
    total_users_exist = AppResponse(future_0)
    pending_awaits.remove(future_0)
    if not total_users_exist:
        future_1 = AppRequest('SET', 'total_users', 0)
        pending_awaits.add(future_1)
        future_2 = AppRequest('SET', f'room:0:name', 'General')
        pending_awaits.add(future_2)
        pending_awaits_create, _ = demo_data.create()
        pending_awaits.update(pending_awaits_create)
    return (pending_awaits, None)

def event_stream():
    pending_awaits = {*()}
    'Handle message formatting, etc.'
    future_0 = AppRequest('SUBSCRIBE', 'MESSAGES')
    pending_awaits.add(future_0)
    future_1 = AppRequest('LISTEN')
    pending_awaits.add(future_1)
    messages = AppResponse(future_1)
    pending_awaits.remove(future_1)
    for message in messages:
        data = f'data: {str(message)}\n\n'
        yield data
    return (pending_awaits, None)