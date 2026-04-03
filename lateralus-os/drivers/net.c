/* ═══════════════════════════════════════════════════════════════════════
 * LateralusOS — Network Driver (RTL8139)
 * ═══════════════════════════════════════════════════════════════════════
 * RTL8139 Ethernet NIC driver via PCI I/O.  The RTL8139 is the default
 * network card emulated by QEMU (`-net nic,model=rtl8139`).
 *
 * This driver provides:
 *   - PCI bus scan to detect the RTL8139 (vendor 0x10EC, device 0x8139)
 *   - Hardware reset, MAC read, RX/TX buffer allocation
 *   - Polled send/receive (interrupt support stubbed for later)
 *
 * Copyright (c) 2025-2026 bad-antics. All rights reserved.
 * ═══════════════════════════════════════════════════════════════════════ */

#include "net.h"

/* ── External symbols (from kernel_stub.c) ────────────────────────────── */

extern void serial_puts(const char *s);
extern void *kmalloc(uint64_t size);

/* ── Port I/O helpers ─────────────────────────────────────────────────── */

static inline void outb(uint16_t port, uint8_t val) {
    __asm__ volatile ("outb %0, %1" :: "a"(val), "Nd"(port));
}

static inline uint8_t inb(uint16_t port) {
    uint8_t val;
    __asm__ volatile ("inb %1, %0" : "=a"(val) : "Nd"(port));
    return val;
}

static inline void outw(uint16_t port, uint16_t val) {
    __asm__ volatile ("outw %0, %1" :: "a"(val), "Nd"(port));
}

static inline uint16_t inw(uint16_t port) {
    uint16_t val;
    __asm__ volatile ("inw %1, %0" : "=a"(val) : "Nd"(port));
    return val;
}

static inline void outl(uint16_t port, uint32_t val) {
    __asm__ volatile ("outl %0, %1" :: "a"(val), "Nd"(port));
}

static inline uint32_t inl(uint16_t port) {
    uint32_t val;
    __asm__ volatile ("inl %1, %0" : "=a"(val) : "Nd"(port));
    return val;
}

/* ── PCI configuration space ──────────────────────────────────────────── */

#define PCI_CONFIG_ADDR  0x0CF8
#define PCI_CONFIG_DATA  0x0CFC

static uint32_t pci_read32(uint8_t bus, uint8_t dev, uint8_t func, uint8_t off) {
    uint32_t addr = (1u << 31)
                  | ((uint32_t)bus  << 16)
                  | ((uint32_t)dev  << 11)
                  | ((uint32_t)func << 8)
                  | (off & 0xFC);
    outl(PCI_CONFIG_ADDR, addr);
    return inl(PCI_CONFIG_DATA);
}

static void pci_write32(uint8_t bus, uint8_t dev, uint8_t func, uint8_t off, uint32_t val) {
    uint32_t addr = (1u << 31)
                  | ((uint32_t)bus  << 16)
                  | ((uint32_t)dev  << 11)
                  | ((uint32_t)func << 8)
                  | (off & 0xFC);
    outl(PCI_CONFIG_ADDR, addr);
    outl(PCI_CONFIG_DATA, val);
}

/* ── RTL8139 register offsets ─────────────────────────────────────────── */

#define RTL_IDR0       0x00  /* MAC address bytes 0-3             */
#define RTL_IDR4       0x04  /* MAC address bytes 4-5             */
#define RTL_MAR0       0x08  /* Multicast filter                  */
#define RTL_TSD0       0x10  /* TX status descriptor 0            */
#define RTL_TSAD0      0x20  /* TX start address descriptor 0     */
#define RTL_RBSTART    0x30  /* RX buffer start (physical)        */
#define RTL_CMD        0x37  /* Command register                  */
#define RTL_CAPR       0x38  /* Current address of packet read    */
#define RTL_CBR        0x3A  /* Current buffer address            */
#define RTL_IMR        0x3C  /* Interrupt mask                    */
#define RTL_ISR        0x3E  /* Interrupt status                  */
#define RTL_TCR        0x40  /* Transmit configuration            */
#define RTL_RCR        0x44  /* Receive configuration             */
#define RTL_CONFIG1    0x52  /* Config register 1 (power)         */

