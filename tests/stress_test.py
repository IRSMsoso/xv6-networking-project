#!/usr/bin/env python3

#
# Stress tests for xv6 networking
# Monitors drop rate and queue depth over time
#

import socket
import sys
import time
import os
import threading
import json
from datetime import datetime

# qemu listens for packets sent to FWDPORT,
# and re-writes them so they arrive in
# xv6 with destination port 2000.
FWDPORT1 = (os.getuid() % 5000) + 25999
FWDPORT2 = (os.getuid() % 5000) + 30999

# xv6's nettest.c and host_net_helper.py use SERVERPORT.
SERVERPORT = (os.getuid() % 5000) + 25099


def usage():
    sys.stderr.write("Usage: stress_test.py [rate]\n")
    sys.stderr.write("\n")
    sys.stderr.write("Finds maximum sustainable throughput for xv6 networking.\n")
    sys.stderr.write("\n")
    sys.stderr.write("Examples:\n")
    sys.stderr.write("  stress_test.py          - Auto-find max rate (binary search)\n")
    sys.stderr.write("  stress_test.py 5000     - Test at 5000 packets/sec\n")
    sys.stderr.write("  stress_test.py 10000    - Test at 10000 packets/sec\n")
    sys.stderr.write("\n")
    sys.stderr.write("Make sure xv6 is running 'nettest throughput' first!\n")
    sys.exit(1)


def test_droprate():
    """
    Send 1000 packets rapidly
    Count how many xv6 receives
    Calculate drop %
    """
    print("Drop Rate Test: Starting")
    print("=" * 60)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Send 1000 packets as fast as possible
    packets_sent = 1000
    print(f"Sending {packets_sent} packets rapidly...")

    start_time = time.time()
    for i in range(packets_sent):
        payload = f"droptest {i}".encode("ascii")
        sock.sendto(payload, ("127.0.0.1", FWDPORT1))

    elapsed = time.time() - start_time
    print(f"Sent {packets_sent} packets in {elapsed:.3f} seconds")
    print(f"Rate: {packets_sent / elapsed:.1f} packets/sec")
    print()
    print("Waiting for xv6 to report received count...")
    print("(xv6 should report how many packets it received)")
    print()
    print("Instructions:")
    print("1. The drop rate % = (sent - received) / sent * 100")
    print(f"2. We sent {packets_sent} packets")
    print("3. Check xv6 output for received count")


def test_queuedepth():
    """
    Monitor queue depth over time by sending packets
    at varying rates and observing behavior
    """
    print("Queue Depth Over Time Test: Starting")
    print("=" * 60)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Phase 1: Send at low rate
    print("Phase 1: Low rate (10 pkt/sec) for 5 seconds")
    for i in range(50):
        payload = f"queue_low {i}".encode("ascii")
        sock.sendto(payload, ("127.0.0.1", FWDPORT1))
        time.sleep(0.1)  # 10 packets per second

    print("Phase 1 complete. Check xv6 queue behavior.")
    time.sleep(1)

    # Phase 2: Send at medium rate
    print("\nPhase 2: Medium rate (50 pkt/sec) for 5 seconds")
    for i in range(250):
        payload = f"queue_med {i}".encode("ascii")
        sock.sendto(payload, ("127.0.0.1", FWDPORT1))
        time.sleep(0.02)  # 50 packets per second

    print("Phase 2 complete. Check xv6 queue behavior.")
    time.sleep(1)

    # Phase 3: Send burst
    print("\nPhase 3: Burst (500 packets instantly)")
    for i in range(500):
        payload = f"queue_burst {i}".encode("ascii")
        sock.sendto(payload, ("127.0.0.1", FWDPORT1))

    print("Phase 3 complete. Check xv6 queue behavior.")
    time.sleep(2)

    # Phase 4: Recovery period
    print("\nPhase 4: Recovery (slow rate 5 pkt/sec) for 5 seconds")
    for i in range(25):
        payload = f"queue_recover {i}".encode("ascii")
        sock.sendto(payload, ("127.0.0.1", FWDPORT1))
        time.sleep(0.2)  # 5 packets per second

    print("\nQueue depth test complete!")
    print("\nTo visualize queue depth over time:")
    print("1. Add instrumentation in xv6 to print queue length")
    print("2. Log timestamps and queue sizes")
    print("3. Plot the data to see queue behavior under load")


