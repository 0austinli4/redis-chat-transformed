import asyncio
import json
import os
import bcrypt
from flask import Response, jsonify, request, session
from chat import utils
from chat.app import app
from chat.auth import auth_middleware
from mdlin import AppRequest


@app.route('/stream')
def stream():
    return Response(utils.event_stream(), mimetype='text/event-stream')

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def catch_all(path):
    return app.send_static_file('index.html')

@app.route('/me')
def get_me():
    user = session.get('user', None)
    return jsonify(user)

@app.route('/links')
def get_links():
    """Returns JSON with available deploy links"""
    repo = open(os.path.join(app.root_path, '../repo.json'))
    data = json.load(repo)
    return jsonify(data)

@app.route('/login', methods=['POST'])
def login():
    pending_awaits = {*()}
    'For now, just simulate session behavior'
    data = request.get_json()
    username = data['username']
    password = data['password']
    username_key = utils.make_username_key(username)
    future_0 = AppRequest('EXISTS', username_key)
    pending_awaits.add(future_0)
    user_exists = AppResponse(future_0)
    pending_awaits.remove(future_0)
    if not user_exists:
        pending_awaits_create_user, new_user = utils.create_user(username, password)
        pending_awaits.update(pending_awaits_create_user)
        session['user'] = new_user
    else:
        future_1 = AppRequest('GET', username_key)
        pending_awaits.add(future_1)
        user_name = AppResponse(future_1)
        pending_awaits.remove(future_1)
        user_key = user_name.decode('utf-8')
        future_2 = AppRequest('GET', user_key)
        pending_awaits.add(future_2)
        data = AppResponse(future_2)
        pending_awaits.remove(future_2)
        if bcrypt.hashpw(password.encode('utf-8'), data[b'password']) == data[b'password']:
            user = {'id': user_key.split(':')[-1], 'username': username}
            session['user'] = user
            return (pending_awaits, (user, 200))
    return (pending_awaits, (jsonify({'message': 'Invalid username or password'}), 404))

@app.route('/logout', methods=['POST'])
@auth_middleware
def logout():
    session['user'] = None
    return (jsonify(None), 200)

@app.route('/users/online')
@auth_middleware
def get_online_users():
    pending_awaits = {*()}
    future_0 = AppRequest('GET', 'online_users')
    pending_awaits.add(future_0)
    members = AppResponse(future_0)
    pending_awaits.remove(future_0)
    online_ids = map(lambda x: x.decode('utf-8'), members)
    users = {}
    user = AppResponse(future_1)
    pending_awaits.remove(future_1)
    for online_id in online_ids:
        future_1 = AppRequest('GET', f'user:{online_id}')
        pending_awaits.add(future_1)
        user = AppResponse(future_1)
        pending_awaits.remove(future_1)
        users[online_id] = {'id': online_id, 'username': user.get(b'username', '').decode('utf-8'), 'online': True}
    return (pending_awaits, (jsonify(users), 200))

@app.route('/rooms/<user_id>')
@auth_middleware
def get_rooms_for_user_id(user_id=0):
    pending_awaits = {*()}
    'Get rooms for the selected user.'
    members = list(utils.redis_client.get(f'user:{user_id}:rooms'))
    room_ids = list(map(lambda x: x.decode('utf-8'), members))
    rooms = []
    name = AppResponse(future_0)
    pending_awaits.remove(future_0)
    for room_id in room_ids:
        future_0 = AppRequest('GET', f'room:{room_id}:name')
        pending_awaits.add(future_0)
        name = AppResponse(future_0)
        pending_awaits.remove(future_0)
        if not name:
            future_1 = AppRequest('EXISTS', f'room:{room_id}')
            pending_awaits.add(future_1)
            room_exists = AppResponse(future_1)
            pending_awaits.remove(future_1)
            if not room_exists:
                continue
            user_ids = room_id.split(':')
            if len(user_ids) != 2:
                return (pending_awaits, (jsonify(None), 400))
            pending_awaits_hmget, name1 = utils.hmget(f'user:{user_ids[0]}', 'username')
            pending_awaits.update(pending_awaits_hmget)
            pending_awaits_hmget, name2 = utils.hmget(f'user:{user_ids[1]}', 'username')
            pending_awaits.update(pending_awaits_hmget)
            rooms.append({'id': room_id, 'names': [name1, name2]})
        else:
            name = AppResponse(future_0)
            pending_awaits.remove(future_0)
            rooms.append({'id': room_id, 'names': [name.decode('utf-8')]})
    return (pending_awaits, (jsonify(rooms), 200))

@app.route('/room/<room_id>/messages')
@auth_middleware
def get_messages_for_selected_room(room_id='0'):
    offset = request.args.get('offset')
    size = request.args.get('size')
    try:
        messages = utils.get_messages(room_id, int(offset), int(size))
        return jsonify(messages)
    except:
        return (jsonify(None), 400)

@app.route('/users')
def get_user_info_from_ids():
    pending_awaits = {*()}
    ids = request.args.getlist('ids[]')
    if ids:
        users = {}
        is_member = AppResponse(future_1)
        pending_awaits.remove(future_1)
        user = AppResponse(future_0)
        pending_awaits.remove(future_0)
        for id in ids:
            future_0 = AppRequest('GET', f'user:{id}')
            pending_awaits.add(future_0)
            future_1 = AppRequest('SISMEMBER', 'online_users', id)
            pending_awaits.add(future_1)
            is_member = AppResponse(future_1)
            pending_awaits.remove(future_1)
            user = AppResponse(future_0)
            pending_awaits.remove(future_0)
            users[id] = {'id': id, 'username': user[b'username'].decode('utf-8'), 'online': bool(is_member)}
        return (pending_awaits, jsonify(users))
    return (pending_awaits, (jsonify(None), 404))