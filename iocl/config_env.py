import os
import json


def load_config_and_set_env(config_path):
    """Load JSON config and set environment variables for C++ binding"""
    print(f"Loading config from: {config_path}")
    with open(config_path, "r") as f:
        config = json.load(f)
    config_dir = os.path.dirname(os.path.abspath(config_path))
    env_mapping = {
        "benchmark_name": "IOCL_BENCHMARK",
        "bench_mode": "IOCL_BENCH_MODE",
        "client_experiment_length": "IOCL_EXP_DURATION",
        "client_ramp_up": "IOCL_WARMUP_SECS",
        "client_ramp_down": "IOCL_COOLDOWN_SECS",
        "tput_interval": "IOCL_TPUT_INTERVAL",
        "client_message_timeout": "IOCL_MESSAGE_TIMEOUT",
        "client_abort_backoff": "IOCL_ABORT_BACKOFF",
        "client_retry_aborted": "IOCL_RETRY_ABORTED",
        "client_max_backoff": "IOCL_MAX_BACKOFF",
        "client_max_attempts": "IOCL_MAX_ATTEMPTS",
        "client_fanout": "IOCL_CLIENT_FANOUT",
        "client_issue_concurrent": "IOCL_CLIENT_ISSUE_CONCURRENT",
        "mpl": "IOCL_MPL",
        "client_key_selector": "IOCL_CLIENT_KEY_SELECTOR",
        "client_zipf_coefficient": "IOCL_CLIENT_ZIPF_COEFFICIENT",
        "rw_num_ops_txn": "IOCL_RW_NUM_OPS_TXN",
        "client_num_keys": "IOCL_CLIENT_NUM_KEYS",
        "replication_protocol": "IOCL_REPLICATION_PROTOCOL",
        "client_protocol_mode": "IOCL_PROTOCOL_MODE",
        "consistency": "IOCL_CONSISTENCY",
        "client_id": "IOCL_CLIENT_ID",
        "num_shards": "IOCL_NUM_SHARDS",
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
    for json_key, env_name in env_mapping.items():
        if json_key in config:
            value = config[json_key]
            if isinstance(value, list):
                value = value[0]
            os.environ[env_name] = str(value)
            # print(f"Set {env_name} = {value}")
    if "replication_protocol_settings" in config:
        rps = config["replication_protocol_settings"]
        if "message_transport_type" in rps:
            transport_type = rps["message_transport_type"]
            os.environ["IOCL_TRANSPORT_PROTOCOL"] = transport_type
            # print(f"Set IOCL_TRANSPORT_PROTOCOL = {transport_type}")
    if "client_arrival_rate" not in config:
        os.environ["IOCL_CLIENT_ARRIVAL_RATE"] = "1.0"
    if "client_think_time" not in config:
        os.environ["IOCL_CLIENT_THINK_TIME"] = "1.0"
    if "client_stay_probability" not in config:
        os.environ["IOCL_CLIENT_STAY_PROBABILITY"] = "0.5"
    if "client_switch_probability" not in config:
        os.environ["IOCL_CLIENT_SWITCH_PROBABILITY"] = "0.0"
    if "IOCL_DEBUG_STATS" not in os.environ:
        os.environ["IOCL_DEBUG_STATS"] = "false"
    if "IOCL_DEBUG_OUTPUT" not in os.environ:
        os.environ["IOCL_DEBUG_OUTPUT"] = "false"
    if (
        "IOCL_REPLICA_CONFIG_PATHS" not in os.environ
        and "IOCL_NET_CONFIG_PATH" not in os.environ
    ):
        print("No command-line config paths detected, resolving from JSON config")
        resolve_config_paths(config, config_dir)
    else:
        print(
            "Command-line config paths detected, skipping JSON config path resolution"
        )
    print("Environment variables set successfully")


def resolve_config_paths(config, config_dir):
    path_mapping = {
        "replica_config": "IOCL_REPLICA_CONFIG_PATHS",
        "network_config": "IOCL_NET_CONFIG_PATH",
        "shard_config": "IOCL_SHARD_CONFIG_PATH",
    }
    for config_key, env_name in path_mapping.items():
        if config_key in config:
            file_path = config[config_key]
            if not os.path.isabs(file_path):
                abs_path = os.path.join(config_dir, file_path)
                os.environ[env_name] = abs_path
                print(f"Resolved {config_key}: {file_path} -> {abs_path}")
            else:
                os.environ[env_name] = file_path
                print(f"Using absolute path for {config_key}: {file_path}")
    if "replica_config_format_str" in config and "num_shards" in config:
        format_str = config["replica_config_format_str"]
        num_shards = config["num_shards"]
        replica_paths = []
        for i in range(num_shards):
            relative_path = format_str.replace("%d", str(i))
            abs_path = os.path.join(config_dir, relative_path)
            replica_paths.append(abs_path)
        replica_paths_str = ",".join(replica_paths)
        os.environ["IOCL_REPLICA_CONFIG_PATHS"] = replica_paths_str
        print(f"Set IOCL_REPLICA_CONFIG_PATHS = {replica_paths_str}")
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
        print(f"Set IOCL_SHARD_CONFIG_PATHS = {shard_paths_str}")


def set_env_from_command_line_args(args):
    if args.clientid is not None:
        os.environ["IOCL_CLIENT_ID"] = str(args.clientid)
        # print(f"Set IOCL_CLIENT_ID = {args.clientid}")
    if args.num_keys is not None:
        os.environ["IOCL_CLIENT_NUM_KEYS"] = str(args.num_keys)
        # print(f"Set IOCL_CLIENT_NUM_KEYS = {args.num_keys}")
    if args.num_shards is not None:
        os.environ["IOCL_NUM_SHARDS"] = str(args.num_shards)
        # print(f"Set IOCL_NUM_SHARDS = {args.num_shards}")
    if args.replica_config_paths is not None:
        os.environ["IOCL_REPLICA_CONFIG_PATHS"] = args.replica_config_paths
        # print(f"Set IOCL_REPLICA_CONFIG_PATHS = {args.replica_config_paths}")
    if args.net_config_path is not None:
        os.environ["IOCL_NET_CONFIG_PATH"] = args.net_config_path
        # print(f"Set IOCL_NET_CONFIG_PATH = {args.net_config_path}")
    if args.client_host is not None:
        os.environ["IOCL_CLIENT_HOST"] = args.client_host
        # print(f"Set IOCL_CLIENT_HOST = {args.client_host}")
    if args.trans_protocol is not None:
        os.environ["IOCL_TRANSPORT_PROTOCOL"] = args.trans_protocol
        # print(f"Set IOCL_TRANSPORT_PROTOCOL = {args.trans_protocol}")


def init_benchmark_with_config(config_path):
    load_config_and_set_env(config_path)
