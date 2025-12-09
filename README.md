# xv6 Network Stack: E1000 Driver and UDP Implementation

A complete UDP networking stack for the xv6 operating system, featuring an Intel E1000 NIC driver with DMA-based packet handling and UDP protocol implementation.

## Overview

This project extends xv6 with networking capabilities by implementing an E1000 network driver and UDP protocol stack from scratch. We utilized MIT's 6.1810 tests to make sure of the implementation's correctness, but built over them to create stress tests that show the operating system's limits in throughput.

## Quick Start

### Build and Run

```bash
# Build and run xv6 with networking
make qemu

# Clean build artifacts if needed
make clean

# In xv6 shell
$ nettest
```

### Run Tests

```bash
# Outside QEMU, in separate terminal
cd tests

# Full test suite
python3 grade-lab-net

# Individual tests
python3 host_net_helper.py rx      # Reception test
python3 host_net_helper.py dns     # DNS query

# Throughput testing
python3 stress_test.py             # Auto-find max rate
python3 stress_test.py 5000        # Test at 5000 pkt/s
```

## Project Structure

```
.
├── kernel/                   # xv6 kernel with networking
│   ├── e1000.c               # E1000 driver: TX/RX via DMA rings
│   ├── e1000_dev.h           # E1000 registers & descriptor formats
│   ├── net.c                 # UDP protocol & syscalls (bind/recv/send)
│   ├── net.h                 # Network headers (Ethernet/IP/UDP/ARP/DNS)
│   ├── pci.c                 # PCI bus initialization for E1000
│   └── syscall.c/h           # System call dispatch (SYS_bind/recv/send)
├── user/                     # User-space programs
│   └── nettest.c             # Comprehensive network test suite
├── tests/                    # Testing infrastructure
│   ├── grade-lab-net         # MIT grading script
│   ├── host_net_helper.py    # Python test orchestration
│   ├── stress_test.py        # Throughput/latency benchmarks
│   └── results/              # Test output (JSON)
├── conf/lab.mk               # Lab configuration (LAB=net)
├── Makefile                  # Build system with network support
└── final_report.pdf          # Full research paper
```

## Implementation Details

### E1000 Network Driver

The E1000 driver manages packet I/O through DMA-based circular descriptor rings:

**Transmit (`e1000_transmit`):**
- 16-descriptor TX ring with DD (Descriptor Done) status tracking
- Checks DD bit for descriptor availability
- Frees previous buffer on ring wrap-around
- Sets EOP (End of Packet) and RS (Report Status) flags
- Updates TDT register to notify hardware

**Receive (`e1000_recv`):**
- 16-descriptor RX ring (tested with 64 descriptors)
- Interrupt-driven batch processing (drains all available packets)
- Allocates fresh buffer after extracting each packet
- Passes packets to `net_rx()` for protocol processing

**Synchronization:**
- Separate TX/RX locks enable concurrent send/receive
- Prevents deadlock when RX interrupt fires during TX

### UDP Protocol Stack

Uses a "mailbox analogy" for packet routing:

**Port Management:**
- 32 ports with 16-packet FIFO queues per port
- Tracks: bound status, port number, head/tail pointers, drop count

**Packet Processing (`ip_rx`):**
```c
1. Parse Ethernet → IP → UDP headers
2. Extract dest_port, src_ip, src_port (convert network→host byte order)
3. Find bound port entry
4. If queue full → drop packet (UDP semantics)
5. Else → enqueue packet, wakeup() waiting process
```

**System Calls:**
- `bind(port)` - Claim a port, initialize queue
- `recv(port, src, sport, buf, maxlen)` - Dequeue packet, sleep if empty, copyout to user
- `send(sport, dst, dport, buf, len)` - Build Ethernet/IP/UDP headers, transmit

**Synchronization:**
- Single `netlock` protects all port queues
- Sleep-safe: automatically released/reacquired by `sleep()`

### The Mailbox Analogy

Think of UDP ports as apartment mailboxes:
- `bind(port)` - Claim a mailbox, put your name on it
- `ip_rx()` - Mailman sorting packets into correct mailboxes by port number
- `recv()` - Open your mailbox, retrieve a letter
- Queue full? New mail gets dropped (16-packet limit per port)

## Testing & Validation

### Correctness Tests (MIT 6.828 Lab Suite)

All tests pass successfully:

- **txone/rx/rxburst** - Basic TX/RX, burst handling (32 packets)
- **rx2** - Port isolation (1000+ interleaved packets, zero cross-contamination)
- **ping0/ping1/ping2** - Echo tests, FIFO ordering, dual-port concurrent
- **ping3** - Queue overflow (257 packets → 16 slots, no crash, correct drops)
- **dns** - Real-world Google DNS query (8.8.8.8), validates byte order & interoperability
- **grade** - Memory stability (< 32 pages difference, no leaks)

### Performance Results

**Throughput Testing** (1000 packets, binary search for zero-loss rate):

| Ring Size | Max Zero-Loss Rate | Effective Throughput |
|-----------|-------------------|---------------------|
| 16 descriptors | 4,013 pkt/s | 723 pkt/s (round-trip) |
| 64 descriptors | 6,310 pkt/s | 778 pkt/s (round-trip) |

**Key Finding:** 300% larger ring → only 57% throughput gain. Bottleneck is kernel processing (locks, copyout, queue management), not hardware buffering.

**Latency Testing** (synchronous round-trip):

| Throughput | Average | Median | P95 | P99 | Max |
|-----------|---------|--------|-----|-----|-----|
| 1 msg/s | 1.58ms | 1.65ms | 1.93ms | 1.93ms | 1.93ms |
| 100 msg/s | 1.72ms | 1.55ms | 2.82ms | 4.90ms | 23ms |
| 1000 msg/s | 1.23ms | 1.18ms | 1.47ms | 2.85ms | 39ms |

**Surprising Result:** Average latency *decreases* at higher throughput. Hypothesis: "Hot path" optimization—driver batch-processes multiple packets per interrupt, reducing per-packet overhead.

You may check [`final_report.pdf`](final_report.pdf) to read our discussion over results and design.

## Key Implementation Decisions

- **Packet Copy vs. Buffer Passing**: Copy payload to queue for simpler memory management
- **16-Packet Queue Depth**: Matches UDP best-effort semantics, sufficient for burst handling
- **Separate TX/RX Locks**: Enables concurrent operations, prevents deadlock
- **Batch Receive Processing**: Drain all available packets per interrupt to reduce context switches

## Key Files Reference

**Driver Layer:**
- **`kernel/e1000.c:96`** - `e1000_transmit()` implementation
- **`kernel/e1000.c:129`** - `e1000_recv()` batch processing loop
- **`kernel/e1000.c:162`** - Interrupt handler
- **`kernel/e1000_dev.h`** - Hardware registers and descriptor structures

**Protocol Layer:**
- **`kernel/net.c:303`** - `ip_rx()` packet routing (the "mailman")
- **`kernel/net.c:68`** - `sys_bind()` port registration
- **`kernel/net.c:137`** - `sys_recv()` with sleep/wakeup
- **`kernel/net.c:242`** - `sys_send()` with header construction
- **`kernel/net.h`** - Ethernet/IP/UDP/ARP header definitions, byte order macros

**Testing:**
- **`user/nettest.c`** - Built-in test suite
- **`tests/stress_test.py`** - Throughput/latency benchmarking
- **`tests/host_net_helper.py`** - External test orchestration

