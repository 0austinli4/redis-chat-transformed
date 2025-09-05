import json
import os
import os.path
from config_env import set_env_from_command_line_args, init_benchmark_with_config
import select
import redisstore
from redisstore import async_send_request, async_get_response, ValueType, start_transport


def load_config_and_set_env(config_path):
    """Load JSON config and set environment variables for C++ binding"""

    print(f"Loading config from: {config_path}")

    with open(config_path, "r") as f:
        config = json.load(f)

    # Get the directory containing the config file for resolving relative paths
    config_dir = os.path.dirname(os.path.abspath(config_path))

    # Map JSON keys to environment variable names
    env_mapping = {
        # Basic benchmark settings
        "benchmark_name": "IOCL_BENCHMARK",
        "bench_mode": "IOCL_BENCH_MODE",
        "client_experiment_length": "IOCL_EXP_DURATION",
        "client_ramp_up": "IOCL_WARMUP_SECS",
        "client_ramp_down": "IOCL_COOLDOWN_SECS",
        "tput_interval": "IOCL_TPUT_INTERVAL",
        # Client behavior parameters
        "client_message_timeout": "IOCL_MESSAGE_TIMEOUT",
        "client_abort_backoff": "IOCL_ABORT_BACKOFF",
        "client_retry_aborted": "IOCL_RETRY_ABORTED",
        "client_max_backoff": "IOCL_MAX_BACKOFF",
        "client_max_attempts": "IOCL_MAX_ATTEMPTS",
        "client_fanout": "IOCL_CLIENT_FANOUT",
        "client_issue_concurrent": "IOCL_CLIENT_ISSUE_CONCURRENT",
        # Client timing and behavior
        "mpl": "IOCL_MPL",
        "client_key_selector": "IOCL_CLIENT_KEY_SELECTOR",
        "client_zipf_coefficient": "IOCL_CLIENT_ZIPF_COEFFICIENT",
        "rw_num_ops_txn": "IOCL_RW_NUM_OPS_TXN",
        "client_num_keys": "IOCL_CLIENT_NUM_KEYS",
        # Protocol and consistency
        "replication_protocol": "IOCL_REPLICATION_PROTOCOL",
        "client_protocol_mode": "IOCL_PROTOCOL_MODE",
        "consistency": "IOCL_CONSISTENCY",
        # Network and system settings - SKIP THESE if already set by command line
        "client_id": "IOCL_CLIENT_ID",
        "num_shards": "IOCL_NUM_SHARDS",
        # 'replica_config': 'IOCL_REPLICA_CONFIG_PATHS',  # SKIP - use command line
        # 'network_config': 'IOCL_NET_CONFIG_PATH',       # SKIP - use command line
        # Additional fields from the JSON
        "server_port": "IOCL_SERVER_PORT",
        "truetime_error": "IOCL_CLOCK_ERROR",
        "server_load_time": "IOCL_SERVER_LOAD_TIME",
        "server_preload_keys": "IOCL_SERVER_PRELOAD_KEYS",
        "client_debug_stats": "IOCL_DEBUG_STATS",
        "client_debug_output": "IOCL_DEBUG_OUTPUT",
        "client_rand_sleep": "IOCL_CLIENT_RAND_SLEEP",
        "client_read_percentage": "IOCL_CLIENT_READ_PERCENTAGE",
        "client_write_percentage": "IOCL_CLIENT_WRITE_PERCENTAGE",
        "client_conflict_percentage": "IOCL_CLIENT_CONFLICT_PERCENTAGE",
        "client_rmw_percentage": "IOCL_CLIENT_RMW_PERCENTAGE",
        "client_zipfian_s": "IOCL_CLIENT_ZIPFIAN_S",
        "client_zipfian_v": "IOCL_CLIENT_ZIPFIAN_V",
        "client_max_processors": "IOCL_CLIENT_MAX_PROCESSORS",
        "client_random_coordinator": "IOCL_CLIENT_RANDOM_COORDINATOR",
        "client_disable_gc": "IOCL_CLIENT_DISABLE_GC",
        "client_gc_debug_trace": "IOCL_CLIENT_GC_DEBUG_TRACE",
        "client_cpuprofile": "IOCL_CLIENT_CPUPROFILE",
    }

    # Set environment variables
    for json_key, env_name in env_mapping.items():
        if json_key in config:
            value = config[json_key]

            # Handle list values (like consistency which is ["lin"])
            if isinstance(value, list):
                value = value[0]  # Take first value

            # Convert to string and set environment variable
            os.environ[env_name] = str(value)
            # print(f"Set {env_name} = {value}")

    # Handle nested config (like replication_protocol_settings)
    if "replication_protocol_settings" in config:
        rps = config["replication_protocol_settings"]
        if "message_transport_type" in rps:
            transport_type = rps["message_transport_type"]
            os.environ["IOCL_TRANSPORT_PROTOCOL"] = transport_type
            # print(f"Set IOCL_TRANSPORT_PROTOCOL = {transport_type}")

    # Handle client timing parameters that might be missing
    if "client_arrival_rate" not in config:
        os.environ["IOCL_CLIENT_ARRIVAL_RATE"] = "1.0"
    if "client_think_time" not in config:
        os.environ["IOCL_CLIENT_THINK_TIME"] = "1.0"
    if "client_stay_probability" not in config:
        os.environ["IOCL_CLIENT_STAY_PROBABILITY"] = "0.5"
    if "client_switch_probability" not in config:
        os.environ["IOCL_CLIENT_SWITCH_PROBABILITY"] = "0.0"

    # Handle missing boolean flags
    if "IOCL_DEBUG_STATS" not in os.environ:
        os.environ["IOCL_DEBUG_STATS"] = "false"
    if "IOCL_DEBUG_OUTPUT" not in os.environ:
        os.environ["IOCL_DEBUG_OUTPUT"] = "false"

    # SKIP resolving config paths if they were set by command line
    # This prevents JSON config from overriding command-line paths
    if (
        "IOCL_REPLICA_CONFIG_PATHS" not in os.environ
        and "IOCL_NET_CONFIG_PATH" not in os.environ
    ):
        print("No command-line config paths detected, resolving from JSON config")
        resolve_config_paths(config, config_dir)

    print("Environment variables set successfully")


