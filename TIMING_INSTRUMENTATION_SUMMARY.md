# Fine-Grained Timing Instrumentation Summary

## Overview

This document summarizes the fine-grained timing instrumentation implemented to understand where latency comes from in the Python-C++ async operation flow.

## Completed Phases

### ✅ Phase 1: Dummy Functions (Baseline Measurements)

**Location:** `/Users/austinli/College/researchIOCL/IOCL/src/iocl_python/binding.cc`

**Purpose:** Measure baseline Python-C++ communication overhead

**Functions Implemented:**

1. **`DummyFn()`**
   - Returns 42 immediately at C++ side
   - **Measures:** Pure Python→C++ FFI overhead (no syscalls, no I/O)
   - **Expected latency:** Microseconds

2. **`DummyEFDFn1()`**
   - Creates eventfd and returns it immediately
   - **Measures:** FFI + `eventfd()` syscall overhead
   - **Expected latency:** Low microseconds (FFI + syscall)

3. **`DummyEFDFn2(efd)`**
   - Spawns thread that sleeps 5s, then writes to EFD
   - **Measures:** `select()` granularity and responsiveness
   - **Expected behavior:** Should unblock ~5 seconds after call
   - **Includes:** C++ side timing for sleep accuracy and write latency

**Test Script:** `/Users/austinli/College/researchIOCL/IOCL/test_dummy_timing.py`

**Build Script:** `/Users/austinli/College/researchIOCL/IOCL/rebuild_python_module.sh`

---

### ✅ Phase 2: Python-Side Timing Instrumentation

**Location:** `/Users/austinli/College/researchIOCL/redis-chat-transformed/iocl/iocl_utils.py`

**Purpose:** Track timestamps at key points in the async request flow on Python side

**Controlled by Environment Variable:**
```bash
export IOCL_ENABLE_TIMING=1  # Enable timing (default: disabled)
```

**Output Format:**
```
TIMING,<location>,<timestamp_ns>,<client_id>,<command_id>,<session_id>,<context>
```

All timing logs are written to **STDERR** to avoid mixing with workload output.

#### Instrumented Functions

##### 1. `send_request_and_await()` - Synchronous blocking call

| Point | Label | Description |
|-------|-------|-------------|
| T1 | `PY_SEND_AND_AWAIT_ENTRY` | Function entry |
| T2 | `PY_BEFORE_ASYNC_SEND` | Before FFI call to C++ |
| T3 | `PY_AFTER_ASYNC_SEND` | After FFI returns with command_id |
| T4 | `PY_BEFORE_FIRST_GET_RESPONSE` | Before checking if response ready |
| T5 | `PY_AFTER_FIRST_GET_RESPONSE` | After first check |
| T6 | `PY_BEFORE_SELECT` | About to block on select() (if not ready) |
| T7 | `PY_AFTER_SELECT` | select() returned (unblocked) |
| T8 | `PY_BEFORE_EFD_READ` | About to read from eventfd |
| T9 | `PY_AFTER_EFD_READ` | Read complete, efd closed |
| T10 | `PY_BEFORE_SECOND_GET_RESPONSE` | Fetch actual result |
| T11 | `PY_AFTER_SECOND_GET_RESPONSE` | Result retrieved |
| T12 | `PY_SEND_AND_AWAIT_EXIT_FAST/SLOW` | Function exit |

**Two paths:**
- **Fast path:** T1 → T2 → T3 → T4 → T5 → T12 (response already ready)
- **Slow path:** T1 → T2 → ... → T11 → T12 (had to wait on select)

##### 2. `send_request()` - Non-blocking async send

| Point | Label | Description |
|-------|-------|-------------|
| S1 | `PY_SEND_REQUEST_ENTRY` | Function entry |
| S2 | `PY_SEND_REQUEST_BEFORE_ASYNC_SEND` | Before FFI |
| S3 | `PY_SEND_REQUEST_AFTER_ASYNC_SEND` | After FFI |
| S4 | `PY_SEND_REQUEST_EXIT` | Return with command_id |

##### 3. `await_request()` - Wait for async result

