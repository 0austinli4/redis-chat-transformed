#!/usr/bin/env python3
"""
Test script for measuring Python-C++ communication overhead using dummy functions.

This script tests:
1. DummyFn - Pure FFI overhead without any I/O
2. DummyEFDFn1 - EFD creation overhead + FFI
3. DummyEFDFn2 - select() granularity and responsiveness
"""

import time
import select
import os
import sys

# Add the path where redisstore module is located
sys.path.insert(0, '/Users/austinli/College/researchIOCL/IOCL/src/iocl_python')

try:
    from redisstore import dummy_fn, dummy_efd_fn1, dummy_efd_fn2
    print("✓ Successfully imported dummy functions from redisstore")
except ImportError as e:
    print(f"✗ Failed to import dummy functions: {e}")
    print("\nPlease rebuild the redisstore module first:")
    print("  cd /Users/austinli/College/researchIOCL/IOCL/src/iocl_python")
    print("  make clean && make")
    sys.exit(1)


def ns_timestamp():
    """Get current timestamp in nanoseconds"""
    # Python 3.7+ has clock_gettime_ns, older versions need conversion
    if hasattr(time, 'clock_gettime_ns'):
        return time.clock_gettime_ns(time.CLOCK_MONOTONIC)
    else:
        # Fallback for Python 3.6 and earlier
        t = time.clock_gettime(time.CLOCK_MONOTONIC)
        return int(t * 1e9)


