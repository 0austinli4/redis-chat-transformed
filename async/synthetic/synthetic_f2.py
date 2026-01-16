import sys
import os

print("=" * 100, file=sys.stderr)
sys.stderr.flush()
print("SIMPLE_TEST.PY ASYNC - FIRST LINE EXECUTING", file=sys.stderr)
sys.stderr.flush()
print("=" * 100, file=sys.stderr)
sys.stderr.flush()

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from iocl.config_env import set_env_from_command_line_args, init_benchmark_with_config
from iocl.iocl_utils import send_request, await_request


def run_app(session_id, client_id, client_type, explen):
    print("RUNNING SIMPLE_TEST.PY (ASYNC VERSION) - IOCL-CT", file=sys.stderr)

    # Simple test: Issue 2 requests concurrently for IOCL
    # Send both requests without waiting
    future_0 = send_request(session_id, "SET", f"test_key_{client_id}_1", "value1", None)
    future_1 = send_request(session_id, "SET", f"test_key_{client_id}_1", "value2", None)

    # Now await both results
    result_0 = await_request(session_id, future_0)
    result_1 = await_request(session_id, future_1)

    print(f"Client {client_id}: Concurrent request results: {result_0}, {result_1}", file=sys.stderr)
    return


print("__name__ is:", __name__, file=sys.stderr)
sys.stderr.flush()

if __name__ == "__main__":
    import argparse
    import sys

    print("=" * 80, file=sys.stderr)
    sys.stderr.flush()
    print("SIMPLE_TEST.PY (ASYNC) STARTING - ARGUMENTS:", sys.argv, file=sys.stderr)
    sys.stderr.flush()
    print("=" * 80, file=sys.stderr)
    sys.stderr.flush()

    parser = argparse.ArgumentParser(description="IOCL Benchmark Client")

    parser.add_argument(
        "--config",
        action="store",
        dest="config_path",
        default="/users/akalaba/IOCL/experiments/configs/1shard_transformed_test.json",
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
    print("PARSED ARGS:", args, file=sys.stderr)
    sys.stderr.flush()

    try:
        print(f"Setting env from command line args...", file=sys.stderr)
        sys.stderr.flush()
        set_env_from_command_line_args(args)

        print(f"Initializing benchmark with config: {args.config_path}", file=sys.stderr)
        sys.stderr.flush()
        init_benchmark_with_config(args.config_path)

        print(f"Importing redisstore...", file=sys.stderr)
        sys.stderr.flush()
        import redisstore
        print(f"redisstore imported successfully", file=sys.stderr)
        sys.stderr.flush()

        print(f"Creating session...", file=sys.stderr)
        sys.stderr.flush()
        session_id = redisstore.custom_init_session()
        print(f"Session created: {session_id}", file=sys.stderr)

        print(f"Calling run_app with clientid={args.clientid}, explen={args.explen}", file=sys.stderr)
        run_app(session_id, args.clientid, "multi_paxos", args.explen)

        print(f"run_app completed successfully", file=sys.stderr)

    except FileNotFoundError:
        print(f"Error: Config file not found at {args.config_path}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error initializing client: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc(file=sys.stderr)
        sys.exit(1)