| Point | Label | Description |
|-------|-------|-------------|
| A1 | `PY_AWAIT_REQUEST_ENTRY` | Function entry |
| A2 | `PY_AWAIT_REQUEST_BEFORE_GET_RESPONSE` | Before checking |
| A3 | `PY_AWAIT_REQUEST_AFTER_GET_RESPONSE` | After check |
| A4 | `PY_AWAIT_REQUEST_BEFORE_SELECT` | About to block (if not ready) |
| A5 | `PY_AWAIT_REQUEST_AFTER_SELECT` | select() returned |
| A6 | `PY_AWAIT_REQUEST_BEFORE_EFD_READ` | Before read |
| A7 | `PY_AWAIT_REQUEST_AFTER_EFD_READ` | After read |
| A8 | `PY_AWAIT_REQUEST_BEFORE_SECOND_GET_RESPONSE` | Fetch result |
| A9 | `PY_AWAIT_REQUEST_AFTER_SECOND_GET_RESPONSE` | Result retrieved |
| A10 | `PY_AWAIT_REQUEST_EXIT_FAST/SLOW` | Function exit |

**Two paths:**
- **Fast path:** A1 → A2 → A3 → A10 (response already ready)
- **Slow path:** A1 → A2 → ... → A9 → A10 (had to wait)

---

## Key Metrics You Can Calculate

### 1. Python-C++ FFI Overhead
```
Send FFI:  T3 - T2  (or S3 - S2)
Get FFI:   T5 - T4  (or A3 - A2)
```

### 2. select() Blocking Time
```
Actual wait: T7 - T6  (or A5 - A4)
```

### 3. EFD Operations
```
Read latency:  T9 - T8  (or A7 - A6)
```

### 4. Total Operation Latency

**Synchronous (send_request_and_await):**
```
Fast path:  T12 - T1
Slow path:  T12 - T1
  Breakdown:
    - FFI overhead:         (T3-T2) + (T5-T4) + (T11-T10)
    - Actual wait:          (T7-T6)
    - EFD read:            (T9-T8)
    - Python overhead:      Total - (FFI + wait + EFD)
```

**Asynchronous (send_request + await_request):**
```
Send:   S4 - S1
Await:  A10 - A1
Total:  (S4-S1) + (A10-A1)
```

### 5. Python Overhead (Non-I/O)
```
= Total latency - (FFI calls + select wait + EFD read)
```

This tells you how much time is spent in pure Python code (arg parsing, type conversion, etc.)

---

## Usage Instructions

### Running with Timing Enabled

#### For Sync Mode:
```bash
cd /Users/austinli/College/researchIOCL/redis-chat-transformed/sync
export IOCL_ENABLE_TIMING=1
python main.py --config config.json --explen 30 2> timing_output.log
```

#### For Async Mode:
```bash
cd /Users/austinli/College/researchIOCL/redis-chat-transformed/async
export IOCL_ENABLE_TIMING=1
python main.py --config config.json --explen 30 2> timing_output.log
```

### Analyzing Timing Output

#### Extract all timing data:
```bash
grep '^TIMING,' timing_output.log > timing_data.csv
```

#### Sort by command_id and timestamp:
```bash
grep '^TIMING,' timing_output.log | sort -t',' -k4,4 -k2,2
```

#### Get statistics for a specific command:
```bash
grep '^TIMING,.*,42,' timing_output.log  # command_id = 42
```

#### Calculate average FFI latency:
```bash
grep 'ffi_duration_ns=' timing_output.log | \
  awk -F'ffi_duration_ns=' '{print $2}' | \
  awk -F',' '{print $1}' | \
  awk '{sum+=$1; n++} END {print "Average FFI: " sum/n " ns"}'
```

#### Calculate average select() duration:
```bash
grep 'select_duration_ns=' timing_output.log | \
  awk -F'select_duration_ns=' '{print $2}' | \
  awk -F',' '{print $1}' | \
  awk '{sum+=$1; n++} END {print "Average select: " sum/n " ns (" sum/n/1000000 " ms)"}'
```

---

## Sample Output