def resolve_config_paths(config, config_dir):
    """Resolve relative config file paths to absolute paths"""

    # Map of config keys to environment variable names for file paths
    path_mapping = {
        "replica_config": "IOCL_REPLICA_CONFIG_PATHS",
        "network_config": "IOCL_NET_CONFIG_PATH",
        "shard_config": "IOCL_SHARD_CONFIG_PATH",
    }

    for config_key, env_name in path_mapping.items():
        if config_key in config:
            file_path = config[config_key]

            # If it's a relative path, make it absolute
            if not os.path.isabs(file_path):
                abs_path = os.path.join(config_dir, file_path)
                os.environ[env_name] = abs_path
                print(f"Resolved {config_key}: {file_path} -> {abs_path}")
            else:
                os.environ[env_name] = file_path
                print(f"Using absolute path for {config_key}: {file_path}")

    # Handle replica config format string for multiple shards
    if "replica_config_format_str" in config and "num_shards" in config:
        format_str = config["replica_config_format_str"]
        num_shards = config["num_shards"]

        replica_paths = []
        for i in range(num_shards):
            # Replace %d with shard number
            relative_path = format_str.replace("%d", str(i))
            abs_path = os.path.join(config_dir, relative_path)
            replica_paths.append(abs_path)

        # Join multiple paths with comma (as expected by the C++ binding)
        replica_paths_str = ",".join(replica_paths)
        os.environ["IOCL_REPLICA_CONFIG_PATHS"] = replica_paths_str
        # print(f"Set IOCL_REPLICA_CONFIG_PATHS = {replica_paths_str}")

    # Handle shard config format string
    if "shard_config_format_str" in config and "num_shards" in config:
        format_str = config["shard_config_format_str"]
        num_shards = config["num_shards"]

        shard_paths = []
        for i in range(num_shards):
            relative_path = format_str.replace("%d", str(i))
            abs_path = os.path.join(config_dir, relative_path)
            shard_paths.append(abs_path)

        shard_paths_str = ",".join(shard_paths)
        os.environ["IOCL_SHARD_CONFIG_PATHS"] = shard_paths_str
        # print(f"Set IOCL_SHARD_CONFIG_PATHS = {shard_paths_str}")


