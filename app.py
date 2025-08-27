from chat.app import app, run_app  # noqa
import argparse
from config_env import set_env_from_command_line_args, init_benchmark_with_config

if __name__ == "__main__":
    # monkey patch is "required to force the message queue package to use coroutine friendly functions and classes"
    # check flask-socketio docs https://flask-socketio.readthedocs.io/en/latest/
    import eventlet

    eventlet.monkey_patch()
    parser = argparse.ArgumentParser(description="Short sample app")
    parser.add_argument("--clientid", action="store", dest="clientid", default=0)
    parser.add_argument("--explen", action="store", dest="explen", default=0)
    parser.add_argument(
        "--config",
        action="store",
        dest="config_path",
        default="/users/akalaba/IOCL/experiments/configs/1shard_transformed_test.json",
        help="Path to the JSON configuration file",
    )
    args = parser.parse_args()

    # Set environment from config and command line (order: CLI, then config)
    set_env_from_command_line_args(args)
    init_benchmark_with_config(args.config_path)

    run_app(args.clientid, "mdl", args.explen)
