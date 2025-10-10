import select
import os
import hashlib
from redisstore import (
    async_send_request,
    async_get_response,
    ValueType,
    Operation,
    Value,
    value_to_python,
)
import sys


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

    # print("send request and await", session_id, operation, key, new_val, old_val)
    # print("var types send request and await", type(session_id), type(operation_enum), type(key_int), type(new_val), type(old_val))
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
    try:
        command_id = int(command_id)
    except ValueError:
        raise RuntimeError("Invalid command_id returned by async_send_request")

    success, resp = async_get_response(session_id, command_id)

    # Response is ready
    if success:
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

    r, _, _ = select.select([efd], [], [], timeout)
    if not r:
        os.close(efd)
        raise TimeoutError(f"Timeout waiting for command {command_id}")

    try:
        os.read(efd, 8)
    finally:
        os.close(efd)

    # After unblocking, fetch the actual result
    success, result = async_get_response(session_id, command_id)
    if success:
        return success, extract_value_by_type(result)
    else:
        raise RuntimeError(
            f"Failed to retrieve result after unblocking for command {command_id}"
        )


def send_request(session_id, operation, key, new_val="", old_val=""):
    """
    Sends a request to the C++ layer and blocks until the response is ready.
    Args:
        session_id (int): The session ID.
        operation (str or Operation): The operation to perform (string or enum).
        key (int/str): The key for the operation.
        new_val (object): The new value for the operation.
        old_val (object): The old value for the operation.
    Returns:
        tuple: A tuple containing the success status and the resulting request ID to await.
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

    # print("send request and await", session_id, operation, key, new_val, old_val)
    # print("var types send request and await", type(session_id), type(operation_enum), type(key_int), type(new_val), type(old_val))
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
    try:
        command_id = int(command_id)
    except ValueError:
        raise RuntimeError("Invalid command_id returned by async_send_request")
    return command_id


def await_request(session_id, command_id, timeout=20):
    # print("Awaiting request", command_id)

    success, resp = async_get_response(session_id, command_id)

    # Response is ready
    if success:
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

    r, _, _ = select.select([efd], [], [], timeout)
    if not r:
        os.close(efd)
        raise TimeoutError(f"Timeout waiting for command {command_id}")

    try:
        os.read(efd, 8)
    finally:
        os.close(efd)

    # After unblocking, fetch the actual result
    success, result = async_get_response(session_id, command_id)
    if success:
        return success, extract_value_by_type(result)
    else:
        raise RuntimeError(
            f"Failed to retrieve result after unblocking for command {command_id}"
        )