/* CMD bits */
#define RTL_CMD_RESET  0x10
#define RTL_CMD_RE     0x08  /* Receiver enable                   */
#define RTL_CMD_TE     0x04  /* Transmitter enable                */

/* RCR bits */
#define RTL_RCR_AAP    (1 << 0)  /* Accept all packets            */
#define RTL_RCR_APM    (1 << 1)  /* Accept physical match         */
#define RTL_RCR_AM     (1 << 2)  /* Accept multicast              */
#define RTL_RCR_AB     (1 << 3)  /* Accept broadcast              */
#define RTL_RCR_WRAP   (1 << 7)  /* Wrap at end of RX buffer      */

/* ISR/IMR bits */
#define RTL_INT_ROK    0x0001  /* Receive OK                      */
#define RTL_INT_TOK    0x0004  /* Transmit OK                     */

/* TSD bits */
#define RTL_TSD_OWN    (1 << 13)

/* ── Global state ─────────────────────────────────────────────────────── */

static NetDeviceInfo nic;
static uint8_t *rx_buffer;                      /* RX ring buffer       */
static uint8_t *tx_buffers[NET_TX_BUF_COUNT];   /* TX descriptor bufs   */
static int      tx_cur;                         /* Next TX descriptor   */
static uint16_t rx_offset;                      /* Current RX offset    */

/* ── Hex helpers ──────────────────────────────────────────────────────── */

static const char hex_chars[] = "0123456789ABCDEF";

static void hex8(char *out, uint8_t v) {
    out[0] = hex_chars[(v >> 4) & 0xF];
    out[1] = hex_chars[v & 0xF];
}

/* ── memcpy (freestanding — no libc) ──────────────────────────────────── */

static void net_memcpy(void *dst, const void *src, uint64_t n) {
    uint8_t *d = (uint8_t *)dst;
    const uint8_t *s = (const uint8_t *)src;
    while (n--) *d++ = *s++;
}

static void net_memset(void *dst, uint8_t val, uint64_t n) {
    uint8_t *d = (uint8_t *)dst;
    while (n--) *d++ = val;
}

/* ── I/O wait (400ns) ─────────────────────────────────────────────────── */

static void io_wait(void) {
    inb(0x80); inb(0x80); inb(0x80); inb(0x80);
}

/* ── PCI scan for RTL8139 ─────────────────────────────────────────────── */

/* Scan the PCI bus for vendor:device.
   Returns 1 and fills *out_bus, *out_dev, *out_func if found. */
static int pci_find(uint16_t vendor, uint16_t device,
                    uint8_t *out_bus, uint8_t *out_dev, uint8_t *out_func)
{
    for (int bus = 0; bus < 256; bus++) {
        for (int dev = 0; dev < 32; dev++) {
            uint32_t id = pci_read32(bus, dev, 0, 0);
            if (id == 0xFFFFFFFF) continue;
            uint16_t vid = id & 0xFFFF;
            uint16_t did = (id >> 16) & 0xFFFF;
            if (vid == vendor && did == device) {
                *out_bus  = bus;
                *out_dev  = dev;
                *out_func = 0;
                return 1;
            }
        }
    }
    return 0;
}

/* ── RTL8139 initialisation ───────────────────────────────────────────── */