```
TIMING,PY_SEND_AND_AWAIT_ENTRY,1234567890000,0,42,1,op=PUT,key=user:123
TIMING,PY_BEFORE_ASYNC_SEND,1234567890100,0,-,1,op=Operation.PUT
TIMING,PY_AFTER_ASYNC_SEND,1234567890500,0,42,1,ffi_duration_ns=400
TIMING,PY_BEFORE_FIRST_GET_RESPONSE,1234567890550,0,42,1,
TIMING,PY_AFTER_FIRST_GET_RESPONSE,1234567890600,0,42,1,success=False,get_response_duration_ns=50
TIMING,PY_BEFORE_SELECT,1234567890700,0,42,1,efd=5
TIMING,PY_AFTER_SELECT,1234567895700,0,42,1,select_duration_ns=5000000,efd=5
TIMING,PY_BEFORE_EFD_READ,1234567895750,0,42,1,
TIMING,PY_AFTER_EFD_READ,1234567895800,0,42,1,read_duration_ns=50
TIMING,PY_BEFORE_SECOND_GET_RESPONSE,1234567895850,0,42,1,
TIMING,PY_AFTER_SECOND_GET_RESPONSE,1234567895900,0,42,1,success=True,get_response_duration_ns=50
TIMING,PY_SEND_AND_AWAIT_EXIT_SLOW,1234567896000,0,42,1,total_duration_ns=6000000,select_path_overhead_ns=1000000
```

**Interpretation:**
- FFI latency: 400 ns
- select() wait: 5,000,000 ns (5 ms) - **actual operation time**
- EFD read: 50 ns
- Total: 6,000,000 ns (6 ms)
- Python overhead: 6ms - 5ms = 1ms (includes FFI, EFD, and Python code)

---

## Next Steps: Phase 3 (C++ Instrumentation)

To complete the picture, Phase 3 would add timing at the C++ layer:

### binding.cc Instrumentation Points

**AsyncSendRequest():**
- B1: Entry
- B2: Before `benchmarkClient->SendAsynchOperation()`
- B3: After `SendAsynchOperation()` returns
- B4: Exit

**AsyncGetResponse():**
- G1: Entry
- G2: Before `benchmarkClient->AwaitAsynchResponse()`
- G3: After `AwaitAsynchResponse()` returns
- G4-G9: EFD path handling

### bench_client.cc Instrumentation Points

**SendAsynchOperation():**
- C1: Entry
- C2: Before `client.SendAsynchOperation()`
- C3: After `client.SendAsynchOperation()`
- C4: Exit with commandId

**AwaitAsynchResponse():**
- W1: Entry
- W2-W6: Check replies_map, create EFD if needed

**AsynchOperationCallback():**
- CB1: Entry (when response arrives)
- CB2: Store in replies_map
- CB3-CB4: Write to EFD

---

## Questions This Instrumentation Answers

1. ✅ **How much overhead is "Python stuff"?**
   - Calculate: `(Total latency) - (select wait time)`

2. ✅ **Is select() blocking longer than it should?**
   - Compare: `(T7-T6)` vs expected operation latency

3. ✅ **What's the latency of Python→C++ FFI calls?**
   - Measure: `(T3-T2)`, `(T5-T4)`, etc.

4. ✅ **Where are the major bottlenecks?**
   - Compare all timing intervals to identify slowest parts

5. ✅ **Is eventfd creation/signaling adding overhead?**
   - Phase 1 dummy functions establish baseline
   - Measure: `(T9-T8)` for read overhead

---

## Files Modified/Created

### Modified:
- `/Users/austinli/College/researchIOCL/IOCL/src/iocl_python/binding.cc`
  - Added dummy functions with timing

- `/Users/austinli/College/researchIOCL/redis-chat-transformed/iocl/iocl_utils.py`
  - Added comprehensive Python timing instrumentation

### Created:
- `/Users/austinli/College/researchIOCL/IOCL/test_dummy_timing.py`
  - Test script for Phase 1 dummy functions

- `/Users/austinli/College/researchIOCL/IOCL/test_phase2_timing.py`
  - Documentation and examples for Phase 2

- `/Users/austinli/College/researchIOCL/IOCL/rebuild_python_module.sh`
  - Build script for C++ module

- `/Users/austinli/College/researchIOCL/IOCL/TIMING_INSTRUMENTATION_SUMMARY.md`
  - This comprehensive documentation

---

## Ready to Use!

The Python-side instrumentation is **ready to use immediately** - no rebuild required!

Just set `IOCL_ENABLE_TIMING=1` and run your workload. The C++ dummy functions (Phase 1) require rebuilding the module first.
