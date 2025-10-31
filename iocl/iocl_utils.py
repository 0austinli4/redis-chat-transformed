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
ENABLE_TIMING = os.environ.get("IOCL_ENABLE_TIMING", "") == "1"
ENABLE_TIMING = 1
def _ns_timestamp():
    """Get current timestamp in nanoseconds"""
    # Python 3.7+ has clock_gettime_ns, older versions need conversion
    if hasattr(time, 'clock_gettime_ns'):
        return time.clock_gettime_ns(time.CLOCK_MONOTONIC)
    else:
        # Fallback for Python 3.6 and earlier
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

    print(f"TIMING,{location},{timestamp_ns},{client_id},{cmd_id_str},{sess_id_str},{context}",
          file=sys.stderr, flush=True)


def _hash_key_to_int(key):
    if isinstance(key, str):
        # Use md5 for deterministic hash, take first 8 bytes as integer
        h = hashlib.md5(key.encode("utf-8")).digest()
        return int.from_bytes(h[:8], "big")
    return key


def convert_value_to_python(value):
    """
    Convert a request_utils::Value object to a native Python object.

    Args:
        value (Value): The Value object to convert.

    Returns:
        object: The converted Python object (str, list, set, dict, or None).
    """
    return value_to_python(value)


def extract_value_by_type(value):
    """
    Extract a value from a Value object based on its type, handling both Value objects and regular Python objects.

    Args:
        value: Either a Value object or a regular Python object.

    Returns:
        object: The extracted value in the appropriate Python type.

    Raises:
        ValueError: If the value type is not supported.
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
    Sends a request to the C++ layer and blocks until the response is ready.
    Args:
        session_id (int): The session ID.
        operation (str or Operation): The operation to perform (string or enum).
        key (int/str): The key for the operation.
        new_val (object): The new value for the operation.
        old_val (object): The old value for the operation.
    Returns:
        tuple: A tuple containing the success status and the result value.
    Raises:
        RuntimeError: If AsyncSendRequest fails.
    """
    # T1: Entry to send_request_and_await()
    t1 = _ns_timestamp()
    _log_timing("PY_SEND_AND_AWAIT_ENTRY", t1, session_id=session_id,
                context=f"op={operation},key={key}")

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

    # T2: Before async_send_request() call
    t2 = _ns_timestamp()
    _log_timing("PY_BEFORE_ASYNC_SEND", t2, session_id=session_id,
                context=f"op={operation_enum}")

    success, command_id = async_send_request(
        session_id, operation_enum, key_int, new_val, old_val
    )

    # T3: After async_send_request() returns
    t3 = _ns_timestamp()

    if not success:
        raise RuntimeError("AsyncSendRequest failed")
    if hasattr(command_id, "type") and command_id.type == ValueType.STRING:
        try:
            command_id = int(command_id.str)
        except ValueError:
            raise RuntimeError("Invalid Value object returned by async_send_request")
    try:
        command_id = int(command_id)
    except ValueError:
        raise RuntimeError("Invalid command_id returned by async_send_request")

    _log_timing("PY_AFTER_ASYNC_SEND", t3, command_id=command_id, session_id=session_id,
                context=f"ffi_duration_ns={t3-t2}")

    # T4: Before async_get_response() call
    t4 = _ns_timestamp()
    _log_timing("PY_BEFORE_FIRST_GET_RESPONSE", t4, command_id=command_id, session_id=session_id)

    success, resp = async_get_response(session_id, command_id)

    # T5: After async_get_response() returns
    t5 = _ns_timestamp()
    _log_timing("PY_AFTER_FIRST_GET_RESPONSE", t5, command_id=command_id, session_id=session_id,
                context=f"success={success},get_response_duration_ns={t5-t4}")

    # Response is ready
    if success:
        # T12: Exit from send_request_and_await() (fast path)
        t12 = _ns_timestamp()
        _log_timing("PY_SEND_AND_AWAIT_EXIT_FAST", t12, command_id=command_id, session_id=session_id,
                    context=f"total_duration_ns={t12-t1}")
        return success, extract_value_by_type(resp)

    # Response is not ready yet -> resp.str contains efd as a string
    try:
        efd = int(resp.str)
        print(f"Waiting on efd {efd} for command {command_id}")
    except ValueError:
        raise RuntimeError(f"Expected efd string, got {resp}")

    # Wait for fd
    import select, os, fcntl

    timeout = 20

    try:
        fcntl.fcntl(efd, fcntl.F_GETFD)  # validate fd
    except OSError as e:
        raise RuntimeError(f"EFD {efd} is invalid: {e}")

    # T6: Before select.select()
    t6 = _ns_timestamp()
    _log_timing("PY_BEFORE_SELECT", t6, command_id=command_id, session_id=session_id,
                context=f"efd={efd}")

    r, _, _ = select.select([efd], [], [], timeout)

    # T7: After select.select() returns
    t7 = _ns_timestamp()
    _log_timing("PY_AFTER_SELECT", t7, command_id=command_id, session_id=session_id,
                context=f"select_duration_ns={t7-t6},efd={efd}")

    if not r:
        os.close(efd)
        raise TimeoutError(f"Timeout waiting for command {command_id}")

    # T8: Before os.read(efd)
    t8 = _ns_timestamp()
    _log_timing("PY_BEFORE_EFD_READ", t8, command_id=command_id, session_id=session_id)

    try:
        os.read(efd, 8)
    finally:
        os.close(efd)

    # T9: After os.read(efd)
    t9 = _ns_timestamp()
    _log_timing("PY_AFTER_EFD_READ", t9, command_id=command_id, session_id=session_id,
                context=f"read_duration_ns={t9-t8}")

    # T10: Before second async_get_response()
    t10 = _ns_timestamp()
    _log_timing("PY_BEFORE_SECOND_GET_RESPONSE", t10, command_id=command_id, session_id=session_id)

    # After unblocking, fetch the actual result
    success, result = async_get_response(session_id, command_id)

    # T11: After second async_get_response()
    t11 = _ns_timestamp()
    _log_timing("PY_AFTER_SECOND_GET_RESPONSE", t11, command_id=command_id, session_id=session_id,
                context=f"success={success},get_response_duration_ns={t11-t10}")

    # T12: Exit from send_request_and_await() (slow path)
    t12 = _ns_timestamp()
    _log_timing("PY_SEND_AND_AWAIT_EXIT_SLOW", t12, command_id=command_id, session_id=session_id,
                context=f"total_duration_ns={t12-t1},select_path_overhead_ns={t12-t1-(t7-t6)}")

    if success:
        return success, extract_value_by_type(result)
    else:
        raise RuntimeError(
            f"Failed to retrieve result after unblocking for command {command_id}"
        )


