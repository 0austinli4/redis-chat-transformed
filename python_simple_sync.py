import time
from chat import utils_app_sync
from chat import workload_app_sync
from redisstore import SyncAppRequest, InitCustom
import argparse
SESSION_ID = None

def one_op_workload():
    print("Calling sync, one op workload")
    print("DEBUG: Performing simple put operation")

    for i in range(100):
        SyncAppRequest(SESSION_ID, "PUT", "key1", "value1")
        put_result = SyncAppRequest(SESSION_ID, "GET", "key1")
        if i == 0:
            print("Received answer from HMGET, EXPECTED: 'pass': ", put_result)

    print("DEBUG: Completed PUT/GET iterations")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Short sample app")
    parser.add_argument("--clientid", action="store", dest="clientid", default=0)
    parser.add_argument("--explen", action="store", dest="explen", default=0)
    args = parser.parse_args()
    print("Received args", args)
    session_id = redisstore.InitCustom()
    print("GOT SESSION ID", session_id)
    global SESSION_ID
    SESSION_ID = session_id
    one_op_workload()

def init_redis(session_id, clientid):
    print("using paxos client utils!!")
    global SESSION_ID
    SESSION_ID = session_id

    SyncAppRequest(SESSION_ID, "SET", "total_users", 0)
    SyncAppRequest(SESSION_ID, "SET", "room:0:name", "General")
    print("Completed init")


def sequential_redis():
    # Initialize Redis for client 0
    # init_redis(0)

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
    print("Alice sent a message at", timestamp)

    # Fetch messages (should be empty initially)
    messages = utils_app_sync.get_messages(room_id=room["id"])
    print("Messages in Room:", messages)