static int rtl8139_init(uint8_t bus, uint8_t dev, uint8_t func) {
    /* Read BAR0 (I/O base address) */
    uint32_t bar0 = pci_read32(bus, dev, func, 0x10);
    if (!(bar0 & 1)) {
        serial_puts("[net] RTL8139 BAR0 is memory-mapped — expected I/O\n");
        return 0;
    }
    nic.io_base = (uint16_t)(bar0 & 0xFFFC);

    /* Read IRQ line */
    uint32_t irq_reg = pci_read32(bus, dev, func, 0x3C);
    nic.irq = (uint8_t)(irq_reg & 0xFF);

    /* Enable PCI bus mastering (set bit 2 of Command register) */
    uint32_t pci_cmd = pci_read32(bus, dev, func, 0x04);
    pci_cmd |= (1 << 2);    /* bus master */
    pci_cmd |= (1 << 0);    /* I/O space  */
    pci_write32(bus, dev, func, 0x04, pci_cmd);

    uint16_t io = nic.io_base;

    /* Power on */
    outb(io + RTL_CONFIG1, 0x00);
    io_wait();

    /* Software reset */
    outb(io + RTL_CMD, RTL_CMD_RESET);
    int timeout = 1000;
    while ((inb(io + RTL_CMD) & RTL_CMD_RESET) && --timeout) {
        io_wait();
    }
    if (!timeout) {
        serial_puts("[net] RTL8139 reset timed out\n");
        return 0;
    }

    /* Read MAC address */
    for (int i = 0; i < 4; i++)
        nic.mac[i] = inb(io + RTL_IDR0 + i);
    for (int i = 0; i < 2; i++)
        nic.mac[4 + i] = inb(io + RTL_IDR4 + i);

    /* Allocate RX buffer (NET_RX_BUF_SIZE) */
    rx_buffer = (uint8_t *)kmalloc(NET_RX_BUF_SIZE);
    if (!rx_buffer) {
        serial_puts("[net] Failed to allocate RX buffer\n");
        return 0;
    }
    net_memset(rx_buffer, 0, NET_RX_BUF_SIZE);

    /* Allocate TX buffers */
    for (int i = 0; i < NET_TX_BUF_COUNT; i++) {
        tx_buffers[i] = (uint8_t *)kmalloc(NET_MAX_PACKET);
        if (!tx_buffers[i]) {
            serial_puts("[net] Failed to allocate TX buffer\n");
            return 0;
        }
        net_memset(tx_buffers[i], 0, NET_MAX_PACKET);
    }
    tx_cur = 0;
    rx_offset = 0;

    /* Set RX buffer address (physical — identity-mapped) */
    outl(io + RTL_RBSTART, (uint32_t)(uint64_t)rx_buffer);

    /* Enable receiver and transmitter */
    outb(io + RTL_CMD, RTL_CMD_RE | RTL_CMD_TE);

    /* Configure RX: accept broadcast + physical match + multicast + all,
       wrap mode, max DMA burst 1024 */
    outl(io + RTL_RCR, RTL_RCR_AB | RTL_RCR_APM | RTL_RCR_AM
                      | RTL_RCR_AAP | RTL_RCR_WRAP
                      | (6 << 8)    /* RBLEN = 8K+16  */
                      | (7 << 13)); /* Max DMA burst   */

    /* Configure TX: max DMA burst, interframe gap */
    outl(io + RTL_TCR, (6 << 8) | (3 << 24));  /* DMA burst 1024, IFG default */

    /* Enable interrupts: ROK + TOK */
    outw(io + RTL_IMR, RTL_INT_ROK | RTL_INT_TOK);

    /* Clear pending interrupts */
    outw(io + RTL_ISR, 0xFFFF);

    /* Set TX start addresses (physical — identity-mapped) */
    for (int i = 0; i < NET_TX_BUF_COUNT; i++) {
        outl(io + RTL_TSAD0 + i * 4, (uint32_t)(uint64_t)tx_buffers[i]);
    }

    nic.present = 1;
    nic.type    = NET_TYPE_RTL8139;

    return 1;
}

/* ═══════════════════════════════════════════════════════════════════════
 * Public API
 * ═══════════════════════════════════════════════════════════════════════ */

int net_init(void) {
    uint8_t bus, dev, func;

    net_memset(&nic, 0, sizeof(nic));
    rx_buffer = 0;
    tx_cur    = 0;
    rx_offset = 0;

    /* Probe for RTL8139 (vendor 0x10EC, device 0x8139) */
    if (pci_find(0x10EC, 0x8139, &bus, &dev, &func)) {
        char msg[] = "[net] RTL8139 found on PCI 00:00.0\n";
        /* patch bus:dev.func into message */
        msg[27] = '0' + (bus / 10); msg[28] = '0' + (bus % 10);
        msg[30] = '0' + (dev / 10); msg[31] = '0' + (dev % 10);
        msg[33] = '0' + func;
        serial_puts(msg);

        if (rtl8139_init(bus, dev, func)) {
            /* Print MAC */
            char mac_msg[64];
            net_memcpy(mac_msg, "[net] MAC: ", 11);
            for (int i = 0; i < 6; i++) {
                int off = 11 + i * 3;
                hex8(mac_msg + off, nic.mac[i]);
                mac_msg[off + 2] = (i < 5) ? ':' : '\n';
            }
            mac_msg[11 + 6 * 3] = '\0';
            serial_puts(mac_msg);

            char irq_msg[] = "[net] IRQ: 00\n";
            irq_msg[11] = '0' + (nic.irq / 10);
            irq_msg[12] = '0' + (nic.irq % 10);
            serial_puts(irq_msg);

            serial_puts("[net] RTL8139 initialized\n");
            return 1;
        }
    }

    serial_puts("[net] No supported network adapter found\n");
    return 0;
}