def send_request_and_await(session_id, operation, key, new_val, old_val):
    """
    Sends a request to the C++ layer and blocks until the response is ready.

    Args:
        session_id (int): The session ID.
        operation (int): The operation to perform.
        key (int): The key for the operation.
        new_val (object): The new value for the operation.
        old_val (object): The old value for the operation.

    Returns:
        tuple: A tuple containing the success status and the result value.

    Raises:
        RuntimeError: If AsyncSendRequest fails.
    """
    print(f"Sending request: session_id={session_id}, operation={operation}, key={key}")

    # Call the C++ AsyncSendRequest function
    success, efd_or_result = async_send_request(
        session_id, operation, key, new_val, old_val
    )

    if not success:
        print(
            f"AsyncSendRequest failed for session_id={session_id}, operation={operation}, key={key}"
        )
        raise RuntimeError("AsyncSendRequest failed")

    # Extract the integer value from efd_or_result if it is a Value object
    if hasattr(efd_or_result, "type") and efd_or_result.type == ValueType.STRING:
        try:
            efd_or_result = int(efd_or_result.str)
            print("POST conversion: result as Value object:", efd_or_result)
        except ValueError:
            print(f"Failed to convert Value.str to int: {efd_or_result.str}")
            raise RuntimeError("Invalid Value object returned by async_send_request")

    # Ensure efd_or_result is an integer
    try:
        efd_or_result = int(efd_or_result)
    except ValueError:
        print(f"Failed to convert efd_or_result to int: {efd_or_result}")
        raise RuntimeError("Invalid efd_or_result returned by async_send_request")
    
    print(
        f"Right before await async response: "
        f"efd_or_result={efd_or_result}, session_id={session_id}"
    )
    # Call AwaitAsynchResponse to check for the result or get the efd
    print("[PYTHON] Calling async_get_response")
    success, efd_or_result = async_get_response(session_id, efd_or_result)

    if success:
        # If the result is directly returned, no need to block
        print(f"Request succeeded: session_id={session_id}, key={key}")
        return success, efd_or_result
    else:
        print(
            f"Request pending, need to block: session_id={session_id}, key={key}, efd_or_result={efd_or_result}"
        )
    print("Converting the request asynch await response")

    # Extract integer value from Value object if necessary
    if hasattr(efd_or_result, "type") and efd_or_result.type == ValueType.STRING:
        try:
            efd_or_result = int(efd_or_result.str)
        except ValueError:
            print(f"Failed to convert Value.str to int: {efd_or_result.str}")
            raise RuntimeError("Invalid Value object returned by async_get_response")

    # If efd_or_result is not a valid file descriptor, raise an error
    if not isinstance(efd_or_result, int) or efd_or_result < 0:
        print(f"Invalid event file descriptor: {efd_or_result}")
        raise RuntimeError(
            "Invalid event file descriptor returned by async_get_response"
        )

    # If efd_or_result is an event file descriptor, block on it
    efd = efd_or_result
    print(f"Blocking on eventfd for session_id={session_id}, key={key}, efd={efd}")
    timeout = 20 # number of seconds of timeout  
    r, _, _ = select.select([efd], [], [], timeout)
    if not r:
        print(
            f"Timeout occurred while waiting for eventfd: session_id={session_id}, key={key}"
        )
        raise TimeoutError("AwaitAsynchResponse timed out")

    if r:
        # Drain the eventfd counter
        os.read(efd, 8)

        # Close the event file descriptor
        os.close(efd)

        # call async get response again to get actual value
        success, result = async_get_response(session_id)
        if success:
            print(
                f"Result received: session_id={session_id}, key={key}, result={result}"
            )
            return success, result
        else:
            print(f"Failed to retrieve result for session_id={session_id}, key={key}")
            raise RuntimeError("Failed to retrieve result after unblocking")


def one_op_workload(session_id):
    print("Calling sync, one op workload")
    print("DEBUG: Performing simple put operation")
    for i in range(10):
        result = send_request_and_await(
            session_id, redisstore.Operation.PUT, 1, "value1", "oldvalue1"
        )
        print(result)
    print("DEBUG: Completed PUT/GET iterations")


