import sys
import os

print("=" * 100, file=sys.stderr)
sys.stderr.flush()
print("SIMPLE_TEST.PY SYNC", file=sys.stderr)
sys.stderr.flush()
print("=" * 100, file=sys.stderr)
sys.stderr.flush()

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from iocl.config_env import set_env_from_command_line_args, init_benchmark_with_config
from iocl.iocl_utils import send_request_and_await


def run_app(session_id, client_id, client_type, explen, warmup_secs=0, cooldown_secs=0):
    explen = float(explen)
    print("RUNNING SYNTHETIC_F1.PY (SYNC VERSION) - IOCL-CT", file=sys.stderr)

    rampUp = int(warmup_secs)
    rampDown = int(cooldown_secs)

    if rampUp + rampDown >= explen:
        raise ValueError("Ramp-up + ramp-down must be less than total experiment length")

    steady_secs = explen - rampUp - rampDown
    t_start = time.time()
    t_end = t_start + explen

    print("#start,0,0")

    while time.time() < t_end:
        before = int(time.time() * 1e9)  # latency in ns

        result_0 = send_request_and_await(session_id, "SET", f"test_key_{client_id}_1", "value1", None)
        result_1 = send_request_and_await(session_id, "SET", f"test_key_{client_id}_1", "value1", None)
        
        after = int(time.time() * 1e9)
        lat = after - before
        optime = int((time.time() - t_start) * 1e9)
        optype = "SET"

        now = time.time()
        # Only print latencies during steady-state
        if rampUp <= (now - t_start) < (rampUp + steady_secs):
            print(f"app,{lat},{optime},{client_id}")
            print(f"{optype},{lat},{optime},{client_id}")

    elapsed = time.time() - t_start
    end_sec = int(elapsed)
    end_usec = int((elapsed - end_sec) * 1e6)
    print(f"#end,{end_sec},{end_usec},{client_id}")
    return

if __name__ == "__main__":
    import argparse
    import sys

    print("=" * 80, file=sys.stderr)
    sys.stderr.flush()
    print("SIMPLE_TEST.PY (SYNC) STARTING - ARGUMENTS:", sys.argv, file=sys.stderr)
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
    # print("PARSED ARGS:", args, file=sys.stderr)
    sys.stderr.flush()

    try:
        # print(f"Setting env from command line args...", file=sys.stderr)
        sys.stderr.flush()
        set_env_from_command_line_args(args)

        # print(f"Initializing benchmark with config: {args.config_path}", file=sys.stderr)
        sys.stderr.flush()
        init_benchmark_with_config(args.config_path)

        # print(f"Importing redisstore...", file=sys.stderr)
        # sys.stderr.flush()
        import redisstore
        # print(f"redisstore imported successfully", file=sys.stderr)
        # sys.stderr.flush()

        # print(f"Creating session...", file=sys.stderr)
        # sys.stderr.flush()
        session_id = redisstore.custom_init_session()

        print(f"Calling run_app with clientid={args.clientid}, explen={args.explen}, session_id={session_id}", file=sys.stderr)
        run_app(session_id, args.clientid, "multi_paxos", args.explen)

        # print(f"run_app completed successfully", file=sys.stderr)

    except FileNotFoundError:
        print(f"Error: Config file not found at {args.config_path}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error initializing client: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
