from chat.app_app_sync import app, run_app_sync  # noqa
import argparse

if __name__ == "__main__":
    # monkey patch is "required to force the message queue package to use coroutine friendly functions and classes"
    # check flask-socketio docs https://flask-socketio.readthedocs.io/en/latest/
    import eventlet

    eventlet.monkey_patch()
    parser = argparse.ArgumentParser(description="Short sample app")
    parser.add_argument("--clientid", action="store", dest="clientid", default=0)
    parser.add_argument("--explen", action="store", dest="explen", default=0)
    args = parser.parse_args()

    run_app_sync(args.clientid, "multi_paxos", args.explen)