def random_op_workload(session_id, experiment_len=30):
    """Run random redisstore operations for experiment_len seconds."""
    import random
    import time

    op_types = [
        redisstore.Operation.PUT,
        redisstore.Operation.GET,
        redisstore.Operation.INCR,
        redisstore.Operation.SET,
        redisstore.Operation.SADD,
        redisstore.Operation.EXISTS,
        redisstore.Operation.HMSET,
        redisstore.Operation.HSET,
        redisstore.Operation.HMGET,
        redisstore.Operation.HGETALL,
        redisstore.Operation.ZADD,
        redisstore.Operation.ZINCRBY,
        redisstore.Operation.ZSCORE,
        redisstore.Operation.ZREVRANGE,
        redisstore.Operation.ZRANGE,
    ]
    start = time.time()
    while time.time() - start < experiment_len:
        op = random.choice(op_types)
        key = f"key{random.randint(1, 100)}"
        value = f"val{random.randint(1, 100)}"
        old_value = f"old{random.randint(1, 100)}"
        try:
            if op == redisstore.Operation.PUT:
                result = redisstore.send_request(session_id, op, key, value)
            elif op == redisstore.Operation.GET:
                result = redisstore.send_request(session_id, op, key, "")
            elif op == redisstore.Operation.INCR:
                result = redisstore.send_request(session_id, op, key, "")
            elif op == redisstore.Operation.SET:
                result = redisstore.send_request(session_id, op, key, value)
            elif op == redisstore.Operation.SADD:
                result = redisstore.send_request(session_id, op, key, value)
            elif op == redisstore.Operation.EXISTS:
                result = redisstore.send_request(session_id, op, key, "")
            elif op == redisstore.Operation.HMSET:
                hash_val = '{"field1": "val1", "field2": "val2"}'
                result = redisstore.send_request(session_id, op, key, hash_val)
            elif op == redisstore.Operation.HSET:
                result = redisstore.send_request(session_id, op, key, value, old_value)
            elif op == redisstore.Operation.HMGET:
                result = redisstore.send_request(session_id, op, key, value)
            elif op == redisstore.Operation.HGETALL:
                result = redisstore.send_request(session_id, op, key, "")
            elif op == redisstore.Operation.ZADD:
                result = redisstore.send_request(session_id, op, key, value, old_value)
            elif op == redisstore.Operation.ZINCRBY:
                result = redisstore.send_request(session_id, op, key, value, old_value)
            elif op == redisstore.Operation.ZSCORE:
                result = redisstore.send_request(session_id, op, key, value)
            elif (
                op == redisstore.Operation.ZREVRANGE
                or op == redisstore.Operation.ZRANGE
            ):
                start_idx = str(random.randint(0, 10))
                stop_idx = str(random.randint(11, 20))
                result = redisstore.send_request(
                    session_id, op, key, start_idx, stop_idx
                )
            else:
                result = None
            print(f"{op.name}: {result}")
        except Exception as e:
            print(f"Error running {op.name}: {e}")
        time.sleep(0.05) # small sleep


if __name__ == "__main__":
    import argparse
    import sys

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

    # Print out all arguments
    # print("Initializing client with the following parameters:")
    # print(f"Config Path: {args.config_path}")
    # print(f"Experiment Length: {args.explen}")
    # print(f"Client ID: {args.clientid}")
    # print(f"Number of Keys: {args.num_keys}")
    # print(f"Number of Shards: {args.num_shards}")
    # print(f"Replica Config Paths: {args.replica_config_paths}")
    # print(f"Network Config Path: {args.net_config_path}")
    # print(f"Client Host: {args.client_host}")
    # print(f"Transport Protocol: {args.trans_protocol}")

    try:
        # First, set environment variables from command line arguments
        # This takes precedence over the JSON config file
        set_env_from_command_line_args(args)

        # Then load the JSON config file (for any additional settings)
        # The JSON config will NOT override config paths if they were set by command line
        init_benchmark_with_config(args.config_path)

        # Now call the C++ binding
        import redisstore

        session_id = redisstore.custom_init_session()
        print("GOT SESSION ID", session_id)
        redisstore.start_transport()
        one_op_workload(session_id)
    except FileNotFoundError:
        print(f"Error: Config file not found at {args.config_path}")
        sys.exit(1)
    except Exception as e:
        print(f"Error initializing client: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