const NetDeviceInfo *net_get_info(void) {
    return nic.present ? &nic : 0;
}

int net_send(const void *data, uint16_t length) {
    if (!nic.present) return -1;
    if (length > NET_MAX_PACKET || length < 14) return -1;

    uint16_t io = nic.io_base;

    /* Wait for the current TX descriptor to become available */
    int timeout = 10000;
    while (!(inl(io + RTL_TSD0 + tx_cur * 4) & RTL_TSD_OWN) && --timeout) {
        io_wait();
    }

    /* Copy frame into TX buffer */
    net_memcpy(tx_buffers[tx_cur], data, length);

    /* Tell the NIC: set size (clears OWN bit, starts transmission) */
    outl(io + RTL_TSD0 + tx_cur * 4, length & 0x1FFF);

    nic.packets_tx++;
    nic.bytes_tx += length;

    /* Advance to next descriptor */
    tx_cur = (tx_cur + 1) % NET_TX_BUF_COUNT;

    return 0;
}

uint16_t net_recv(void *buf, uint16_t buf_size) {
    if (!nic.present || !rx_buffer) return 0;

    uint16_t io = nic.io_base;

    /* Check if buffer is empty */
    uint8_t cmd = inb(io + RTL_CMD);
    if (cmd & 0x01) {
        /* BUFE bit set — buffer is empty */
        return 0;
    }

    /* Read packet header from RX ring buffer.
       RTL8139 RX format: [status:16][length:16][data...][padding to dword] */
    uint16_t *header = (uint16_t *)(rx_buffer + rx_offset);
    uint16_t status = header[0];
    uint16_t pkt_len = header[1];  /* includes CRC (4 bytes) */

    /* Validate */
    if (!(status & 0x01)) {
        /* ROK bit not set — bad packet */
        return 0;
    }
    if (pkt_len > NET_MAX_PACKET + 4 || pkt_len < 18) {
        /* Bogus length — skip */
        rx_offset = (rx_offset + pkt_len + 4 + 3) & ~3u;
        rx_offset %= NET_RX_BUF_SIZE;
        outw(io + RTL_CAPR, rx_offset - 16);
        return 0;
    }

    /* Copy payload (skip 4-byte header, omit 4-byte CRC) */
    uint16_t data_len = pkt_len - 4;
    if (data_len > buf_size) data_len = buf_size;
    net_memcpy(buf, rx_buffer + rx_offset + 4, data_len);

    /* Advance RX pointer (dword-aligned) */
    rx_offset = (rx_offset + pkt_len + 4 + 3) & ~3u;
    rx_offset %= NET_RX_BUF_SIZE;
    outw(io + RTL_CAPR, rx_offset - 16);

    nic.packets_rx++;
    nic.bytes_rx += data_len;

    return data_len;
}

void net_mac_str(char *out) {
    for (int i = 0; i < 6; i++) {
        hex8(out + i * 3, nic.mac[i]);
        out[i * 3 + 2] = (i < 5) ? ':' : '\0';
    }
}

int net_link_up(void) {
    if (!nic.present) return 0;
    /* RTL8139 basic media status register at offset 0x58 (BMSR) */
    uint8_t msr = inb(nic.io_base + 0x58);
    /* Bit 2 = link status (inverted on some models; for QEMU it's straightforward) */
    return (msr & 0x04) ? 0 : 1;  /* link OK if bit NOT set in RTL convention */
}
