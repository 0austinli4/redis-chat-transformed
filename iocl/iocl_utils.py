import select
import os
import hashlib
import time
from redisstore import (
    async_send_request,
    async_get_response,
    ValueType,
    Operation,
    Value,
    value_to_python,
)
import sys

# Global flag to enable/disable timing instrumentation
ENABLE_TIMING = os.environ.get("IOCL_ENABLE_TIMING", "") == "0"
ENABLE_TIMING = 0


def _ns_timestamp():
    """Get current timestamp in nanoseconds."""
    if hasattr(time, "clock_gettime_ns"):
        return time.clock_gettime_ns(time.CLOCK_MONOTONIC)
    else:
        t = time.clock_gettime(time.CLOCK_MONOTONIC)
        return int(t * 1e9)


def _log_timing(location, timestamp_ns, client_id=0, command_id=None, session_id=None, context=""):
    """
    Log timing information in a parseable format.
    Format: TIMING,<location>,<timestamp_ns>,<client_id>,<command_id>,<session_id>,<context>
    """
    if not ENABLE_TIMING:
        return

    cmd_id_str = str(command_id) if command_id is not None else "-"
    sess_id_str = str(session_id) if session_id is not None else "-"

    print(
        f"TIMING,{location},{timestamp_ns},{client_id},{cmd_id_str},{sess_id_str},{context}",
        file=sys.stderr,
        flush=True,
    )


def _hash_key_to_int(key):
    if isinstance(key, str):
        # Use md5 for deterministic hash, take first 8 bytes as integer
        h = hashlib.md5(key.encode("utf-8")).digest()
        return int.from_bytes(h[:8], "big")
    return key


def convert_value_to_python(value):
    """Convert a Value object to Python native type."""
    return value_to_python(value)


def extract_value_by_type(value):
    """
    Extract the Python value from a Value object.
    """
    if not hasattr(value, "type"):
        return value

    if value.type == ValueType.STRING:
        return value.str
    elif value.type == ValueType.LIST:
        return value.list
    elif value.type == ValueType.SET:
        return value.set
    elif value.type == ValueType.HASH:
        return value.hash
    else:
        return None


def send_request_and_await(session_id, operation, key, new_val, old_val):
    """
    Sends a request to C++ layer and BLOCKS until the response is ready.
    """
    # If operation is a string, map to redisstore.Operation
    if isinstance(operation, str):
        op_str = operation.upper()
        if hasattr(Operation, op_str):
            operation_enum = getattr(Operation, op_str)
        else:
            raise ValueError(f"Unknown operation string: {operation}")
    else:
        operation_enum = operation

    key_int = _hash_key_to_int(key)

    success, command_id = async_send_request(
        session_id, operation_enum, key_int, new_val, old_val
    )

    if not success:
        raise RuntimeError("AsyncSendRequest failed")

    if hasattr(command_id, "type") and command_id.type == ValueType.STRING:
        try:
            command_id = int(command_id.str)
        except ValueError:
            raise RuntimeError("Invalid Value object returned by async_send_request")

    command_id = int(command_id)

    # FIRST TRY
    success, resp = async_get_response(session_id, command_id)

    if success:
        return success, extract_value_by_type(resp)

    # Must wait using eventfd
    try:
        efd = int(resp.str)
    except ValueError:
        raise RuntimeError(f"Expected efd string, got {resp}")

    import fcntl

    try:
        fcntl.fcntl(efd, fcntl.F_GETFD)
    except OSError as e:
        raise RuntimeError(f"EFD {efd} is invalid: {e}")

    timeout = 20
    r, _, _ = select.select([efd], [], [], timeout)

    if not r:
        os.close(efd)
        raise TimeoutError(f"Timeout waiting for command {command_id}")

    try:
        os.read(efd, 8)
    finally:
        os.close(efd)

    # SECOND GET_RESPONSE
    success, result = async_get_response(session_id, command_id)

    if success:
        return success, extract_value_by_type(result)
    else:
        raise RuntimeError(f"Failed to retrieve result after unblocking for command {command_id}")


def send_request(session_id, operation, key, new_val="", old_val=""):
    """
    Sends a request to C++ layer and returns immediately with the command ID.
    """
    if isinstance(operation, str):
        op_str = operation.upper()
        if hasattr(Operation, op_str):
            operation_enum = getattr(Operation, op_str)
        else:
            raise ValueError(f"Unknown operation string: {operation}")
    else:
        operation_enum = operation

    key_int = _hash_key_to_int(key)

    success, command_id = async_send_request(
        session_id, operation_enum, key_int, new_val, old_val
    )

    if not success:
        raise RuntimeError("AsyncSendRequest failed")

    if hasattr(command_id, "type") and command_id.type == ValueType.STRING:
        try:
            command_id = int(command_id.str)
        except ValueError:
            raise RuntimeError("Invalid Value returned by async_send_request")

    return int(command_id)


def await_request(session_id, command_id, timeout=20):
    """
    Waits for the result of a previously sent request.
    """

    success, resp = async_get_response(session_id, command_id)

    if success:
        return success, extract_value_by_type(resp)

    try:
        efd = int(resp.str)
    except ValueError:
        raise RuntimeError(f"Expected efd string, got {resp}")

    import fcntl

    try:
        fcntl.fcntl(efd, fcntl.F_GETFD)
    except OSError as e:
        raise RuntimeError(f"EFD {efd} is invalid: {e}")

    r, _, _ = select.select([efd], [], [], timeout)

    if not r:
        os.close(efd)
        raise TimeoutError(f"Timeout waiting for command {command_id}")

    try:
        os.read(efd, 8)
    finally:
        os.close(efd)

    success, result = async_get_response(session_id, command_id)

    if success:
        return success, extract_value_by_type(result)
    else:
        raise RuntimeError(f"Failed to retrieve result after unblocking for command {command_id}")

