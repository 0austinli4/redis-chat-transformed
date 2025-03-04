import time
from chat import utils
from chat import workload
from mdlin import AppRequest, AppResponse


def init_redis(clientid):
    print("using mdl client utils!!")
    pending_awaits = set()
    future_0 = AppRequest("SET", "total_users", 0)
    pending_awaits.add(future_0)
    future_1 = AppRequest("SET", f"room:0:name", "General")
    pending_awaits.add(future_1)
    for future in pending_awaits:
        AppResponse(future)
    print("Completed init")


# Initialize Redis for client 0
init_redis(0)

# Create users
user1 = utils.create_user("alice", "password123")
print("Created User 1:", user1)

user2 = utils.create_user("bob", "securepass")
print("Created User 2:", user2)

# Fetch user keys
print("Alice's user key:", utils.make_username_key("alice"))
print("Bob's user key:", utils.make_username_key("bob"))

# Create a private room
room, error = utils.create_private_room(user1["id"], user2["id"])
if not error:
    print("Created Private Room:", room)

# Send a message from Alice to the private room
timestamp = int(time.time())  # Current UNIX timestamp
workload.add_message(room["id"], user1["id"], "Hello, Bob!", timestamp)
print(f"Alice sent a message at {timestamp}")

# Fetch messages (should be empty initially)
messages = utils.get_messages(room_id=room["id"])
print("Messages in Room:", messages)
