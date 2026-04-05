/* =======================================================================
 * LateralusOS — Network Driver (RTL8139 / NE2000)
 * =======================================================================
 * PCI-based Ethernet NIC driver supporting RTL8139 (common in QEMU).
 * Provides basic send/receive for raw Ethernet frames.
 *
 * Copyright (c) 2025-2026 bad-antics. All rights reserved.
 * ======================================================================= */

#ifndef LATERALUS_NET_H
#define LATERALUS_NET_H

#include "../gui/types.h"

/* -- Constants ---------------------------------------------------------- */

#define NET_MAX_PACKET    1536
#define NET_RX_BUF_SIZE   (8192 + 16 + 1536)
#define NET_TX_BUF_COUNT  4

/* Supported NIC types */
#define NET_TYPE_NONE     0
#define NET_TYPE_RTL8139  1
#define NET_TYPE_NE2000   2

/* -- NIC info ----------------------------------------------------------- */

typedef struct {
    uint8_t  present;            /* 1 if NIC detected              */
    uint8_t  type;               /* NET_TYPE_RTL8139 / NE2000      */
    uint8_t  mac[6];             /* MAC address                    */
    uint16_t io_base;            /* I/O base port                  */
    uint8_t  irq;                /* IRQ line                       */
    uint32_t packets_tx;         /* Packets sent                   */
    uint32_t packets_rx;         /* Packets received               */
    uint64_t bytes_tx;           /* Bytes sent                     */
    uint64_t bytes_rx;           /* Bytes received                 */
} NetDeviceInfo;

/* -- API ---------------------------------------------------------------- */

/* Probe PCI bus for a supported NIC, initialise if found.
   Returns 1 if a NIC was found and initialised, 0 otherwise. */
int net_init(void);

/* Get NIC device info (read-only).
   Returns NULL if no NIC present. */
const NetDeviceInfo *net_get_info(void);

/* Send a raw Ethernet frame.
   `data` must be a complete Ethernet frame (dest + src + type + payload).
   `length` is the total frame length in bytes (14..NET_MAX_PACKET).
   Returns 0 on success, -1 on error. */
int net_send(const void *data, uint16_t length);

/* Poll for a received packet (non-blocking).
   Copies up to `buf_size` bytes into `buf`.
   Returns actual packet length, or 0 if no packet available. */
uint16_t net_recv(void *buf, uint16_t buf_size);

/* Get human-readable MAC address string "XX:XX:XX:XX:XX:XX".
   `out` must be at least 18 bytes. */
void net_mac_str(char *out);

/* Check if the NIC link is up.
   Returns 1 if link detected, 0 otherwise. */
int net_link_up(void);

#endif /* LATERALUS_NET_H */
