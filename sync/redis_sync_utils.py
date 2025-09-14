import select
import os
from redisstore import async_send_request, async_get_response, ValueType, Operation


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

    success, command_id = async_send_request(
        session_id, operation_enum, key, new_val, old_val
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
    success, efd_or_result = async_get_response(session_id, command_id)
    if hasattr(efd_or_result, "type") and efd_or_result.type == ValueType.STRING:
        try:
            efd_or_result = int(efd_or_result.str)
        except ValueError:
            raise RuntimeError("Invalid Value object returned by async_get_response")
    if not isinstance(efd_or_result, int) or efd_or_result < 0:
        raise RuntimeError(
            "Invalid event file descriptor returned by async_get_response"
        )
    efd = efd_or_result
    timeout = 20
    r, _, _ = select.select([efd], [], [], timeout)
    if not r:
        raise TimeoutError("AwaitAsynchResponse timed out")
    if r:
        try:
            os.read(efd, 8)
        finally:
            os.close(efd)
        success, result = async_get_response(session_id, command_id)
        if success:
            return success, result
        else:
            raise RuntimeError("Failed to retrieve result after unblocking")