def send_request(session_id, operation, key, new_val="", old_val=""):
    """
    Sends a request to the C++ layer and returns the command ID immediately (non-blocking).
    Args:
        session_id (int): The session ID.
        operation (str or Operation): The operation to perform (string or enum).
        key (int/str): The key for the operation.
        new_val (object): The new value for the operation.
        old_val (object): The old value for the operation.
    Returns:
        int: The command ID to use with await_request().
    """
    # S1: Entry to send_request()
    s1 = _ns_timestamp()
    _log_timing("PY_SEND_REQUEST_ENTRY", s1, session_id=session_id,
                context=f"op={operation},key={key}")

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

    # S2: Before async_send_request()
    s2 = _ns_timestamp()
    _log_timing("PY_SEND_REQUEST_BEFORE_ASYNC_SEND", s2, session_id=session_id,
                context=f"op={operation_enum}")

    success, command_id = async_send_request(
        session_id, operation_enum, key_int, new_val, old_val
    )

    # S3: After async_send_request()
    s3 = _ns_timestamp()

    if not success:
        raise RuntimeError("AsyncSendRequest failed")
    if hasattr(command_id, "type") and command_id.type == ValueType.STRING:
        try:
            command_id = int(command_id.str)
        except ValueError:
            raise RuntimeError("Invalid Value object returned by async_send_request")
    try:
        command_id = int(command_id)
    except ValueError:
        raise RuntimeError("Invalid command_id returned by async_send_request")

    _log_timing("PY_SEND_REQUEST_AFTER_ASYNC_SEND", s3, command_id=command_id, session_id=session_id,
                context=f"ffi_duration_ns={s3-s2}")

    # S4: Exit from send_request()
    s4 = _ns_timestamp()
    _log_timing("PY_SEND_REQUEST_EXIT", s4, command_id=command_id, session_id=session_id,
                context=f"total_duration_ns={s4-s1}")

    return command_id