def test_dummy_fn(iterations=1000):
    """
    Test DummyFn: Measures pure Python-C++ FFI overhead

    Expected: Very low latency (microseconds)
    This is the baseline for FFI calls with no actual work
    """
    print("\n" + "="*70)
    print(f"TEST 1: DummyFn (Pure FFI Overhead) - {iterations} iterations")
    print("="*70)

    latencies = []

    # Warmup
    for _ in range(100):
        dummy_fn()

    # Actual measurement
    for i in range(iterations):
        t1 = ns_timestamp()
        result = dummy_fn()
        t2 = ns_timestamp()

        latency_ns = t2 - t1
        latencies.append(latency_ns)

        if i < 5:  # Print first 5 for debugging
            print(f"  Call {i+1}: {latency_ns} ns ({latency_ns/1000:.2f} μs)")

    # Statistics
    latencies.sort()
    avg = sum(latencies) / len(latencies)
    median = latencies[len(latencies) // 2]
    p95 = latencies[int(len(latencies) * 0.95)]
    p99 = latencies[int(len(latencies) * 0.99)]

    print(f"\nResults (n={iterations}):")
    print(f"  Average:  {avg:.2f} ns ({avg/1000:.2f} μs)")
    print(f"  Median:   {median} ns ({median/1000:.2f} μs)")
    print(f"  95th %:   {p95} ns ({p95/1000:.2f} μs)")
    print(f"  99th %:   {p99} ns ({p99/1000:.2f} μs)")
    print(f"  Min:      {latencies[0]} ns ({latencies[0]/1000:.2f} μs)")
    print(f"  Max:      {latencies[-1]} ns ({latencies[-1]/1000:.2f} μs)")

    return latencies


def test_dummy_efd_fn1(iterations=1000):
    """
    Test DummyEFDFn1: Measures EFD creation overhead + FFI

    Expected: Low latency but higher than DummyFn (includes syscall overhead)
    """
    print("\n" + "="*70)
    print(f"TEST 2: DummyEFDFn1 (EFD Creation + FFI) - {iterations} iterations")
    print("="*70)

    latencies = []
    efds_to_close = []

    # Actual measurement
    for i in range(iterations):
        t1 = ns_timestamp()
        efd = dummy_efd_fn1()
        t2 = ns_timestamp()

        if efd < 0:
            print(f"  ERROR: Call {i+1} failed to create EFD")
            continue

        latency_ns = t2 - t1
        latencies.append(latency_ns)
        efds_to_close.append(efd)

        if i < 5:  # Print first 5 for debugging
            print(f"  Call {i+1}: efd={efd}, latency={latency_ns} ns ({latency_ns/1000:.2f} μs)")

    # Close all EFDs
    for efd in efds_to_close:
        try:
            os.close(efd)
        except:
            pass

    # Statistics
    if not latencies:
        print("  ERROR: No successful measurements")
        return []

    latencies.sort()
    avg = sum(latencies) / len(latencies)
    median = latencies[len(latencies) // 2]
    p95 = latencies[int(len(latencies) * 0.95)]
    p99 = latencies[int(len(latencies) * 0.99)]

    print(f"\nResults (n={len(latencies)}):")
    print(f"  Average:  {avg:.2f} ns ({avg/1000:.2f} μs)")
    print(f"  Median:   {median} ns ({median/1000:.2f} μs)")
    print(f"  95th %:   {p95} ns ({p95/1000:.2f} μs)")
    print(f"  99th %:   {p99} ns ({p99/1000:.2f} μs)")
    print(f"  Min:      {latencies[0]} ns ({latencies[0]/1000:.2f} μs)")
    print(f"  Max:      {latencies[-1]} ns ({latencies[-1]/1000:.2f} μs)")

    return latencies


def test_dummy_efd_fn2():
    """
    Test DummyEFDFn2: Measures select() granularity and responsiveness

    Expected: Should unblock ~5 seconds after call, measuring select() accuracy
    """
    print("\n" + "="*70)
    print("TEST 3: DummyEFDFn2 (select() Granularity)")
    print("="*70)

    # Create an EFD
    print("\nStep 1: Creating EFD...")
    t_create_start = ns_timestamp()
    efd = dummy_efd_fn1()
    t_create_end = ns_timestamp()

    if efd < 0:
        print("  ERROR: Failed to create EFD")
        return None

    print(f"  ✓ Created efd={efd} in {(t_create_end - t_create_start)/1000:.2f} μs")

    # Call DummyEFDFn2 to spawn thread
    print("\nStep 2: Calling DummyEFDFn2 (spawns thread that sleeps 5s)...")
    t_call_start = ns_timestamp()
    success = dummy_efd_fn2(efd)
    t_call_end = ns_timestamp()

    if not success:
        print("  ERROR: DummyEFDFn2 failed")
        os.close(efd)
        return None

    print(f"  ✓ DummyEFDFn2 returned in {(t_call_end - t_call_start)/1000:.2f} μs")
    print(f"  ✓ Thread spawned successfully")

    # Wait on the EFD using select()
    print("\nStep 3: Waiting on EFD with select() (expecting ~5s)...")
    t_select_start = ns_timestamp()

    timeout = 10  # 10 second timeout
    r, _, _ = select.select([efd], [], [], timeout)

    t_select_end = ns_timestamp()

    if not r:
        print(f"  ERROR: select() timed out after {timeout} seconds")
        os.close(efd)
        return None

    select_duration_ns = t_select_end - t_select_start
    select_duration_s = select_duration_ns / 1e9

    print(f"  ✓ select() unblocked after {select_duration_s:.6f} seconds")
    print(f"    = {select_duration_ns} ns")
    print(f"    Expected: ~5.000000 seconds")
    print(f"    Difference: {abs(select_duration_s - 5.0)*1000:.3f} ms")

    # Read from EFD
    print("\nStep 4: Reading from EFD...")
    t_read_start = ns_timestamp()

    try:
        data = os.read(efd, 8)
        t_read_end = ns_timestamp()

        val = int.from_bytes(data, 'little')
        read_duration_ns = t_read_end - t_read_start

        print(f"  ✓ Read value: {val}")
        print(f"  ✓ Read took {read_duration_ns} ns ({read_duration_ns/1000:.2f} μs)")
    except Exception as e:
        print(f"  ERROR: Failed to read from EFD: {e}")
    finally:
        os.close(efd)

    # Total end-to-end
    total_duration_ns = t_read_end - t_create_start
    total_duration_s = total_duration_ns / 1e9

    print(f"\nTotal end-to-end: {total_duration_s:.6f} seconds")
    print(f"  = {total_duration_ns} ns")

    # Breakdown
    print("\nBreakdown:")
    print(f"  EFD creation:         {(t_create_end - t_create_start)/1000:>10.2f} μs")
    print(f"  DummyEFDFn2 call:     {(t_call_end - t_call_start)/1000:>10.2f} μs")
    print(f"  select() wait:        {select_duration_s:>10.6f} s")
    print(f"  EFD read:             {(t_read_end - t_read_start)/1000:>10.2f} μs")

    return {
        'total_ns': total_duration_ns,
        'select_ns': select_duration_ns,
        'expected_ns': 5_000_000_000,
        'difference_ns': abs(select_duration_ns - 5_000_000_000)
    }


def main():
    print("="*70)
    print("PHASE 1: Python-C++ Communication Overhead Measurement")
    print("="*70)

    # Test 1: Pure FFI overhead
    dummy_fn_latencies = test_dummy_fn(iterations=1000)

    # Test 2: EFD creation overhead
    dummy_efd_fn1_latencies = test_dummy_efd_fn1(iterations=1000)

    # Test 3: select() granularity
    dummy_efd_fn2_result = test_dummy_efd_fn2()

    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)

    if dummy_fn_latencies:
        avg_ffi = sum(dummy_fn_latencies) / len(dummy_fn_latencies)
        print(f"DummyFn (pure FFI):           {avg_ffi:.2f} ns ({avg_ffi/1000:.2f} μs)")

    if dummy_efd_fn1_latencies:
        avg_efd_create = sum(dummy_efd_fn1_latencies) / len(dummy_efd_fn1_latencies)
        print(f"DummyEFDFn1 (FFI + EFD):      {avg_efd_create:.2f} ns ({avg_efd_create/1000:.2f} μs)")

        if dummy_fn_latencies:
            efd_overhead = avg_efd_create - avg_ffi
            print(f"  → EFD creation overhead:    {efd_overhead:.2f} ns ({efd_overhead/1000:.2f} μs)")

    if dummy_efd_fn2_result:
        diff_ms = dummy_efd_fn2_result['difference_ns'] / 1e6
        print(f"\nDummyEFDFn2 select() accuracy:")
        print(f"  Expected: 5.000000 s")
        print(f"  Actual:   {dummy_efd_fn2_result['select_ns']/1e9:.6f} s")
        print(f"  Error:    {diff_ms:.3f} ms ({diff_ms/5000*100:.3f}% of 5s)")

    print("\n" + "="*70)
    print("What these measurements tell us:")
    print("="*70)
    print("1. DummyFn establishes the baseline Python→C++ FFI cost")
    print("2. DummyEFDFn1 shows the additional cost of eventfd() syscall")
    print("3. DummyEFDFn2 reveals how accurately select() can measure time")
    print("\nUse these baselines when analyzing async operation latency!")
    print("="*70)


if __name__ == "__main__":
    main()
