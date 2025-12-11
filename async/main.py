
import sys
import os
import workload_app_async
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import argparse
from iocl.config_env import set_env_from_command_line_args, init_benchmark_with_config
from iocl.iocl_utils import send_request, await_request
import redisstore

def run_app(session_id, client_id, client_type, explen, warmup_secs, cooldown_secs):
    # print("in MDL python", file=sys.stderr)

    pending_awaits = {*()}
    if int(client_id) == 0:
        future_0 = send_request(session_id, "EXISTS", "total_users")
        pending_awaits.add(future_0)
        total_users_exist = await_request(session_id, future_0)
        pending_awaits.remove(future_0)
        if total_users_exist == "0":
            future_1 = send_request(session_id, "SET", "total_users", 0)
            pending_awaits.add(future_1)
            future_2 = send_request(session_id, "SET", f"room:0:name", "General")
            pending_awaits.add(future_2)
            await_request(session_id, future_1)
            await_request(session_id, future_2)
            pending_awaits.remove(future_1)
            pending_awaits.remove(future_2)
    elif int(client_id) > 0:
        while True:
            future_0 = send_request(session_id, "EXISTS", "total_users")
            pending_awaits.add(future_0)
            total_users_exist = await_request(session_id, future_0)
            pending_awaits.remove(future_0)
            if total_users_exist != "0":
                break
    workload_app_async.create(session_id, client_id, explen, warmup_secs, cooldown_secs)



if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="IOCL Benchmark Client")

    parser.add_argument(
        "--config",
        action="store",
        dest="config_path",
        default="/users/akalaba/IOCL/experiments/configs/1shard_transformed_test_wisc.json",
        # default="/users/akalaba/IOCL/experiments/configs/1shard_transformed_test.json",
        help="Path to the JSON configuration file",
    )
    parser.add_argument(
        "--explen",
        action="store",
        dest="explen",
        default=30,
        help="Experiment length override",
    )
    parser.add_argument("--warmup_secs", type=int, default=0, help="Warmup seconds")
    parser.add_argument("--cooldown_secs", type=int, default=0, help="Cooldown seconds")
    parser.add_argument("--clientid", type=int, default=0, help="Client ID")
    parser.add_argument("--num_keys", type=int, default=1000000, help="Number of keys")
    parser.add_argument("--num_shards", type=int, default=1, help="Number of shards")
    parser.add_argument(
        "--replica_config_paths",
        type=str,
        default="",
        help="Path(s) to replica config(s)",
    )
    parser.add_argument(
        "--net_config_path", type=str, default="", help="Path to network config"
    )
    parser.add_argument(
        "--client_host", type=str, default="localhost", help="Client host name"
    )
    parser.add_argument(
        "--trans_protocol",
        type=str,
        choices=["tcp", "udp"],
        default="tcp",
        help="Transport protocol",
    )

    parser.add_argument("--partitioner", type=str, default="", help="Partitioner type")
    parser.add_argument("--key_selector", type=str, default="", help="Key selector")
    parser.add_argument(
        "--zipf_coefficient", type=float, default=0.0, help="Zipf coefficient"
    )
    parser.add_argument("--debug_stats", action="store_true", help="Enable debug stats")
    parser.add_argument("--delay", type=int, default=0, help="Random delay")
    parser.add_argument(
        "--ping_replicas", type=str, default="", help="Ping replicas flag"
    )
    parser.add_argument("--stats_file", type=str, default="", help="Stats file path")

    args = parser.parse_args()

    try:
        set_env_from_command_line_args(args)
        init_benchmark_with_config(args.config_path)
        session_id = redisstore.custom_init_session()
        # print("Session ID:", session_id)
        run_app(session_id, args.clientid, "iocl/async", args.explen, args.warmup_secs, args.cooldown_secs)

    except FileNotFoundError:
        print(f"Error: Config file not found at {args.config_path}")
        sys.exit(1)
    except Exception as e:
        print(f"Error initializing client: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)