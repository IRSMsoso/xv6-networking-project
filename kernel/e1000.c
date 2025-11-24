#include "types.h"
#include "param.h"
#include "memlayout.h"
#include "riscv.h"
#include "spinlock.h"
#include "proc.h"
#include "defs.h"
#include "e1000_dev.h"

#define TX_RING_SIZE 16
static struct tx_desc tx_ring[TX_RING_SIZE] __attribute__((aligned(16)));

#define RX_RING_SIZE 16
static struct rx_desc rx_ring[RX_RING_SIZE] __attribute__((aligned(16)));

// remember where the e1000's registers live.
static volatile uint32 *regs;

struct spinlock e1000_transmit_lock;
struct spinlock e1000_recv_lock;

// called by pci_init().
// xregs is the memory address at which the
// e1000's registers are mapped.
// this code loosely follows the initialization directions
// in Chapter 14 of Intel's Software Developer's Manual.
void
e1000_init(uint32 *xregs)
{
  int i;

  initlock(&e1000_transmit_lock, "e1000_transmit");
  initlock(&e1000_recv_lock, "e1000_recv");

  regs = xregs;

  // Reset the device
  regs[E1000_IMS] = 0; // disable interrupts
  regs[E1000_CTL] |= E1000_CTL_RST;
  regs[E1000_IMS] = 0; // redisable interrupts
  __sync_synchronize();

  // [E1000 14.5] Transmit initialization
  memset(tx_ring, 0, sizeof(tx_ring));
  for (i = 0; i < TX_RING_SIZE; i++) {
    tx_ring[i].status = E1000_TXD_STAT_DD;
    tx_ring[i].addr = 0;
  }
  regs[E1000_TDBAL] = (uint64) tx_ring;
  if(sizeof(tx_ring) % 128 != 0)
    panic("e1000");
  regs[E1000_TDLEN] = sizeof(tx_ring);
  regs[E1000_TDH] = regs[E1000_TDT] = 0;
  
  // [E1000 14.4] Receive initialization
  memset(rx_ring, 0, sizeof(rx_ring));
  for (i = 0; i < RX_RING_SIZE; i++) {
    rx_ring[i].addr = (uint64) kalloc();
    if (!rx_ring[i].addr)
      panic("e1000");
  }
  regs[E1000_RDBAL] = (uint64) rx_ring;
  if(sizeof(rx_ring) % 128 != 0)
    panic("e1000");
  regs[E1000_RDH] = 0;
  regs[E1000_RDT] = RX_RING_SIZE - 1;
  regs[E1000_RDLEN] = sizeof(rx_ring);

  // filter by qemu's MAC address, 52:54:00:12:34:56
  regs[E1000_RA] = 0x12005452;
  regs[E1000_RA+1] = 0x5634 | (1<<31);
  // multicast table
  for (int i = 0; i < 4096/32; i++)
    regs[E1000_MTA + i] = 0;

  // transmitter control bits.
  regs[E1000_TCTL] = E1000_TCTL_EN |  // enable
    E1000_TCTL_PSP |                  // pad short packets
    (0x10 << E1000_TCTL_CT_SHIFT) |   // collision stuff
    (0x40 << E1000_TCTL_COLD_SHIFT);
  regs[E1000_TIPG] = 10 | (8<<10) | (6<<20); // inter-pkt gap

  // receiver control bits.
  regs[E1000_RCTL] = E1000_RCTL_EN | // enable receiver
    E1000_RCTL_BAM |                 // enable broadcast
    E1000_RCTL_SZ_2048 |             // 2048-byte rx buffers
    E1000_RCTL_SECRC;                // strip CRC
  
  // ask e1000 for receive interrupts.
  regs[E1000_RDTR] = 0; // interrupt after every received packet (no timer)
  regs[E1000_RADV] = 0; // interrupt after every packet (no timer)
  regs[E1000_IMS] = (1 << 7); // RXDW -- Receiver Descriptor Write Back
}

int
e1000_transmit(char *buf, int len)
{
  // First, acquire lock
  acquire(&e1000_transmit_lock);
  
  uint32 tx_next_ring_index = regs[E1000_TDT];

  // If the next descriptor in the ring isn't yet finished (we've wrapped around), then we early return error.
  if (!(tx_ring[tx_next_ring_index].status & E1000_TXD_STAT_DD)) {
    release(&e1000_transmit_lock);
    return -1;
  }

  // Free the last buffer. When we loop around, we'll start freeing every time.
  if (tx_ring[tx_next_ring_index].addr) {
    kfree((void*)tx_ring[tx_next_ring_index].addr);  // Does not null our addr, so we do it.
    tx_ring[tx_next_ring_index].addr = 0;
  }

  tx_ring[tx_next_ring_index].addr = (uint64)buf;
  tx_ring[tx_next_ring_index].length = len;
  tx_ring[tx_next_ring_index].cmd = E1000_TXD_CMD_EOP | E1000_TXD_CMD_RS; // End of Packet (Assumption is that each call and packet will be compromised of just one descriptor in the ring) and Report status so that we can spin on the hardware being finished with the descriptor.
  tx_ring[tx_next_ring_index].status = 0;

  // This is our signal to hardware to process.
  regs[E1000_TDT] = (tx_next_ring_index + 1) % TX_RING_SIZE;

  release(&e1000_transmit_lock);
  
  return 0;
}

static void
e1000_recv(void)
{
  acquire(&e1000_recv_lock);

  // We will loop until we run out of descriptors to process.
  while (1) {
    uint32 rx_next_ring_index = (regs[E1000_RDT] + 1) % RX_RING_SIZE;

    if (!(rx_ring[rx_next_ring_index].status & E1000_RXD_STAT_DD)) {
      // The next descriptor is not yet ready, we're finished looping.
      release(&e1000_recv_lock);
      return;
    }

    // Deliver the packet to kernel.
    net_rx((char*)rx_ring[rx_next_ring_index].addr, rx_ring[rx_next_ring_index].length);

    // Allocate empty page for buffer.
    rx_ring[rx_next_ring_index].addr = (uint64) kalloc();
    if (!rx_ring[rx_next_ring_index].addr)
      panic("e1000 kalloc in e1000_recv()");

    // Clear status
    rx_ring[rx_next_ring_index].status = 0;

    // Move RDT register forward
    regs[E1000_RDT] = rx_next_ring_index;
  }

  panic("e1000_recv unreachable");
}

void
e1000_intr(void)
{
  // tell the e1000 we've seen this interrupt;
  // without this the e1000 won't raise any
  // further interrupts.
  regs[E1000_ICR] = 0xffffffff;

  e1000_recv();
}
