import json
import random
import bcrypt
import sys
import app_request as app
import time

def make_username_key(username):
    return f"username:{username}"

def create_user(username, password):
    username_key = make_username_key(username)
    hashed_password = bcrypt.hashpw(str(password).encode("utf-8"), bcrypt.gensalt(10))
    next_id = app.AppRequest("INCR", "total_users")
    user_key = f"user:{next_id}"

    hashed_password_str = hashed_password.decode("utf-8")

    app.AppRequest("SET", username_key, user_key)

    app.AppRequest("HMSET", user_key, {"username": username, "password": hashed_password_str})

    app.AppRequest("SADD", f"user:{next_id}:rooms", "0")
    return {"id": next_id, "username": username}


def get_messages(room_id=0, offset=0, size=50):
    """Check if room with id exists; fetch messages limited by size"""
    room_key = f"room:{room_id}"
    room_exists = app.AppRequest("EXISTS", room_key)
    if not room_exists:
        print("Room doesn't exist")
        return []
    else:
        print("Room exists!")
        values = app.AppRequest("ZREVRANGE", room_key, str(offset), str(offset + size))
        return [json.loads(msg) for msg in values if msg]


def hmget(key, key2):
    """Wrapper around hmget to unpack bytes from hmget"""
    print("Key", key, "Key2", key2)
    result = app.AppRequest("HMGET", key, key2)
    print("RESULT", result)
    return list(result)


def get_private_room_id(user1, user2):
    if user1 == user2:
        return None
    min_user_id = user2 if user1 > user2 else user1
    max_user_id = user1 if user1 > user2 else user2
    return f"{min_user_id}:{max_user_id}"


def create_private_room(user1, user2):
    """Create a private room and add users to it"""
    room_id = get_private_room_id(user1, user2)
    if not room_id:
        raise RuntimeError("ROOM ID DID NOT RETURN")
        return (None, True)
    app.AppRequest("SADD", f"user:{user1}:rooms", room_id)
    app.AppRequest("SADD", f"user:{user2}:rooms", room_id)
    user1 = hmget(f"user:{user1}", "username")
    user2 = hmget(f"user:{user2}", "username")
    return ({"id": room_id, "names": [user1, user2]}, False)

def add_message(room_id, from_id, content, timestamp):
    room_key = f"room:{room_id}"
    print("ADD MESSAGE TO ROOM ", room_key)
    message = {
        "from": from_id,
        "date": timestamp,
        "message": content,
        "roomId": room_id,
    }
    # Convert entire message to a single JSON string
    message_json = json.dumps(message)
    # Pass member and score as separate parameters
    app.AppRequest("ZADD", room_key, message_json, str(timestamp))

def test():
    # 1. Create two users and print their details.
    user1 = create_user("alice", "password123")
    user2 = create_user("bob", "secret456")
    print("Created users:")
    print("User1:", user1)
    # print("User2:", user2)
    
    # 2. Retrieve and print the usernames using hmget.
    username1 = hmget(f"user:{user1['id']}", "username")
    username2 = hmget(f"user:{user2['id']}", "username")
    print("Retrieved usernames via hmget:")
    print("User1 username:", username1)
    # print("User2 username:", username2)
    
    # 3. Create a private room between the two users.
    room, error = create_private_room(user1["id"], user2["id"])
    if error:
        print("Error in creating private room")
        return
    print("Private room created with details:")
    print(room)
    
    # 4. Add messages to the private room.
    current_time = int(time.time())
    add_message(room["id"], user1["id"], "Hello Bob!", current_time)
    time.sleep(1)  # Ensure a different timestamp for the next message
    add_message(room["id"], user2["id"], "Hi Alice!", current_time + 1)
    
    # 5. Retrieve messages from the room and print them.
    messages = get_messages(room["id"], 0, 10)
    print("Retrieved messages from the private room:")
    for msg in messages:
        print(msg)

if __name__ == "__main__":
    test()
