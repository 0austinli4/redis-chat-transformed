import json
import bcrypt
from iocl.iocl_utils import send_request_and_await
import sys


def make_username_key(username):
    return f"username:{username}"


def create_user(session_id, client_id, username, password):
    username_key = make_username_key(username)
    hashed_password = bcrypt.hashpw(str(password).encode("utf-8"), bcrypt.gensalt(10))
    next_id = send_request_and_await(session_id, client_id, "INCR", "total_users", None, None)
    # Debug: log next_id and its type
    try:
        print(f"[DEBUG] create_user next_id={next_id} type={type(next_id)}", file=sys.stderr)
    except Exception:
        pass
    user_key = f"user:{next_id}"

    hashed_password_str = hashed_password.decode("utf-8")

    send_request_and_await(session_id, client_id, "SET", username_key, user_key, None)
    send_request_and_await(
        session_id,
        client_id,
        "HMSET",
        user_key,
        {"username": username, "password": hashed_password_str},
        ""
    )
    send_request_and_await(session_id, client_id, "SADD", f"user:{next_id}:rooms", "0", None)
    return {"id": next_id, "username": username}


def get_messages(session_id, client_id, room_id=0, offset=0, size=10):
    """Check if room with id exists; fetch messages limited by size"""
    room_key = f"room:{room_id}"
    room_exists = send_request_and_await(session_id, client_id, "EXISTS", room_key, None, None)
    # room_exists may be tuple or bool-like depending on bridge; normalize
    if isinstance(room_exists, tuple) and len(room_exists) == 2:
        room_exists = room_exists[1]
    if not room_exists:
        return []
    else:
        values = send_request_and_await(
            session_id, client_id, "ZREVRANGE", room_key, offset, offset + size
        )
        # Debug: log raw values
        try:
            print(f"[DEBUG] get_messages raw values type={type(values)} len={getattr(values, '__len__', lambda: 'NA')()}", file=sys.stderr)
        except Exception:
            pass
            
        return values


def hmget(session_id, client_id, key, key2):
    """Wrapper around hmget to unpack bytes from hmget"""
    result = send_request_and_await(session_id, client_id, "HMGET", key, key2, None)
    return list(result)


def get_private_room_id(user1, user2):
    if user1 == user2:
        return None
    min_user_id = user2 if user1 > user2 else user1
    max_user_id = user1 if user1 > user2 else user2
    return f"{min_user_id}:{max_user_id}"


def create_private_room(session_id, client_id, user1, user2):
    """Create a private room and add users to it"""
    room_id = get_private_room_id(user1, user2)
    if not room_id:
        room_id = 0
    send_request_and_await(session_id, client_id, "SADD", f"user:{user1}:rooms", room_id, None)
    send_request_and_await(session_id, client_id, "SADD", f"user:{user2}:rooms", room_id, None)
    user1 = hmget(session_id, client_id, f"user:{user1}", "username")
    user2 = hmget(session_id, client_id, f"user:{user2}", "username")
    return ({"id": room_id, "names": [user1, user2]}, False)


def event_stream(session_id, client_id):
    """Handle message formatting, etc."""
    send_request_and_await(session_id, client_id, "SUBSCRIBE", "MESSAGES", None, None)
    messages = send_request_and_await(session_id, client_id, "LISTEN", 0, None, None)
    for message in messages:
        data = f"data: {str(message)}\n\n"
        yield data
