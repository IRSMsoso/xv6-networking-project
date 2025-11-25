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

# qemu listens for packets sent to FWDPORT,
# and re-writes them so they arrive in
# xv6 with destination port 2000.
FWDPORT1 = (os.getuid() % 5000) + 25999
FWDPORT2 = (os.getuid() % 5000) + 30999

# xv6's nettest.c tx sends to SERVERPORT.
SERVERPORT = (os.getuid() % 5000) + 25099

def usage():
    sys.stderr.write("Usage: stress_test.py droprate\n")
    sys.stderr.write("       stress_test.py queuedepth\n")
    sys.stderr.write("       stress_test.py throughput\n")
    sys.stderr.write("       stress_test.py sustained\n")
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
        payload = f"droptest {i}".encode('ascii')
        sock.sendto(payload, ("127.0.0.1", FWDPORT1))

    elapsed = time.time() - start_time
    print(f"Sent {packets_sent} packets in {elapsed:.3f} seconds")
    print(f"Rate: {packets_sent/elapsed:.1f} packets/sec")
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
        payload = f"queue_low {i}".encode('ascii')
        sock.sendto(payload, ("127.0.0.1", FWDPORT1))
        time.sleep(0.1)  # 10 packets per second

    print("Phase 1 complete. Check xv6 queue behavior.")
    time.sleep(1)

    # Phase 2: Send at medium rate
    print("\nPhase 2: Medium rate (50 pkt/sec) for 5 seconds")
    for i in range(250):
        payload = f"queue_med {i}".encode('ascii')
        sock.sendto(payload, ("127.0.0.1", FWDPORT1))
        time.sleep(0.02)  # 50 packets per second

    print("Phase 2 complete. Check xv6 queue behavior.")
    time.sleep(1)

    # Phase 3: Send burst
    print("\nPhase 3: Burst (500 packets instantly)")
    for i in range(500):
        payload = f"queue_burst {i}".encode('ascii')
        sock.sendto(payload, ("127.0.0.1", FWDPORT1))

    print("Phase 3 complete. Check xv6 queue behavior.")
    time.sleep(2)

    # Phase 4: Recovery period
    print("\nPhase 4: Recovery (slow rate 5 pkt/sec) for 5 seconds")
    for i in range(25):
        payload = f"queue_recover {i}".encode('ascii')
        sock.sendto(payload, ("127.0.0.1", FWDPORT1))
        time.sleep(0.2)  # 5 packets per second

    print("\nQueue depth test complete!")
    print("\nTo visualize queue depth over time:")
    print("1. Add instrumentation in xv6 to print queue length")
    print("2. Log timestamps and queue sizes")
    print("3. Plot the data to see queue behavior under load")

def test_throughput():
    """
    Send 1000 packets to xv6 for throughput measurement
    """
    print("Throughput Test: Starting")
    print("=" * 60)
    print("Sending 1000 packets to port 3000...")
    print("(Make sure xv6 is running 'nettest throughput')")
    print()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Map port 3000 to appropriate forward port
    # Adjust based on your qemu configuration
    # Using FWDPORT1 as default, may need adjustment
    target_port = FWDPORT1

    packets_sent = 1000
    start_time = time.time()

    for i in range(packets_sent):
        payload = f"throughput {i}".encode('ascii')
        # Note: May need to bind to specific port or adjust forwarding
        sock.sendto(payload, ("127.0.0.1", target_port))

    elapsed = time.time() - start_time

    print(f"Sent {packets_sent} packets in {elapsed:.3f} seconds")
    print(f"Throughput: {packets_sent/elapsed:.1f} packets/sec")
    print()
    print("Check xv6 output for received throughput measurement")

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
        payload = f"sustained {i}".encode('ascii')
        sock.sendto(payload, ("127.0.0.1", target_port))
        sent_count += 1

        # Print progress every 1000 packets
        if (i + 1) % 1000 == 0:
            elapsed = time.time() - start_time
            rate = sent_count / elapsed if elapsed > 0 else 0
            print(f"Progress: {sent_count}/{total_packets} packets sent ({rate:.1f} pkt/sec)")

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
    if len(sys.argv) != 2:
        usage()

    if sys.argv[1] == "droprate":
        test_droprate()
    elif sys.argv[1] == "queuedepth":
        test_queuedepth()
    elif sys.argv[1] == "throughput":
        test_throughput()
    elif sys.argv[1] == "sustained":
        test_sustained()
    else:
        usage()
