import time
from chat import utils_app_sync
from chat import workload_app_sync
from mdlin import SyncAppRequest

def one_op_workload():
    room_id = 1
    content = "Hello"
    user_key = "123"

    print(f"DEBUG: Performing HMSET for user_key: {user_key}")

    result = SyncAppRequest(
        "HMSET", user_key, {"username": "user", "password": "pass"}
    )
    print(f"DEBUG: HMSET result: {result}")

    results = []
    print(f"DEBUG: Starting HMGET iterations for user_key: {user_key}")

    for i in range(100):
        res = SyncAppRequest("HMGET", user_key, "user")
        if i == 0:
            print("Received answer from HMGET, EXPECTED: 'pass': ", res)
    
    print("DEBUG: Completed HMGET iterations")

            
if __name__ == "__main__":
    one_op_workload()

def init_redis(clientid):
    print("using paxos client utils!!")
    SyncAppRequest("SET", "total_users", 0)
    SyncAppRequest("SET", f"room:0:name", "General")
    print("Completed init")

def sequential_redis():
    # Initialize Redis for client 0
    init_redis(0)

    # Create users
    user1 = utils_app_sync.create_user("alice", "password123")
    print("Created User 1:", user1)

    user2 = utils_app_sync.create_user("bob", "securepass")
    print("Created User 2:", user2)

    # Fetch user keys
    print("Alice's user key:", utils_app_sync.make_username_key("alice"))
    print("Bob's user key:", utils_app_sync.make_username_key("bob"))

    # Create a private room
    room, error = utils_app_sync.create_private_room(user1["id"], user2["id"])
    if not error:
        print("Created Private Room:", room)

    # Send a message from Alice to the private room
    timestamp = int(time.time())  # Current UNIX timestamp
    workload_app_sync.add_message(room["id"], user1["id"], "Hello, Bob!", timestamp)
    print(f"Alice sent a message at {timestamp}")

    # Fetch messages (should be empty initially)
    messages = utils_app_sync.get_messages(room_id=room["id"])
    print("Messages in Room:", messages)
