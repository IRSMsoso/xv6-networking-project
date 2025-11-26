#!/usr/bin/env python3

#
# net tests
# to be used with user/nettest.c
#

from datetime import datetime
import socket
import sys
import threading
import time
import os
import random

# qemu listens for packets sent to FWDPORT,
# and re-writes them so they arrive in
# xv6 with destination port 2000.
FWDPORT1 = (os.getuid() % 5000) + 25999
FWDPORT2 = (os.getuid() % 5000) + 30999

# xv6's nettest.c tx sends to SERVERPORT.
SERVERPORT = (os.getuid() % 5000) + 25099


def usage():
    sys.stderr.write("Usage: nettest.py txone\n")
    sys.stderr.write("       nettest.py rxone\n")
    sys.stderr.write("       nettest.py rx\n")
    sys.stderr.write("       nettest.py rx2\n")
    sys.stderr.write("       nettest.py rxburst\n")
    sys.stderr.write("       nettest.py tx\n")
    sys.stderr.write("       nettest.py ping\n")
    sys.stderr.write("       nettest.py latency\n")
    sys.stderr.write("       nettest.py latency_sync\n")
    sys.stderr.write("       nettest.py grade\n")
    sys.exit(1)


if len(sys.argv) != 2:
    usage()

if sys.argv[1] == "txone":
    #
    # listen for a single UDP packet sent by xv6's nettest txone.
    # nettest.py must be started before xv6's nettest txone.
    #
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", SERVERPORT))
    print("tx: listening for a UDP packet")
    buf0, raddr0 = sock.recvfrom(4096)
    if buf0 == b"txone":
        print("txone: OK")
    else:
        print("txone: unexpected payload %s" % (buf0))
elif sys.argv[1] == "rxone":
    #
    # send a single UDP packet to xv6 to test e1000_recv().
    # should result in arp_rx() printing
    #   arp_rx: received an ARP packet
    # and ip_rx() printing
    #   ip_rx: received an IP packet
    #
    print("txone: sending one UDP packet")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(b"xyz", ("127.0.0.1", FWDPORT1))
elif sys.argv[1] == "rx":
    #
    # test the xv6 receive path by sending a slow
    # stream of UDP packets, which should appear
    # on port 2000.
    #
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    i = 0
    while True:
        txt = "packet %d" % (i)
        sys.stderr.write("%s\n" % txt)
        buf = txt.encode("ascii", "ignore")
        sock.sendto(buf, ("127.0.0.1", FWDPORT1))
        time.sleep(1)
        i += 1
elif sys.argv[1] == "rx2":
    #
    # send to two different UDP ports, to see
    # if xv6 keeps them separate.
    #
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    i = 0
    while True:
        txt = "one %d" % (i)
        sys.stderr.write("%s\n" % txt)
        buf = txt.encode("ascii", "ignore")
        sock.sendto(buf, ("127.0.0.1", FWDPORT1))

        txt = "two %d" % (i)
        sys.stderr.write("%s\n" % txt)
        buf = txt.encode("ascii", "ignore")
        sock.sendto(buf, ("127.0.0.1", FWDPORT2))

        time.sleep(1)
        i += 1
elif sys.argv[1] == "rxburst":
    #
    # send a big burst of packets to 2001, then
    # a packet to 2000.
    #
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    i = 0
    while True:
        for ii in range(0, 32):
            txt = "packet %d" % (i)
            # sys.stderr.write("%s\n" % txt)
            buf = txt.encode("ascii", "ignore")
            sock.sendto(buf, ("127.0.0.1", FWDPORT2))

        txt = "packet %d" % (i)
        sys.stderr.write("%s\n" % txt)
        buf = txt.encode("ascii", "ignore")
        sock.sendto(buf, ("127.0.0.1", FWDPORT1))

        time.sleep(1)
        i += 1
elif sys.argv[1] == "tx":
    #
    # listen for UDP packets sent by xv6's nettest tx.
    # nettest.py must be started before xv6's nettest tx.
    #
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", SERVERPORT))
    print("tx: listening for UDP packets")
    buf0, raddr0 = sock.recvfrom(4096)
    buf1, raddr1 = sock.recvfrom(4096)
    if buf0 == b"t 0" and buf1 == b"t 1":
        print("tx: OK")
    else:
        print("tx: unexpected packets %s and %s" % (buf0, buf1))
elif sys.argv[1] == "ping":
    #
    # listen for UDP packets sent by xv6's nettest ping,
    # and send them back.
    # nettest.py must be started before xv6's nettest.
    #
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", SERVERPORT))
    print("ping: listening for UDP packets")
    while True:
        buf, raddr = sock.recvfrom(4096)
        sock.sendto(buf, raddr)
elif sys.argv[1] == "grade":
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", SERVERPORT))

    # first, listen for a single UDP packet sent by xv6,
    # in order to test only e1000_transmit(), in a situation
    # where perhaps e1000_recv() has not yet been implemented.
    buf, raddr = sock.recvfrom(4096)
    if buf == b"txone":
        print("txone: OK")
    else:
        print("txone: received incorrect payload %s" % (buf))
    sys.stdout.flush()
    sys.stderr.flush()

    # second, send a single UDP packet, to test
    # e1000_recv() -- received by user/nettest.c's rxone().
    print("rxone: sending one UDP packet")
    sock1 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock1.sendto(b"rxone", ("127.0.0.1", FWDPORT2))

    # third, act as a ping reflector.
    while True:
        buf, raddr = sock.recvfrom(4096)
        sock.sendto(buf, raddr)
