import redisstore as rs
import hashlib
import struct

def string_to_int64_hash(s):
    hash_value = int(hashlib.sha256(s.encode()).hexdigest(), 16)  # Large int from SHA-256
    int64_hash = (hash_value % (2**64)) - 2**63  # Map to signed int64 range
    return int64_hash


def AppRequest(op_type, key, value=None, old_value=None):
    """
    Perform an operation on a key with optional value and old_value.

    :param op_type: Operation type (e.g., 'PUT', 'GET', 'INCR', 'SET', etc.)
    :param key: Key for the operation (string or integer)
    :param value: Value for the operation (optional)
    :param old_value: Old value for comparison operations (optional)
    :return: Tuple of (success, result)
    """
    # Convert string operation type to enum
    if isinstance(op_type, str):
        try:
            op = getattr(rs.Operation, op_type.upper())
        except AttributeError:
            raise ValueError(f"Unknown operation: {op_type}")
    else:
        op = op_type

    # Convert key to int64 if it's a string that can be converted to an integer
    if isinstance(key, str) and key.isdigit():
        key = int(key)
    elif isinstance(key, str):
        key = string_to_int64_hash(key)
    

    # Call the underlying C++ function
    success, result = rs.send_request(op, key, value, old_value)

    if not success:
        raise Exception("Failed to perform operation")

    return result

