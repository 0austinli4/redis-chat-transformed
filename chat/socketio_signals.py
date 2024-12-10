import asyncio
import json
from flask import session
from flask_socketio import emit, join_room
from chat import utils
from mdlin import AppRequest, AppResponse

def publish(name, message, broadcast=False, room=None):
    pending_awaits = {*()}
    "If the messages' origin is the same sever, use socket.io for sending, otherwise: pub/sub"
    if room:
        emit(name, message, room=room, broadcast=True)
    else:
        emit(name, message, broadcast=broadcast)
    outgoing = {'serverId': utils.SERVER_ID, 'type': name, 'data': message}
    future_0 = AppRequest('PUBLISH', 'MESSAGES', json.dumps(outgoing))
    pending_awaits.add(future_0)
    return (pending_awaits, None)

def io_connect():
    pending_awaits = {*()}
    'Handle socket.io connection, check if the session is attached'
    user = session.get('user', None)
    if not user:
        return (pending_awaits, None)
    user_id = user.get('id', None)
    future_0 = AppRequest('SADD', 'online_users', user_id)
    pending_awaits.add(future_0)
    msg = dict(user)
    msg['online'] = True
    pending_awaits_publish, _ = publish('user.connected', msg, broadcast=True)
    pending_awaits.update(pending_awaits_publish)
    return (pending_awaits, None)

def io_disconnect():
    pending_awaits = {*()}
    user = session.get('user', None)
    if user:
        future_0 = AppRequest('SREM', 'online_users', user['id'])
        pending_awaits.add(future_0)
        msg = dict(user)
        msg['online'] = False
        pending_awaits_publish, _ = publish('user.disconnected', msg, broadcast=True)
        pending_awaits.update(pending_awaits_publish)
    return (pending_awaits, None)

def io_join_room(id_room):
    join_room(id_room)

def io_on_message(message):
    pending_awaits = {*()}
    "Handle incoming message, make sure it's send to the correct room."

    def escape(htmlstring):
        """Clean up html from the incoming string"""
        escapes = {'"': '&quot;', "'": '&#39;', '<': '&lt;', '>': '&gt;'}
        htmlstring = htmlstring.replace('&', '&amp;')
        for seq, esc in escapes.items():
            htmlstring = htmlstring.replace(seq, esc)
        return htmlstring
    message['message'] = escape(message['message'])
    future_0 = AppRequest('SADD', 'online_users', message['from'])
    pending_awaits.add(future_0)
    message_string = json.dumps(message)
    room_id = message['roomId']
    room_key = f'room:{room_id}'
    is_private = not bool(utils.redis_client.exists(f'{room_key}:name'))
    room_has_messages = bool(utils.redis_client.exists(room_key))
    if is_private and (not room_has_messages):
        ids = room_id.split(':')
        msg = {'id': room_id, 'names': [utils.hmget(f'user:{ids[0]}', 'username'), utils.hmget(f'user:{ids[1]}', 'username')]}
        pending_awaits_publish, _ = publish('show.room', msg, broadcast=True)
        pending_awaits.update(pending_awaits_publish)
    future_1 = AppRequest('ZADD', room_key, {message_string: int(message['date'])})
    pending_awaits.add(future_1)
    if is_private:
        pending_awaits_publish, _ = publish('message', message, room=room_id)
        pending_awaits.update(pending_awaits_publish)
    else:
        pending_awaits_publish, _ = publish('message', message, broadcast=True)
        pending_awaits.update(pending_awaits_publish)
    return (pending_awaits, None)