elif sys.argv[1] == "latency_sync":
    #
    # Synchronous latency test - measures true per-packet RTT
    # Send one, wait for reply, measure, repeat
    #
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", SERVERPORT))
    sock.settimeout(2.0)  # 2 second timeout
    print("Bound to", SERVERPORT)
    print("Synchronous latency test - each packet measured individually")

    throughputs = [1, 10, 100, 1000]
    random.shuffle(throughputs)
    print("Randomized test order:", throughputs)

    results = {}

    for throughput in throughputs:
        print(f"\nTesting with {throughput} packets/sec rate")
        latencies = []
        interval = 1.0 / throughput
        packet_id = 0

        # Send packets at specified rate, measuring each individually
        for i in range(throughput * 5):  # 5 seconds worth
            # Send packet
            msg = packet_id.to_bytes(8, "big")
            send_time = time.perf_counter()
            sock.sendto(msg, ("127.0.0.1", FWDPORT1))

            # Wait for reply
            try:
                reply, addr = sock.recvfrom(128)
                recv_time = time.perf_counter()

                # Verify it's our packet
                reply_id = int.from_bytes(reply[:8], "big")
                if reply_id == packet_id:
                    latency_ms = (recv_time - send_time) * 1000.0
                    latencies.append(latency_ms)
            except socket.timeout:
                print(f"  Packet {packet_id} timeout!")

            packet_id += 1

            # Sleep to maintain rate
            time.sleep(interval)

        # Calculate stats including percentiles
        if latencies:
            sorted_lat = sorted(latencies)
            n = len(sorted_lat)
            results[throughput] = {
                "avg": sum(latencies) / len(latencies),
                "min": min(latencies),
                "max": max(latencies),
                "p50": sorted_lat[n // 2],
                "p95": sorted_lat[int(n * 0.95)],
                "p99": sorted_lat[int(n * 0.99)] if n >= 100 else sorted_lat[-1],
                "count": len(latencies),
            }

        print(f"Cooldown (2 seconds)...")
        time.sleep(2)

    # Print results in sorted order
    print("\n" + "=" * 60)
    print("SYNCHRONOUS LATENCY RESULTS")
    print("=" * 60)
    for throughput in sorted(results.keys()):
        r = results[throughput]
        print(f"\nThroughput: {throughput} msg/sec")
        print(f"  Average: {r['avg']:.3f} ms")
        print(f"  Median:  {r['p50']:.3f} ms (P50)")
        print(f"  P95:     {r['p95']:.3f} ms")
        print(f"  P99:     {r['p99']:.3f} ms")
        print(f"  Min:     {r['min']:.3f} ms")
        print(f"  Max:     {r['max']:.3f} ms")
        print(f"  Samples: {r['count']}")

    exit()

elif sys.argv[1] == "latency":

    class LatencyInfo:
        throughput = None
        send_time = None
        recv_time = None

    throughputs = [1, 10, 100, 1000]
    # RANDOMIZE ORDER to test if warm-up affects results
    random.shuffle(throughputs)
    print("Randomized test order:", throughputs)

    # throughputs = [1]

    total_sent = 0

    for throughput in throughputs:
        total_sent += throughput * 10

    send_infos = {}

    id = 0

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", SERVERPORT))
    print("Bound to", SERVERPORT)

    def recv_thread(sock: socket.socket):
        print("recv thread started")
        while True:
            buf0, raddr0 = sock.recvfrom(8)
            recv_id = int.from_bytes(buf0, "big")
            # print("Received ID", recv_id)
            send_infos[recv_id].recv_time = time.perf_counter()

    t = threading.Thread(target=recv_thread, args=(sock,))
    t.start()

    for throughput in throughputs:
        print("Testing latency with throughput:", throughput, "per second")
        # We do 10 seconds of each throughput
        for i in range(throughput * 10):
            # Encode
            send_infos[id] = LatencyInfo()
            send_infos[id].send_time = time.perf_counter()
            send_infos[id].throughput = throughput
            sock.sendto(id.to_bytes(8, "big"), ("127.0.0.1", FWDPORT1))
            id += 1
            time.sleep(1 / throughput)
            # print("Throughput", throughput, "and sleeping for", 1 / throughput, "i:", i)

        # ADD COOLDOWN between tests to let system "go cold"
        print(f"Cooldown period (3 seconds)...")
        time.sleep(3)

    print("Waiting 5 seconds for recv to catch up")

    time.sleep(5)

    num_recv = 0

    throughput_stats = {}

    # Sort throughputs for consistent output display
    for throughput in sorted([1, 10, 100, 1000]):
        min_latency = 1000000000
        max_latency = 0
        total_latency = 0
        num_valid = 0
        for send_info in send_infos.values():
            if send_info.throughput != throughput:
                continue

            if send_info.recv_time != None:
                num_recv += 1
                num_valid += 1
                latency = (send_info.recv_time - send_info.send_time) * 1000.0
                # print("latency:", latency)
                total_latency += latency
                if latency < min_latency:
                    min_latency = latency
                if latency > max_latency:
                    max_latency = latency

        print(
            "Average latency for throughput of " + str(throughput) + " per second:",
            total_latency / num_valid,
            "ms",
        )
        print(
            "Max latency for throughput of " + str(throughput) + " per second:",
            max_latency,
            "ms",
        )
        print(
            "Min latency for throughput of " + str(throughput) + " per second:",
            min_latency,
            "ms",
        )

    print("Total messages sent:", len(send_infos))
    print("Total messages received:", num_recv)

    exit()

else:
    usage()
