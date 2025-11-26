#!/usr/bin/env python3

import socket
import sys
import time
import os
import threading

# Port configuration
UID_OFFSET = os.getuid() % 5000
SERVERPORT = UID_OFFSET + 25099  # Host receives echoes from xv6
BACKUP_SERVERPORT = UID_OFFSET + 25098  # Backup port in case of conflict

# Global variables for tracking results
received_packets = set()
test_running = False

def listen_for_echoes():
    """Listen for echo responses from xv6"""
    global received_packets, test_running

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # Try main port, fall back to backup port
    try:
        sock.bind(('127.0.0.1', SERVERPORT))
        print(f"Listening on port {SERVERPORT}")
    except OSError:
        try:
            sock.bind(('127.0.0.1', BACKUP_SERVERPORT))
            print(f"Listening on backup port {BACKUP_SERVERPORT}")
        except OSError:
            print("ERROR: Cannot bind to any port")
            return

    sock.settimeout(0.5)

    while test_running:
        try:
            data, addr = sock.recvfrom(4096)
            msg = data.decode('ascii', 'ignore')
            if msg.startswith('burst:'):
                received_packets.add(msg)
        except socket.timeout:
            continue
        except Exception:
            break

    sock.close()

def test_ports_with_echo(num_ports):
    """Test num_ports with actual echo verification"""
    global received_packets, test_running

    received_packets.clear()
    test_running = True

    # Start listener thread
    listener = threading.Thread(target=listen_for_echoes)
    listener.daemon = True
    listener.start()

    # Give listener time to start
    time.sleep(0.2)

    packets_per_port = 3
    total_sent = num_ports * packets_per_port
    sent_messages = set()

    # Create socket to send packets
    send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Send packets to each port
    for port_idx in range(num_ports):
        host_port = 27001 + port_idx
        for seq in range(packets_per_port):
            payload = f"burst:{port_idx}:{seq}"
            sent_messages.add(payload)
            send_sock.sendto(payload.encode('ascii'), ('127.0.0.1', host_port))
            time.sleep(0.05)  # Small delay between packets

    send_sock.close()

    # Wait for responses
    time.sleep(2.0)
    test_running = False
    listener.join(timeout=1.0)

    received_count = len(received_packets)
    success_rate = received_count / total_sent if total_sent > 0 else 0

    print(f"Ports: {num_ports:2d} | Sent: {total_sent:2d} | Received: {received_count:2d} | Success: {success_rate:.1%}")

    return success_rate >= 0.6  # 60% success rate required

def main():
    print("Multi-port Echo Test")
    print("=" * 50)
    print("Testing actual packet echo from xv6 burst_server")
    print("(Make sure xv6 is running 'nettest burst')")
    print()

    max_working_ports = 0

    # Test with increasing port counts: 1, 2, 4, 8
    test_counts = [1, 2, 4, 8]

    for num_ports in test_counts:
        if test_ports_with_echo(num_ports):
            max_working_ports = num_ports
            print(f"✓ {num_ports} ports: PASS")
        else:
            print(f"✗ {num_ports} ports: FAIL")
            break

        time.sleep(1)  # Pause between tests

    print()
    print(f"Maximum working ports: {max_working_ports}")

    if max_working_ports >= 8:
        print("Excellent: System supports high port load")
    elif max_working_ports >= 4:
        print("Good: System supports moderate port load")
    elif max_working_ports >= 2:
        print("OK: System supports basic multi-port")
    else:
        print("Needs improvement: Port scaling issues")

if __name__ == "__main__":
    main()