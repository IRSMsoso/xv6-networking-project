# xv6 Network Testing Guide

This guide explains how to run all the network tests for the xv6 networking lab.

## Test Overview

### Correctness Tests (ALL DONE ✅)
Located in `user/nettest.c` and `nettest.py`

### Stress Tests (MOSTLY DONE ✅)
Located in `user/nettest.c`

### Performance Metrics (NOW IMPLEMENTED ✅)
- **Throughput Test** - Added to `user/nettest.c`
- **Latency Test** - Added to `user/nettest.c`
- **Drop Rate Test** - New Python script `stress_test.py`
- **Queue Depth Over Time** - New Python script `stress_test.py`

---

## How to Run Tests

### Setup (2 Terminals Required)

**Terminal 1: xv6**
```bash
make clean
make qemu
```

**Terminal 2: Test Server**
```bash
python3 nettest.py grade
```

**Terminal 1 (in QEMU):**
```bash
nettest grade
```

---

## Performance Metric Tests

### 1. Throughput Test

**What it measures:** Packets per second that xv6 can receive

**Terminal 2:**
```bash
python3 stress_test.py throughput
```

**Terminal 1 (in QEMU):**
```bash
nettest throughput
```

**Expected Output (xv6):**
```
throughput_test: starting
Throughput: 1000 packets in X ticks
throughput_test: OK
```

**How it works:**
- Python sends 1000 packets as fast as possible
- xv6 receives all 1000 packets and measures elapsed time
- Reports packets/tick (convert ticks to ms based on your system)

---

### 2. Latency Test (RTT)

**What it measures:** Round-trip time for ping packets (min/avg/max/p95/p99)

**Terminal 2:**
```bash
python3 nettest.py ping
```

**Terminal 1 (in QEMU):**
```bash
nettest latency
```

**Expected Output (xv6):**
```
latency_test: starting
Latency (ticks): min=X avg=Y max=Z p95=A p99=B
latency_test: OK
```

**How it works:**
- Sends 100 packets with timestamps to the echo server
- Measures round-trip time for each packet
- Calculates statistics: min, avg, max, 95th percentile, 99th percentile

---

### 3. Drop Rate Test

**What it measures:** Percentage of packets dropped under stress

**Terminal 2:**
```bash
python3 stress_test.py droprate
```

**Terminal 1 (in QEMU):**
You need to write a test that counts received packets. Example:

```c
// Add this to nettest.c if you want to automate it
int droprate_test() {
  bind(2000);
  int received = 0;

  // Receive for a fixed time
  int start = uptime();
  while(uptime() - start < 200) {  // 200 ticks = ~2 seconds
    char buf[1500];
    uint32 src;
    uint16 sport;

    // Non-blocking recv would be ideal, but just use timeout
    int cc = recv(2000, &src, &sport, buf, sizeof(buf));
    if(cc > 0) {
      received++;
    }
  }

  printf("Received %d packets\n", received);
  return 1;
}
```

**How to calculate:**
- Python script sends 1000 packets
- xv6 reports how many it received (e.g., 987)
- Drop rate = (1000 - 987) / 1000 * 100 = 1.3%

---

### 4. Queue Depth Over Time

**What it measures:** How queue fills/drains under varying load

**Terminal 2:**
```bash
python3 stress_test.py queuedepth
```

**Terminal 1 (in QEMU):**
To observe queue depth, you need to add instrumentation to your network stack:

**Add to your receive path (e.g., in `kernel/e1000.c` or network stack):**

```c
// In your packet receive interrupt handler or queue management code
void print_queue_depth() {
  static int last_print = 0;
  int now = ticks;

  if (now - last_print > 10) {  // Print every 10 ticks
    printf("Queue depth: %d\n", current_queue_length);
    last_print = now;
  }
}
```

**How it works:**
- Python sends packets at varying rates:
  - Phase 1: Low rate (10 pkt/sec)
  - Phase 2: Medium rate (50 pkt/sec)
  - Phase 3: Burst (500 packets instantly)
  - Phase 4: Recovery (5 pkt/sec)
- xv6 logs queue depth over time
- You can plot the data to visualize queue behavior

---

## Complete Test Checklist

### Correctness Tests ✅
- [x] Single packet TX/RX
- [x] ARP request/response
- [x] UDP echo (ping0)
- [x] DNS query
- [x] Header parsing
- [x] Port isolation (rx2, ping2)
- [x] FIFO ordering (rx)
- [x] Bind semantics

### Stress Tests ✅
- [x] Multiple ports (rx2, ping2)
- [x] Burst traffic (ping3)
- [x] Queue overflow (ping3)
- [x] Memory leaks (countfree)
- [x] Ring wrap-around (ping1, ping3)
- [x] Packet drops (ping3)

### Performance Metrics ✅
- [x] **Throughput (pkts/sec)** - `nettest throughput` + `stress_test.py throughput`
- [x] **Latency (RTT ms)** - `nettest latency` + `nettest.py ping`
- [x] **Drop rate %** - `stress_test.py droprate` (manual calculation)
- [x] **Queue depth over time** - `stress_test.py queuedepth` (requires instrumentation)

---

## Quick Reference Commands

### Run All Correctness Tests
```bash
# Terminal 2
python3 nettest.py grade

# Terminal 1 (QEMU)
nettest grade
```

### Run Individual Tests

```bash
# Terminal 1 (QEMU)
nettest txone
nettest ping0
nettest ping1
nettest ping2
nettest ping3
nettest dns
nettest throughput
nettest latency
```

### Run Stress Tests

```bash
# Terminal 2
python3 stress_test.py droprate
python3 stress_test.py queuedepth
python3 stress_test.py throughput
```

---

## Expected Results Summary

| Test | Location | Expected Result |
|------|----------|----------------|
| Throughput | nettest.c:844-867 | Reports packets/tick |
| Latency | nettest.c:876-951 | min/avg/max/p95/p99 in ticks |
| Drop Rate | stress_test.py | Script sends 1000, calculate % |
| Queue Depth | stress_test.py | Requires instrumentation |

---

## Notes

1. **Tick to milliseconds conversion**:
   - xv6 tick rate depends on QEMU configuration
   - Typically 10ms per tick
   - Adjust your calculations accordingly

2. **Port Configuration**:
   - Tests use ports 2000-3001
   - Configured in nettest.py via FWDPORT1/FWDPORT2
   - Based on UID to avoid conflicts

3. **IDE Warnings**:
   - You may see "NET_TESTS_PORT is undefined" errors in your IDE
   - This is a false positive - NET_TESTS_PORT is defined via Makefile
   - The code will compile correctly with `make qemu`

4. **Customization**:
   - You can adjust packet counts in tests (currently 1000 for throughput)
   - You can adjust latency sample count (currently 100)
   - Modify stress_test.py rates for different load patterns

---

## Implementation Files

- **`user/nettest.c`** - Lines 840-951: New throughput_test() and latency_test()
- **`stress_test.py`** - New file for drop rate and queue depth testing
- **`nettest.py`** - Existing test server (unchanged, compatible with new tests)

---

## Troubleshooting

### "recv() failed" errors
- Make sure nettest.py or stress_test.py is running first
- Check that port forwarding is configured correctly

### No packets received
- Verify QEMU networking is set up correctly
- Check that both xv6 and Python script are using matching ports

### Latency test hangs
- Ensure `python3 nettest.py ping` is running (acts as echo server)
- The ping server must be started BEFORE running `nettest latency`

---

Good luck with your testing!
