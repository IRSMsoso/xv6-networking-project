#!/usr/bin/env python3

import socket
import sys
import time
import os

# Test basic connectivity first
UID_OFFSET = os.getuid() % 5000
SERVERPORT = UID_OFFSET + 25099

def test_basic_ping():
    """Test basic ping functionality like nettest.py ping does"""
    print("Testing basic ping connectivity...")

    # Create socket to listen for responses
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('127.0.0.1', SERVERPORT))
    sock.settimeout(5.0)

    # Send one packet to port 27001 (maps to xv6 port 2000)
    send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    print(f"Sending test packet to port 27001...")
    print(f"Listening for response on port {SERVERPORT}...")

    payload = b"ping test"
    send_sock.sendto(payload, ('127.0.0.1', 27001))

    try:
        data, addr = sock.recvfrom(4096)
        print(f"SUCCESS: Received response: {data}")
        print(f"From address: {addr}")
        return True
    except socket.timeout:
        print("TIMEOUT: No response received")
        return False
    except Exception as e:
        print(f"ERROR: {e}")
        return False
    finally:
        sock.close()
        send_sock.close()

if __name__ == "__main__":
    test_basic_ping()