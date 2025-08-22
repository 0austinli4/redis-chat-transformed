#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/functional.h>
#include "redis_store.h" // Your header file

namespace py = pybind11;

// Helper function to convert Python objects to Value
Value python_to_value(const py::object& obj) {
    if (py::isinstance<py::str>(obj)) {
        return Value::NewString(obj.cast<std::string>());
    }
    else if (py::isinstance<py::list>(obj)) {
        return Value::NewList(obj.cast<std::vector<std::string>>());
    }
    else if (py::isinstance<py::set>(obj)) {
        return Value::NewSet(obj.cast<std::unordered_set<std::string>>());
    }
    else if (py::isinstance<py::dict>(obj)) {
        return Value::NewHash(obj.cast<std::unordered_map<std::string, std::string>>());
    }
    return NIL;
}

// Global RedisStore instance
static RedisStore globalRedisStore;

// SendRequest
std::pair<bool, Value> SendRequest(Operation op, int64_t keys, const Value& newVal, const Value& oldVal) {
    // Create a Command object to pass to RedisStore::execute
    Command cmd;
    cmd.op = op;
    cmd.key = std::to_string(keys);
    cmd.value = newVal;
    cmd.oldValue = oldVal;
    
    try {
        // Execute the command using the global RedisStore instance
        Value result = globalRedisStore.execute(cmd);
        return {true, result};
    } catch (const std::exception& e) {
        std::cerr << "Error in SendRequest: " << e.what() << std::endl;
        return {false, NIL};
    }
}

// Helper function to convert Value to Python objects
py::object value_to_python(const Value& val) {
    switch (val.type) {
        case ValueType::STRING:
            return py::cast(val.str);
        case ValueType::LIST:
            return py::cast(val.list);
        case ValueType::SET:
            return py::cast(val.set);
        case ValueType::HASH:
            return py::cast(val.hash);
        default:
            return py::none();
    }
}

// Create the Python module
PYBIND11_MODULE(redisstore, m) {
    // Define the Operation enum
    py::enum_<Operation>(m, "Operation")
        .value("PUT", Operation::PUT)
        .value("GET", Operation::GET)
        .value("INCR", Operation::INCR)
        .value("SET", Operation::SET)
        .value("SADD", Operation::SADD)
        .value("EXISTS", Operation::EXISTS)
        .value("HMGET", Operation::HMGET)
        .value("HSET", Operation::HSET)
        .value("HMSET", Operation::HMSET)
        .value("HGETALL", Operation::HGETALL)
        .value("ZADD", Operation::ZADD)
        .value("ZINCRBY", Operation::ZINCRBY)
        .value("ZSCORE", Operation::ZSCORE)
        .value("ZREVRANGE", Operation::ZREVRANGE);

    // Define the ValueType enum
    py::enum_<ValueType>(m, "ValueType")
        .value("STRING", ValueType::STRING)
        .value("LIST", ValueType::LIST)
        .value("SET", ValueType::SET)
        .value("HASH", ValueType::HASH);
    
    // Define the Value class
    py::class_<Value>(m, "Value")
        .def(py::init<>())
        .def(py::init<const std::string&>())
        .def(py::init<const std::vector<std::string>&>())
        .def(py::init<const std::unordered_set<std::string>&>())
        .def(py::init<const std::unordered_map<std::string, std::string>&>())
        .def_readwrite("type", &Value::type)
        .def_readwrite("str", &Value::str)
        .def_readwrite("list", &Value::list)
        .def_readwrite("set", &Value::set)
        .def_readwrite("hash", &Value::hash)
        .def_static("NewString", &Value::NewString)
        .def_static("NewList", &Value::NewList)
        .def_static("NewSet", &Value::NewSet)
        .def_static("NewHash", &Value::NewHash)
        .def("is_nil", &Value::isNil);

    // Define the Command struct
    py::class_<Command>(m, "Command")
        .def(py::init<>())
        .def_readwrite("op", &Command::op)
        .def_readwrite("key", &Command::key)
        .def_readwrite("value", &Command::value)
        .def_readwrite("oldValue", &Command::oldValue);

    // Define the RedisStore class
    py::class_<RedisStore>(m, "RedisStore")
        .def(py::init<>())
        .def("execute", &RedisStore::execute)
        .def("__del__", [](RedisStore& self) { self.~RedisStore(); });

    // Wrapper for SendRequest to handle Python types
    m.def("send_request", [](Operation op, int64_t keys, py::object new_values, py::object old_values) {
        Value newVal = python_to_value(new_values);
        Value oldVal = python_to_value(old_values);
        
        bool success;
        Value result;
        std::tie(success, result) = SendRequest(op, keys, newVal, oldVal);
        
        return py::make_tuple(success, value_to_python(result));
    }, py::arg("op"), py::arg("keys"), py::arg("new_values"), py::arg("old_values") = py::none());
}