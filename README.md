# xv6 Network Stack: E1000 Driver and UDP Implementation

A complete UDP networking stack for the xv6 operating system, featuring an Intel E1000 NIC driver with DMA-based packet handling and UDP protocol implementation.

## Overview

This project extends xv6 with networking capabilities by implementing an E1000 network driver and UDP protocol stack from scratch. We utilized MIT's 6.1810 tests to make sure of the implementation's correctness, but built over them to create stress tests that show the operating system's limits in throughput.

For detailed implementation analysis and design decisions, see [`final_report.pdf`](final_report.pdf).

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

## Architecture

**E1000 Driver:** DMA-based TX/RX rings with separate locks for concurrent operations. Batch-processes received packets per interrupt to minimize overhead.

**UDP Stack:** Think of it like apartment mailboxes with 32 ports, each having 16-packet FIFO queues. `bind()` claims a mailbox, `ip_rx()` sorts incoming packets by port number, `recv()` retrieves them. Queue full? Packet dropped (UDP semantics).

## Performance

All MIT 6.828 correctness tests pass (TX/RX, port isolation, overflow handling, DNS queries, memory stability).

**Throughput:** Max zero-loss rates of 4,013 pkt/s (16-desc ring) and 6,310 pkt/s (64-desc ring). Increasing ring size 300% only yields 57% gain due to the bottleneck being kernel processing, not hardware.

**Latency:** Counterintuitively *decreases* at higher throughput (1.58ms @ 1 msg/s vs 1.23ms @ 1000 msg/s). Batch processing amortizes per-packet overhead.

See [`final_report.pdf`](final_report.pdf) for detailed analysis.

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