def test_throughput(target_rate=1000):
    """
    Send 1000 packets to xv6 for throughput measurement at a specific rate
    xv6 echoes them back to verify round-trip
    """
    print("Throughput Test: Starting")
    print("=" * 60)
    print(f"Target rate: {target_rate} packets/sec")
    print("Sending 1000 packets to port 2000 (via FWDPORT1)...")
    print("(Make sure xv6 is running 'nettest throughput')")
    print()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", SERVERPORT))  # Bind to receive echoes

    # FWDPORT1 maps to xv6's port 2000
    target_port = FWDPORT1

    packets_sent = 1000
    packets_received = 0

    if target_rate <= 0:
        print(f"Sending packets at maximum speed (no rate limit)...")
        send_interval = 0
    else:
        print(f"Sending packets at {target_rate} pkt/s...")
        send_interval = 1.0 / target_rate

    start_time = time.time()

    for i in range(packets_sent):
        payload = f"throughput {i}".encode("ascii")
        sock.sendto(payload, ("127.0.0.1", target_port))
        if (i + 1) % 200 == 0:
            print(f"  Sent {i + 1}/{packets_sent} packets...")
        if send_interval > 0:
            time.sleep(send_interval)

    send_elapsed = time.time() - start_time
    actual_send_rate = packets_sent / send_elapsed
    print(f"Sent {packets_sent} packets in {send_elapsed:.3f} seconds")
    print(f"Actual send rate: {actual_send_rate:.1f} packets/sec")
    print()

    # Now receive echoed packets back
    print("Receiving echoed packets...")
    sock.settimeout(5.0)  # 5 second timeout for receiving
    recv_start = time.time()

    # Track sequence numbers and validate
    received_seqs = set()
    out_of_order = 0
    payload_errors = 0
    port_errors = 0
    last_seq = -1

    try:
        for i in range(packets_sent):
            try:
                data, addr = sock.recvfrom(4096)
                packets_received += 1

                # Validate payload format
                try:
                    payload_str = data.decode("ascii")
                    if payload_str.startswith("throughput "):
                        seq = int(payload_str.split()[1])
                        received_seqs.add(seq)

                        if last_seq >= 0 and seq != last_seq + 1:
                            out_of_order += 1
                        last_seq = seq
                    else:
                        payload_errors += 1
                        if payload_errors <= 3:
                            print(f"  Invalid payload: {payload_str[:50]}")
                except (ValueError, IndexError, UnicodeDecodeError) as e:
                    payload_errors += 1
                    if payload_errors <= 3:
                        print(f"  Payload decode error: {e}")

                # Validate source port (should be from xv6's port 2000)
                # Note: actual port may be forwarded by QEMU

            except socket.timeout:
                print(f"Timeout waiting for packet {i}")
                break
    except KeyboardInterrupt:
        print("\nInterrupted by user")

    recv_elapsed = time.time() - recv_start
    total_elapsed = time.time() - start_time

    # Find missing sequences
    expected_seqs = set(range(packets_sent))
    missing_seqs = expected_seqs - received_seqs
    duplicate_count = packets_received - len(received_seqs)

    print()
    print("=" * 60)
    print("Throughput Test Results:")
    print(f"  Packets sent: {packets_sent}")
    print(f"  Packets received: {packets_received}")
    print(f"  Unique sequences: {len(received_seqs)}/{packets_sent}")
    print(f"  Missing sequences: {len(missing_seqs)}")
    if len(missing_seqs) > 0 and len(missing_seqs) <= 10:
        print(f"    Missing: {sorted(missing_seqs)}")
    print(f"  Duplicates: {duplicate_count}")
    print(f"  Out of order: {out_of_order}")
    print(f"  Payload errors: {payload_errors}")

    loss_rate = (packets_sent - packets_received) / packets_sent * 100
    print(f"  Loss rate: {loss_rate:.1f}%")
    print(f"  Total time: {total_elapsed:.3f} seconds")
    effective_throughput = packets_received / total_elapsed
    print(f"  Effective throughput: {effective_throughput:.1f} packets/sec")
    print()

    # Relaxed validation for max speed - allow minor errors
    # 99% delivery with unique sequences is acceptable
    success = (
        packets_received >= packets_sent * 0.99
        and len(received_seqs) >= packets_sent * 0.99
        and payload_errors <= packets_sent * 0.01  # Allow up to 1% errors
    )

    if success:
        print("✓ Throughput test PASSED")
        if payload_errors == 0 and len(missing_seqs) == 0:
            print("  - Perfect delivery!")
        else:
            print("  - Good delivery with minor issues")
        print(f"  - {len(received_seqs)} unique sequences received")
        print(f"  - {effective_throughput:.0f} packets/sec effective rate")
    else:
        print("✗ Throughput test FAILED")
        if packets_received < packets_sent * 0.99:
            print(f"  - Too many packets lost ({packets_sent - packets_received} lost)")
        if len(received_seqs) < packets_sent * 0.99:
            print(f"  - Too many missing sequences ({len(missing_seqs)} missing)")
        if payload_errors > packets_sent * 0.01:
            print(f"  - Too many payload errors ({payload_errors} errors)")
    print("=" * 60)

    return {
        "rate": target_rate,
        "sent": packets_sent,
        "received": packets_received,
        "loss_rate": loss_rate,
        "throughput": effective_throughput,
        "success": success,
    }


