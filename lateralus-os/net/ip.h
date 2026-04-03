/* ═══════════════════════════════════════════════════════════════════════
 * LateralusOS — IP / ARP / UDP Network Stack
 * ═══════════════════════════════════════════════════════════════════════
 * Minimal network stack providing:
 *   - ARP request/reply (IPv4-over-Ethernet)
 *   - IPv4 send/receive with checksum
 *   - UDP send/receive (port-based demux)
 *   - ICMP Echo (ping) reply
 *   - DHCP client (basic: DISCOVER → OFFER → REQUEST → ACK)
 *
 * Copyright (c) 2025-2026 bad-antics. All rights reserved.
 * ═══════════════════════════════════════════════════════════════════════ */

#ifndef LATERALUS_IP_H
#define LATERALUS_IP_H

#include "../gui/types.h"

/* ── Ethernet ─────────────────────────────────────────────────────────── */

#define ETH_ALEN        6
#define ETH_HLEN        14
#define ETH_TYPE_ARP    0x0806
#define ETH_TYPE_IPV4   0x0800

typedef struct __attribute__((packed)) {
    uint8_t  dst[ETH_ALEN];
    uint8_t  src[ETH_ALEN];
    uint16_t type;        /* big-endian */
} EthHeader;

/* ── ARP ──────────────────────────────────────────────────────────────── */

#define ARP_OP_REQUEST  1
#define ARP_OP_REPLY    2

#define ARP_CACHE_SIZE  16

typedef struct __attribute__((packed)) {
    uint16_t htype;       /* hardware type (1 = Ethernet) */
    uint16_t ptype;       /* protocol type (0x0800 = IPv4) */
    uint8_t  hlen;        /* hardware addr length (6) */
    uint8_t  plen;        /* protocol addr length (4) */
    uint16_t oper;        /* operation (1=request, 2=reply) */
    uint8_t  sha[ETH_ALEN]; /* sender hardware addr */
    uint8_t  spa[4];      /* sender protocol addr */
    uint8_t  tha[ETH_ALEN]; /* target hardware addr */
    uint8_t  tpa[4];      /* target protocol addr */
} ArpPacket;

typedef struct {
    uint32_t ip;
    uint8_t  mac[ETH_ALEN];
    uint8_t  valid;
} ArpEntry;

/* ── IPv4 ─────────────────────────────────────────────────────────────── */

#define IP_PROTO_ICMP   1
#define IP_PROTO_TCP    6
#define IP_PROTO_UDP    17

typedef struct __attribute__((packed)) {
    uint8_t  ver_ihl;     /* version (4) | IHL (5 = 20 bytes) */
    uint8_t  tos;
    uint16_t total_len;   /* big-endian */
    uint16_t id;
    uint16_t flags_frag;
    uint8_t  ttl;
    uint8_t  protocol;
    uint16_t checksum;    /* big-endian */
    uint8_t  src[4];
    uint8_t  dst[4];
} Ipv4Header;

/* ── ICMP ─────────────────────────────────────────────────────────────── */

#define ICMP_ECHO_REPLY   0
#define ICMP_ECHO_REQUEST 8

typedef struct __attribute__((packed)) {
    uint8_t  type;
    uint8_t  code;
    uint16_t checksum;
    uint16_t id;
    uint16_t seq;
} IcmpHeader;

/* ── UDP ──────────────────────────────────────────────────────────────── */

typedef struct __attribute__((packed)) {
    uint16_t src_port;    /* big-endian */
    uint16_t dst_port;    /* big-endian */
    uint16_t length;      /* big-endian, header + payload */
    uint16_t checksum;    /* big-endian, 0 = not computed */
} UdpHeader;

/* ── UDP receive callback ─────────────────────────────────────────────── */

/* Callback: (src_ip, src_port, payload, payload_len) */
typedef void (*udp_recv_fn)(uint32_t src_ip, uint16_t src_port,
                            const void *payload, uint16_t len);

#define UDP_MAX_BINDS  8

typedef struct {
    uint16_t   port;      /* local port (host byte order) */
    udp_recv_fn callback;
} UdpBinding;

/* ── Network config ───────────────────────────────────────────────────── */

typedef struct {
    uint32_t ip;          /* our IPv4 address (host order) */
    uint32_t netmask;     /* subnet mask (host order) */
    uint32_t gateway;     /* default gateway (host order) */
    uint32_t dns;         /* DNS server (host order) */
    uint8_t  configured;  /* 1 if we have a valid IP */
} NetConfig;

/* ── Public API ───────────────────────────────────────────────────────── */

/* Initialise the IP stack (call after net_init) */
void ip_init(void);

/* Process one incoming packet (call from poll loop or IRQ handler) */
void ip_poll(void);

/* Get current network configuration */
const NetConfig *ip_get_config(void);

/* Manually set a static IP configuration */
void ip_set_static(uint32_t ip, uint32_t netmask, uint32_t gateway);

/* ── ARP ──────── */

/* Look up MAC for an IP address. Returns 1 if found, 0 if not cached.
   If not cached, sends an ARP request. */
int arp_resolve(uint32_t ip, uint8_t *mac_out);

/* Print the ARP cache to the console */
void arp_dump(void);

/* ── IP ───────── */

/* Send an IPv4 packet. Handles ARP resolution for next-hop.
   Returns 0 on success, -1 on error. */
int ip_send(uint32_t dst_ip, uint8_t protocol,
            const void *payload, uint16_t payload_len);

/* ── UDP ──────── */

/* Bind a UDP port to a callback function.
   Returns 0 on success, -1 if table full. */
int udp_bind(uint16_t port, udp_recv_fn callback);

/* Send a UDP datagram.
   Returns 0 on success, -1 on error. */
int udp_send(uint32_t dst_ip, uint16_t dst_port, uint16_t src_port,
             const void *payload, uint16_t payload_len);

/* ── ICMP ─────── */

/* Send an ICMP echo request (ping).
   Returns 0 on success, -1 on error. */
int icmp_ping(uint32_t dst_ip, uint16_t seq);

/* Reset the ping reply state (call before sending a ping) */
void icmp_ping_reset(void);

/* Check if a ping reply was received.
   Returns 1 if reply received since last reset, 0 otherwise. */
int icmp_ping_received(void);

/* ── DHCP ─────── */

/* Start a DHCP discover/request cycle (blocking, with timeout).
   Returns 1 on success, 0 on timeout. */
int dhcp_discover(void);

/* ── Utilities ─── */

/* Convert 4-byte IP to dotted string (out must be >= 16 bytes) */
void ip_to_str(uint32_t ip, char *out);

/* Parse dotted IP string to uint32_t (host order). Returns 0 on error. */
uint32_t ip_from_str(const char *s);

/* Make IP from 4 octets (host order) */
static inline uint32_t IP4(uint8_t a, uint8_t b, uint8_t c, uint8_t d) {
    return ((uint32_t)a << 24) | ((uint32_t)b << 16) | ((uint32_t)c << 8) | d;
}

#endif /* LATERALUS_IP_H */