def await_request(session_id, command_id, timeout=20):
    """
    Awaits the result of a previously sent async request.
    Args:
        session_id (int): The session ID.
        command_id (int): The command ID returned by send_request().
        timeout (int): Timeout in seconds for select().
    Returns:
        tuple: (success, result_value)
    """
    # A1: Entry to await_request()
    a1 = _ns_timestamp()
    _log_timing("PY_AWAIT_REQUEST_ENTRY", a1, command_id=command_id, session_id=session_id)

    # A2: Before async_get_response()
    a2 = _ns_timestamp()
    _log_timing("PY_AWAIT_REQUEST_BEFORE_GET_RESPONSE", a2, command_id=command_id, session_id=session_id)

    success, resp = async_get_response(session_id, command_id)

    # A3: After async_get_response()
    a3 = _ns_timestamp()
    _log_timing("PY_AWAIT_REQUEST_AFTER_GET_RESPONSE", a3, command_id=command_id, session_id=session_id,
                context=f"success={success},get_response_duration_ns={a3-a2}")

    # Response is ready
    if success:
        # A10: Exit (fast path - response already available)
        a10 = _ns_timestamp()
        _log_timing("PY_AWAIT_REQUEST_EXIT_FAST", a10, command_id=command_id, session_id=session_id,
                    context=f"total_duration_ns={a10-a1}")
        return success, extract_value_by_type(resp)

    # Response is not ready yet -> resp.str contains efd as a string
    try:
        efd = int(resp.str)
        print(f"Waiting on efd {efd} for command {command_id}")
    except ValueError:
        raise RuntimeError(f"Expected efd string, got {resp}")

    # Wait for fd
    import select, os, fcntl

    try:
        fcntl.fcntl(efd, fcntl.F_GETFD)  # validate fd
    except OSError as e:
        raise RuntimeError(f"EFD {efd} is invalid: {e}")

    # A4: Before select.select()
    a4 = _ns_timestamp()
    _log_timing("PY_AWAIT_REQUEST_BEFORE_SELECT", a4, command_id=command_id, session_id=session_id,
                context=f"efd={efd}")

    r, _, _ = select.select([efd], [], [], timeout)

    # A5: After select.select()
    a5 = _ns_timestamp()
    _log_timing("PY_AWAIT_REQUEST_AFTER_SELECT", a5, command_id=command_id, session_id=session_id,
                context=f"select_duration_ns={a5-a4},efd={efd}")

    if not r:
        os.close(efd)
        raise TimeoutError(f"Timeout waiting for command {command_id}")

    # A6: Before os.read(efd)
    a6 = _ns_timestamp()
    _log_timing("PY_AWAIT_REQUEST_BEFORE_EFD_READ", a6, command_id=command_id, session_id=session_id)

    try:
        os.read(efd, 8)
    finally:
        os.close(efd)

    # A7: After os.read(efd)
    a7 = _ns_timestamp()
    _log_timing("PY_AWAIT_REQUEST_AFTER_EFD_READ", a7, command_id=command_id, session_id=session_id,
                context=f"read_duration_ns={a7-a6}")

    # A8: Before second async_get_response()
    a8 = _ns_timestamp()
    _log_timing("PY_AWAIT_REQUEST_BEFORE_SECOND_GET_RESPONSE", a8, command_id=command_id, session_id=session_id)

    # After unblocking, fetch the actual result
    success, result = async_get_response(session_id, command_id)

    # A9: After second async_get_response()
    a9 = _ns_timestamp()
    _log_timing("PY_AWAIT_REQUEST_AFTER_SECOND_GET_RESPONSE", a9, command_id=command_id, session_id=session_id,
                context=f"success={success},get_response_duration_ns={a9-a8}")

    # A10: Exit (slow path - had to wait on EFD)
    a10 = _ns_timestamp()
    _log_timing("PY_AWAIT_REQUEST_EXIT_SLOW", a10, command_id=command_id, session_id=session_id,
                context=f"total_duration_ns={a10-a1},select_path_overhead_ns={a10-a1-(a5-a4)}")

    if success:
        return success, extract_value_by_type(result)
    else:
        raise RuntimeError(
            f"Failed to retrieve result after unblocking for command {command_id}"
        )
