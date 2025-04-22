import time
from redisstore import SyncAppRequest, InitCustom
import argparse

SESSION_ID = None  # global variable

def one_op_workload():
    global SESSION_ID  # Declare global variable before using it
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
    session_id = InitCustom()
    print("GOT SESSION ID", session_id)
    SESSION_ID = session_id  # Assign the session_id to the global variable
    one_op_workload()