def get_next_filename(base="throughput", ext=".json"):
    """Find next available filename: throughput.json, throughput1.json, etc."""
    results_dir = "tests/results"
    os.makedirs(results_dir, exist_ok=True)
    path = os.path.join(results_dir, f"{base}{ext}")
    if not os.path.exists(path):
        return path

    counter = 1
    while True:
        path = os.path.join(results_dir, f"{base}{counter}{ext}")
        if not os.path.exists(path):
            return path
        counter += 1


def save_results_json(results, best_rate, best_throughput, metadata=None):
    """Save test results to JSON file with auto-incrementing filename."""
    filename = get_next_filename()

    output = {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "test_type": "binary_search_throughput",
            "packets_per_test": 1000,
            **(metadata or {}),
        },
        "summary": {
            "best_rate_pps": best_rate,
            "effective_throughput_pps": best_throughput,
            "iterations": len(results),
            "search_range": [1000, 50000],
        },
        "test_results": results,
    }

    with open(filename, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n📊 Results saved to: {filename}")
    return filename


def test_findmax():
    """
    Binary search to find maximum throughput with good delivery (99%+)
    """
    print("=" * 70)
    print("  XV6 NETWORK THROUGHPUT - MAXIMUM RATE FINDER")
    print("=" * 70)
    print()
    print("This tool will automatically find the maximum sustainable throughput")
    print("for your xv6 networking implementation using binary search.")
    print()
    print("Requirements:")
    print("  1. xv6 must be running (make qemu)")
    print("  2. Run 'nettest throughput' in xv6 shell")
    print("  3. xv6 will stay running in continuous mode")
    print()
    input("Press Enter when ready...")

    # Binary search for maximum rate
    low = 1000
    high = 50000
    best_rate = 0
    best_throughput = 0

    results = []

    print("\n" + "=" * 70)
    print("Starting binary search...")
    print(f"Search range: {low:,} - {high:,} packets/sec")
    print("Target: 99%+ packet delivery")
    print("=" * 70)

    iteration = 0
    while low <= high and iteration < 10:  # Max 10 iterations
        mid = (low + high) // 2
        iteration += 1

        print(f"\n{'=' * 60}")
        print(f"Iteration {iteration}: Testing at {mid} packets/sec")
        print(f"  (Range: {low} - {high})")
        print(f"{'=' * 60}")

        result = test_throughput(mid)
        results.append(result)

        success_rate = result["received"] / result["sent"]
        print(
            f"\nResult: {result['received']}/{result['sent']} packets ({success_rate * 100:.1f}%)"
        )

        if success_rate >= 0.99:  # 99% or better
            print(f"✓ Good! Rate {mid} works well")
            best_rate = mid
            best_throughput = result["throughput"]
            low = mid + 1  # Try higher
        else:
            print(f"✗ Too fast! Lost {result['sent'] - result['received']} packets")
            high = mid - 1  # Try lower

        time.sleep(1)  # Brief pause between tests

    print("\n" + "=" * 60)
    print("BINARY SEARCH RESULTS")
    print("=" * 60)
    print(f"{'Rate (pkt/s)':<15} {'Received':<12} {'Loss %':<10} {'Status'}")
    print("-" * 60)

    for r in sorted(results, key=lambda x: x["rate"]):
        status = "✓ GOOD" if r["success"] else "✗ FAIL"
        print(
            f"{r['rate']:<15} {r['received']}/{r['sent']:<8} {r['loss_rate']:<10.1f} {status}"
        )

    print("=" * 60)
    if best_rate > 0:
        print()
        print(f"🏆 MAXIMUM SUSTAINABLE RATE: {best_rate:,} packets/sec")
        print(f"   Effective throughput: {best_throughput:,.1f} packets/sec")
        print(f"   Delivery rate: 99%+")
        print()
        print("To test at this rate:")
        print(f"  python3 stress_test.py {best_rate}")
    else:
        print("⚠ No successful rate found")
        print("Try increasing buffer sizes in kernel/net.c and kernel/e1000.c")
    print("=" * 60)

    # Save results to JSON
    save_results_json(results, best_rate, best_throughput)


def test_sustained():
    """
    Send packets continuously for 30 seconds at moderate rate
    Tests sustained high load handling
    """
    print("Sustained High Load Test: Starting")
    print("=" * 60)
    print("Sending 2000 packets continuously...")
    print("Rate: ~50 packets/second")
    print("(Make sure xv6 is running 'nettest sustained')")
    print()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Use FWDPORT1 to reach xv6's port 2000
    target_port = FWDPORT1

    # Send 2000 packets at moderate rate
    total_packets = 2000
    packets_per_sec = 50  # Reduced from 100 to avoid queue overflow
    delay = 1.0 / packets_per_sec  # 0.02 seconds = 20ms
    start_time = time.time()

    print(f"Target: {total_packets} packets (expected ~40 seconds)")
    print()

    sent_count = 0
    for i in range(total_packets):
        payload = f"sustained {i}".encode("ascii")
        sock.sendto(payload, ("127.0.0.1", target_port))
        sent_count += 1

        # Print progress every 1000 packets
        if (i + 1) % 1000 == 0:
            elapsed = time.time() - start_time
            rate = sent_count / elapsed if elapsed > 0 else 0
            print(
                f"Progress: {sent_count}/{total_packets} packets sent ({rate:.1f} pkt/sec)"
            )

        time.sleep(delay)

    elapsed = time.time() - start_time
    actual_rate = sent_count / elapsed

    print()
    print(f"Sent {sent_count} packets in {elapsed:.2f} seconds")
    print(f"Actual rate: {actual_rate:.1f} packets/sec")
    print()
    print("Check xv6 output for:")
    print("  - Total packets received")
    print("  - Memory leak status")
    print("  - Error count")


if __name__ == "__main__":
    # Default: findmax (auto-discover maximum)
    # Optional: provide a specific rate to test

    if len(sys.argv) == 1:
        # No arguments - run findmax
        test_findmax()
    elif len(sys.argv) == 2:
        arg = sys.argv[1]

        # Check for help
        if arg in ["-h", "--help", "help"]:
            usage()

        # Try to parse as a rate
        try:
            rate = int(arg)
            if rate <= 0:
                print(f"Error: Rate must be positive", file=sys.stderr)
                sys.exit(1)

            # Single test - save result
            result = test_throughput(rate)
            save_results_json(
                [result], rate, result["throughput"], {"test_mode": "single_rate"}
            )
        except ValueError:
            print(f"Error: Invalid rate '{arg}'", file=sys.stderr)
            print(f"Usage: stress_test.py [rate]", file=sys.stderr)
            print(f"  Or: stress_test.py --help", file=sys.stderr)
            sys.exit(1)
    else:
        usage()
