#!/usr/bin/env python3

import socket
import time
import os

# Simple test to verify if network works at all
UID_OFFSET = os.getuid() % 5000
SERVERPORT = UID_OFFSET + 25099

print("Simple Network Test")
print("==================")
print(f"Will listen on port {SERVERPORT} and send to port 27001")
print("Make sure xv6 'nettest burst' is running...")
print()

# Test 1: Just send a packet and see if xv6 receives it
print("Test 1: Sending single packet to port 27001 (maps to xv6 port 2000)")

send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
test_msg = "hello xv6"
send_sock.sendto(test_msg.encode('ascii'), ('127.0.0.1', 27001))
send_sock.close()
print("Packet sent. Check xv6 terminal for any activity.")
time.sleep(2)

# Test 2: Listen for any incoming packets
print("\nTest 2: Listening for any incoming packets for 5 seconds...")

listen_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

try:
    listen_sock.bind(('127.0.0.1', SERVERPORT))
    listen_sock.settimeout(5.0)

    print(f"Listening on {SERVERPORT}...")

    try:
        data, addr = listen_sock.recvfrom(4096)
        print(f"SUCCESS: Received data: {data}")
        print(f"From: {addr}")
    except socket.timeout:
        print("No packets received within 5 seconds")

except Exception as e:
    print(f"Error: {e}")
finally:
    listen_sock.close()

print("\nIf you see network activity in xv6 terminal, basic networking works.")
print("If not, there may be a port mapping or configuration issue.")