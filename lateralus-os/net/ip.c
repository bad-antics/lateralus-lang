/* =======================================================================
 * LateralusOS — IP / ARP / UDP / ICMP / DHCP implementation
 * =======================================================================
 * Minimal but functional IPv4 stack.
 *
 * Copyright (c) 2025-2026 bad-antics. All rights reserved.
 * ======================================================================= */

#include "ip.h"
#include "tcp.h"
#include "../drivers/net.h"
#include "../kernel/heap.h"

/* -- Serial logging (from kernel_stub) ---------------------------------- */
extern void serial_puts(const char *s);
extern void serial_putc(char c);

/* -- Local helpers ------------------------------------------------------ */

static void net_memcpy(void *dst, const void *src, uint64_t n) {
    uint8_t *d = (uint8_t *)dst;
    const uint8_t *s = (const uint8_t *)src;
    while (n--) *d++ = *s++;
}

static void net_memset(void *dst, uint8_t val, uint64_t n) {
    uint8_t *d = (uint8_t *)dst;
    while (n--) *d++ = val;
}

static int net_memcmp(const void *a, const void *b, uint64_t n) {
    const uint8_t *p = (const uint8_t *)a;
    const uint8_t *q = (const uint8_t *)b;
    while (n--) {
        if (*p != *q) return *p - *q;
        p++; q++;
    }
    return 0;
}

/* -- Byte-order helpers (x86 is little-endian, network is big-endian) -- */

static inline uint16_t htons(uint16_t h) {
    return (h >> 8) | (h << 8);
}
static inline uint16_t ntohs(uint16_t n) { return htons(n); }

static inline uint32_t htonl(uint32_t h) {
    return ((h >> 24) & 0xFF) |
           ((h >>  8) & 0xFF00) |
           ((h <<  8) & 0xFF0000) |
           ((h << 24) & 0xFF000000u);
}
static inline uint32_t ntohl(uint32_t n) { return htonl(n); }

/* -- State -------------------------------------------------------------- */

static NetConfig  net_cfg;
static ArpEntry   arp_cache[ARP_CACHE_SIZE];
static UdpBinding udp_binds[UDP_MAX_BINDS];
static uint16_t   ip_id_counter = 1;

/* Broadcast MAC */
static const uint8_t MAC_BCAST[ETH_ALEN] = {0xFF,0xFF,0xFF,0xFF,0xFF,0xFF};

/* Scratch buffer for constructing outgoing frames */
static uint8_t tx_frame[NET_MAX_PACKET];

/* RX buffer for polling */
static uint8_t rx_buf[NET_MAX_PACKET];

/* ICMP ping state */
static volatile int     ping_reply_received = 0;
static volatile uint16_t ping_reply_seq     = 0;
static volatile uint32_t ping_reply_src     = 0;

/* -- Checksum ----------------------------------------------------------- */

static uint16_t ip_checksum(const void *data, uint16_t len) {
    const uint16_t *p = (const uint16_t *)data;
    uint32_t sum = 0;
    while (len > 1) {
        sum += *p++;
        len -= 2;
    }
    if (len == 1) sum += *(const uint8_t *)p;
    while (sum >> 16) sum = (sum & 0xFFFF) + (sum >> 16);
    return (uint16_t)~sum;
}

/* -- IP address utilities ----------------------------------------------- */

static void uint_to_str_local(uint64_t val, char *buf, int bufsz) {
    if (bufsz < 2) return;
    char tmp[20];
    int i = 0;
    if (val == 0) { buf[0] = '0'; buf[1] = '\0'; return; }
    while (val && i < 19) { tmp[i++] = '0' + (val % 10); val /= 10; }
    int j = 0;
    while (i > 0 && j < bufsz - 1) buf[j++] = tmp[--i];
    buf[j] = '\0';
}

void ip_to_str(uint32_t ip, char *out) {
    char tmp[8];
    int pos = 0;
    for (int i = 3; i >= 0; i--) {
        uint_to_str_local((ip >> (i * 8)) & 0xFF, tmp, sizeof(tmp));
        for (int j = 0; tmp[j]; j++) out[pos++] = tmp[j];
        if (i > 0) out[pos++] = '.';
    }
    out[pos] = '\0';
}

uint32_t ip_from_str(const char *s) {
    uint32_t parts[4] = {0};
    int pi = 0;
    while (*s && pi < 4) {
        if (*s >= '0' && *s <= '9') {
            parts[pi] = parts[pi] * 10 + (*s - '0');
        } else if (*s == '.') {
            pi++;
        } else {
            return 0;
        }
        s++;
    }
    if (pi != 3) return 0;
    return IP4(parts[0], parts[1], parts[2], parts[3]);
}

/* -- Ethernet frame helpers --------------------------------------------- */

static void ip_get_mac(uint8_t *out) {
    const NetDeviceInfo *info = net_get_info();
    if (info) net_memcpy(out, info->mac, ETH_ALEN);
    else      net_memset(out, 0, ETH_ALEN);
}

/* Build Ethernet header at the start of tx_frame, return pointer past it */
static uint8_t *eth_build(const uint8_t *dst_mac, uint16_t type) {
    EthHeader *eh = (EthHeader *)tx_frame;
    net_memcpy(eh->dst, dst_mac, ETH_ALEN);
    ip_get_mac(eh->src);
    eh->type = htons(type);
    return tx_frame + ETH_HLEN;
}

/* ========================================================================
 * ARP
 * ======================================================================== */

static void arp_cache_add(uint32_t ip, const uint8_t *mac) {
    /* Check if already cached */
    for (int i = 0; i < ARP_CACHE_SIZE; i++) {
        if (arp_cache[i].valid && arp_cache[i].ip == ip) {
            net_memcpy(arp_cache[i].mac, mac, ETH_ALEN);
            return;
        }
    }
    /* Find free slot */
    for (int i = 0; i < ARP_CACHE_SIZE; i++) {
        if (!arp_cache[i].valid) {
            arp_cache[i].ip    = ip;
            net_memcpy(arp_cache[i].mac, mac, ETH_ALEN);
            arp_cache[i].valid = 1;
            return;
        }
    }
    /* Evict slot 0 (simple LRU stand-in) */
    arp_cache[0].ip = ip;
    net_memcpy(arp_cache[0].mac, mac, ETH_ALEN);
}

int arp_resolve(uint32_t ip, uint8_t *mac_out) {
    for (int i = 0; i < ARP_CACHE_SIZE; i++) {
        if (arp_cache[i].valid && arp_cache[i].ip == ip) {
            net_memcpy(mac_out, arp_cache[i].mac, ETH_ALEN);
            return 1;
        }
    }

    /* Send ARP request */
    uint8_t *p = eth_build(MAC_BCAST, ETH_TYPE_ARP);
    ArpPacket *arp = (ArpPacket *)p;
    arp->htype = htons(1);
    arp->ptype = htons(0x0800);
    arp->hlen  = 6;
    arp->plen  = 4;
    arp->oper  = htons(ARP_OP_REQUEST);
    ip_get_mac(arp->sha);
    uint32_t our_ip_be = htonl(net_cfg.ip);
    net_memcpy(arp->spa, &our_ip_be, 4);
    net_memset(arp->tha, 0, ETH_ALEN);
    uint32_t tgt_be = htonl(ip);
    net_memcpy(arp->tpa, &tgt_be, 4);

    uint16_t frame_len = ETH_HLEN + sizeof(ArpPacket);
    net_send(tx_frame, frame_len);

    serial_puts("[arp] request sent for ");
    char ipstr[16];
    ip_to_str(ip, ipstr);
    serial_puts(ipstr);
    serial_putc('\n');

    return 0;
}

static void arp_handle(const uint8_t *frame, uint16_t len) {
    if (len < ETH_HLEN + sizeof(ArpPacket)) return;
    const ArpPacket *arp = (const ArpPacket *)(frame + ETH_HLEN);

    if (ntohs(arp->htype) != 1 || ntohs(arp->ptype) != 0x0800) return;

    uint32_t sender_ip = ntohl(*(uint32_t *)arp->spa);
    uint32_t target_ip = ntohl(*(uint32_t *)arp->tpa);

    /* Cache sender's MAC */
    arp_cache_add(sender_ip, arp->sha);

    if (ntohs(arp->oper) == ARP_OP_REQUEST && target_ip == net_cfg.ip) {
        /* Send ARP reply */
        uint8_t *p = eth_build(arp->sha, ETH_TYPE_ARP);
        ArpPacket *reply = (ArpPacket *)p;
        reply->htype = htons(1);
        reply->ptype = htons(0x0800);
        reply->hlen  = 6;
        reply->plen  = 4;
        reply->oper  = htons(ARP_OP_REPLY);
        ip_get_mac(reply->sha);
        uint32_t our_be = htonl(net_cfg.ip);
        net_memcpy(reply->spa, &our_be, 4);
        net_memcpy(reply->tha, arp->sha, ETH_ALEN);
        net_memcpy(reply->tpa, arp->spa, 4);

        net_send(tx_frame, ETH_HLEN + sizeof(ArpPacket));
        serial_puts("[arp] replied to request\n");
    }
}

void arp_dump(void) {
    serial_puts("[arp] cache:\n");
    for (int i = 0; i < ARP_CACHE_SIZE; i++) {
        if (!arp_cache[i].valid) continue;
        char ipstr[16];
        ip_to_str(arp_cache[i].ip, ipstr);
        serial_puts("  ");
        serial_puts(ipstr);
        serial_puts(" -> ");
        /* Print MAC */
        const char *hex = "0123456789ABCDEF";
        char mac_str[18];
        for (int j = 0; j < 6; j++) {
            mac_str[j*3]   = hex[(arp_cache[i].mac[j] >> 4) & 0xF];
            mac_str[j*3+1] = hex[arp_cache[i].mac[j] & 0xF];
            mac_str[j*3+2] = (j < 5) ? ':' : '\0';
        }
        mac_str[17] = '\0';
        serial_puts(mac_str);
        serial_putc('\n');
    }
}

/* ========================================================================
 * IPv4
 * ======================================================================== */

int ip_send(uint32_t dst_ip, uint8_t protocol,
            const void *payload, uint16_t payload_len)
{
    if (!net_cfg.configured && protocol != IP_PROTO_UDP) return -1;

    /* Determine next-hop: if on same subnet → dst, else → gateway */
    uint32_t next_hop = dst_ip;
    if (dst_ip != 0xFFFFFFFF) {  /* not broadcast */
        if (net_cfg.configured &&
            (dst_ip & net_cfg.netmask) != (net_cfg.ip & net_cfg.netmask)) {
            next_hop = net_cfg.gateway;
        }
    }

    /* Resolve destination MAC */
    uint8_t dst_mac[ETH_ALEN];
    if (dst_ip == 0xFFFFFFFF) {
        net_memcpy(dst_mac, MAC_BCAST, ETH_ALEN);
    } else {
        if (!arp_resolve(next_hop, dst_mac)) {
            /* ARP request sent, packet dropped (caller should retry) */
            return -1;
        }
    }

    /* Build frame: ETH | IPv4 | payload */
    uint8_t *p = eth_build(dst_mac, ETH_TYPE_IPV4);
    Ipv4Header *ip = (Ipv4Header *)p;
    uint16_t total = sizeof(Ipv4Header) + payload_len;

    ip->ver_ihl    = 0x45;  /* IPv4, IHL=5 (20 bytes) */
    ip->tos        = 0;
    ip->total_len  = htons(total);
    ip->id         = htons(ip_id_counter++);
    ip->flags_frag = 0;
    ip->ttl        = 64;
    ip->protocol   = protocol;
    ip->checksum   = 0;

    uint32_t src_be = htonl(net_cfg.ip);
    uint32_t dst_be = htonl(dst_ip);
    net_memcpy(ip->src, &src_be, 4);
    net_memcpy(ip->dst, &dst_be, 4);

    ip->checksum = ip_checksum(ip, sizeof(Ipv4Header));

    net_memcpy(p + sizeof(Ipv4Header), payload, payload_len);

    uint16_t frame_len = ETH_HLEN + total;
    if (frame_len < 60) frame_len = 60;  /* minimum Ethernet frame */

    return net_send(tx_frame, frame_len);
}

static void ipv4_handle(const uint8_t *frame, uint16_t len);

/* ========================================================================
 * ICMP
 * ======================================================================== */

static void icmp_handle(uint32_t src_ip, const uint8_t *data, uint16_t len) {
    if (len < sizeof(IcmpHeader)) return;
    const IcmpHeader *icmp = (const IcmpHeader *)data;

    if (icmp->type == ICMP_ECHO_REQUEST && icmp->code == 0) {
        /* Send echo reply */
        uint8_t reply_buf[NET_MAX_PACKET];
        IcmpHeader *rh = (IcmpHeader *)reply_buf;
        rh->type     = ICMP_ECHO_REPLY;
        rh->code     = 0;
        rh->checksum = 0;
        rh->id       = icmp->id;
        rh->seq      = icmp->seq;

        /* Copy payload after ICMP header */
        uint16_t payload_len = len - sizeof(IcmpHeader);
        if (payload_len > 0) {
            net_memcpy(reply_buf + sizeof(IcmpHeader),
                       data + sizeof(IcmpHeader), payload_len);
        }

        rh->checksum = ip_checksum(reply_buf, sizeof(IcmpHeader) + payload_len);
        ip_send(src_ip, IP_PROTO_ICMP, reply_buf, sizeof(IcmpHeader) + payload_len);

        serial_puts("[icmp] echo reply sent\n");
    }
    else if (icmp->type == ICMP_ECHO_REPLY) {
        ping_reply_received = 1;
        ping_reply_seq      = ntohs(icmp->seq);
        ping_reply_src      = src_ip;

        serial_puts("[icmp] echo reply received\n");
    }
}

int icmp_ping(uint32_t dst_ip, uint16_t seq) {
    uint8_t buf[sizeof(IcmpHeader) + 32];
    IcmpHeader *icmp = (IcmpHeader *)buf;
    icmp->type     = ICMP_ECHO_REQUEST;
    icmp->code     = 0;
    icmp->checksum = 0;
    icmp->id       = htons(0x4C54);  /* "LT" */
    icmp->seq      = htons(seq);

    /* 32 bytes of payload pattern */
    for (int i = 0; i < 32; i++)
        buf[sizeof(IcmpHeader) + i] = (uint8_t)(i + 0x41);

    icmp->checksum = ip_checksum(buf, sizeof(buf));

    return ip_send(dst_ip, IP_PROTO_ICMP, buf, sizeof(buf));
}

void icmp_ping_reset(void) {
    ping_reply_received = 0;
    ping_reply_seq      = 0;
    ping_reply_src      = 0;
}

int icmp_ping_received(void) {
    return ping_reply_received;
}

/* ========================================================================
 * UDP
 * ======================================================================== */

int udp_bind(uint16_t port, udp_recv_fn callback) {
    for (int i = 0; i < UDP_MAX_BINDS; i++) {
        if (udp_binds[i].port == 0) {
            udp_binds[i].port     = port;
            udp_binds[i].callback = callback;
            return 0;
        }
    }
    return -1;
}

int udp_send(uint32_t dst_ip, uint16_t dst_port, uint16_t src_port,
             const void *payload, uint16_t payload_len)
{
    uint8_t buf[NET_MAX_PACKET];
    UdpHeader *udp = (UdpHeader *)buf;
    uint16_t udp_len = sizeof(UdpHeader) + payload_len;

    udp->src_port = htons(src_port);
    udp->dst_port = htons(dst_port);
    udp->length   = htons(udp_len);
    udp->checksum = 0;  /* optional for IPv4 */

    net_memcpy(buf + sizeof(UdpHeader), payload, payload_len);

    return ip_send(dst_ip, IP_PROTO_UDP, buf, udp_len);
}

static void udp_handle(uint32_t src_ip, const uint8_t *data, uint16_t len) {
    if (len < sizeof(UdpHeader)) return;
    const UdpHeader *udp = (const UdpHeader *)data;
    uint16_t dst_port = ntohs(udp->dst_port);
    uint16_t src_port = ntohs(udp->src_port);
    uint16_t udp_len  = ntohs(udp->length);
    uint16_t payload_len = udp_len - sizeof(UdpHeader);

    if (payload_len > len - sizeof(UdpHeader)) return;

    const uint8_t *payload = data + sizeof(UdpHeader);

    for (int i = 0; i < UDP_MAX_BINDS; i++) {
        if (udp_binds[i].port == dst_port && udp_binds[i].callback) {
            udp_binds[i].callback(src_ip, src_port, payload, payload_len);
            return;
        }
    }
    /* No binding — silently discard */
}

/* ========================================================================
 * DHCP (minimal: DISCOVER → OFFER → REQUEST → ACK)
 * ======================================================================== */

#define DHCP_SERVER_PORT  67
#define DHCP_CLIENT_PORT  68
#define DHCP_MAGIC_COOKIE 0x63825363

#define DHCP_DISCOVER  1
#define DHCP_OFFER     2
#define DHCP_REQUEST   3
#define DHCP_ACK       5

/* Minimal DHCP packet (fixed portion + options) */
typedef struct __attribute__((packed)) {
    uint8_t  op;         /* 1=request, 2=reply */
    uint8_t  htype;      /* 1=Ethernet */
    uint8_t  hlen;       /* 6 */
    uint8_t  hops;
    uint32_t xid;        /* transaction ID */
    uint16_t secs;
    uint16_t flags;
    uint32_t ciaddr;     /* client IP */
    uint32_t yiaddr;     /* "your" IP */
    uint32_t siaddr;     /* server IP */
    uint32_t giaddr;     /* gateway IP */
    uint8_t  chaddr[16]; /* client hardware addr */
    uint8_t  sname[64];  /* server name */
    uint8_t  file[128];  /* boot file */
    uint32_t magic;      /* DHCP magic cookie */
    /* Options follow (variable length) */
} DhcpPacket;

static volatile int dhcp_state = 0; /* 0=idle, 1=discovering, 2=offered, 3=done */
static uint32_t dhcp_offered_ip    = 0;
static uint32_t dhcp_server_ip     = 0;
static uint32_t dhcp_offered_mask  = 0;
static uint32_t dhcp_offered_gw    = 0;
static uint32_t dhcp_offered_dns   = 0;
static uint32_t dhcp_xid           = 0x4C544C00; /* "LTL\0" */

static void dhcp_recv(uint32_t src_ip, uint16_t src_port,
                      const void *payload, uint16_t len)
{
    (void)src_ip; (void)src_port;
    if (len < sizeof(DhcpPacket)) return;
    const DhcpPacket *pkt = (const DhcpPacket *)payload;

    if (pkt->op != 2) return;  /* not a reply */
    if (pkt->xid != htonl(dhcp_xid)) return;  /* not our xid */

    uint32_t offered = ntohl(pkt->yiaddr);

    /* Parse DHCP options */
    const uint8_t *opts = (const uint8_t *)payload + sizeof(DhcpPacket);
    int opts_len = len - sizeof(DhcpPacket);
    int msg_type = 0;
    uint32_t mask = 0, gw = 0, dns = 0, server = 0;

    int i = 0;
    while (i < opts_len) {
        uint8_t opt = opts[i++];
        if (opt == 0xFF) break;  /* end */
        if (opt == 0) continue;  /* pad */
        if (i >= opts_len) break;
        uint8_t olen = opts[i++];
        if (i + olen > opts_len) break;

        switch (opt) {
            case 53:  /* Message type */
                if (olen >= 1) msg_type = opts[i];
                break;
            case 1:   /* Subnet mask */
                if (olen == 4) mask = ntohl(*(uint32_t *)(opts + i));
                break;
            case 3:   /* Router/gateway */
                if (olen >= 4) gw = ntohl(*(uint32_t *)(opts + i));
                break;
            case 6:   /* DNS server */
                if (olen >= 4) dns = ntohl(*(uint32_t *)(opts + i));
                break;
            case 54:  /* Server identifier */
                if (olen == 4) server = ntohl(*(uint32_t *)(opts + i));
                break;
        }
        i += olen;
    }

    if (msg_type == DHCP_OFFER && dhcp_state == 1) {
        dhcp_offered_ip   = offered;
        dhcp_server_ip    = server;
        dhcp_offered_mask = mask;
        dhcp_offered_gw   = gw;
        dhcp_offered_dns  = dns;
        dhcp_state = 2;

        char ipstr[16];
        ip_to_str(offered, ipstr);
        serial_puts("[dhcp] offer received: ");
        serial_puts(ipstr);
        serial_putc('\n');
    }
    else if (msg_type == DHCP_ACK && dhcp_state == 2) {
        dhcp_state = 3;
        serial_puts("[dhcp] ACK received, lease granted\n");
    }
}

static void dhcp_send_discover(void) {
    uint8_t buf[sizeof(DhcpPacket) + 16];
    net_memset(buf, 0, sizeof(buf));
    DhcpPacket *pkt = (DhcpPacket *)buf;

    pkt->op    = 1;
    pkt->htype = 1;
    pkt->hlen  = 6;
    pkt->xid   = htonl(dhcp_xid);
    pkt->flags = htons(0x8000);  /* broadcast */
    pkt->magic = htonl(DHCP_MAGIC_COOKIE);
    ip_get_mac(pkt->chaddr);

    /* Options: type=DISCOVER, end */
    uint8_t *opts = buf + sizeof(DhcpPacket);
    opts[0] = 53; opts[1] = 1; opts[2] = DHCP_DISCOVER;  /* msg type */
    opts[3] = 55; opts[4] = 3; opts[5] = 1; opts[6] = 3; opts[7] = 6; /* param req */
    opts[8] = 0xFF;  /* end */

    udp_send(0xFFFFFFFF, DHCP_SERVER_PORT, DHCP_CLIENT_PORT,
             buf, sizeof(DhcpPacket) + 9);

    serial_puts("[dhcp] DISCOVER sent\n");
}

static void dhcp_send_request(void) {
    uint8_t buf[sizeof(DhcpPacket) + 32];
    net_memset(buf, 0, sizeof(buf));
    DhcpPacket *pkt = (DhcpPacket *)buf;

    pkt->op    = 1;
    pkt->htype = 1;
    pkt->hlen  = 6;
    pkt->xid   = htonl(dhcp_xid);
    pkt->flags = htons(0x8000);
    pkt->magic = htonl(DHCP_MAGIC_COOKIE);
    ip_get_mac(pkt->chaddr);

    /* Options: type=REQUEST, requested IP, server ID, end */
    uint8_t *opts = buf + sizeof(DhcpPacket);
    int pos = 0;
    opts[pos++] = 53; opts[pos++] = 1; opts[pos++] = DHCP_REQUEST;
    opts[pos++] = 50; opts[pos++] = 4;
    uint32_t req_be = htonl(dhcp_offered_ip);
    net_memcpy(opts + pos, &req_be, 4); pos += 4;
    opts[pos++] = 54; opts[pos++] = 4;
    uint32_t srv_be = htonl(dhcp_server_ip);
    net_memcpy(opts + pos, &srv_be, 4); pos += 4;
    opts[pos++] = 0xFF;

    udp_send(0xFFFFFFFF, DHCP_SERVER_PORT, DHCP_CLIENT_PORT,
             buf, sizeof(DhcpPacket) + pos);

    serial_puts("[dhcp] REQUEST sent\n");
}

int dhcp_discover(void) {
    if (!net_get_info() || !net_get_info()->present) return 0;

    /* Temporarily set IP to 0.0.0.0 for DHCP */
    uint32_t old_ip = net_cfg.ip;
    net_cfg.ip = 0;
    net_cfg.configured = 0;

    /* Bind DHCP client port */
    udp_bind(DHCP_CLIENT_PORT, dhcp_recv);

    dhcp_state = 1;
    dhcp_send_discover();

    /* Poll for OFFER (timeout ~5 seconds at 1000 Hz) */
    extern volatile uint64_t tick_count;
    uint64_t deadline = tick_count + 5000;
    while (dhcp_state == 1 && tick_count < deadline) {
        ip_poll();
    }

    if (dhcp_state == 2) {
        /* Got OFFER — send REQUEST */
        dhcp_send_request();
        deadline = tick_count + 5000;
        while (dhcp_state == 2 && tick_count < deadline) {
            ip_poll();
        }
    }

    if (dhcp_state == 3) {
        net_cfg.ip         = dhcp_offered_ip;
        net_cfg.netmask    = dhcp_offered_mask ? dhcp_offered_mask : IP4(255,255,255,0);
        net_cfg.gateway    = dhcp_offered_gw;
        net_cfg.dns        = dhcp_offered_dns;
        net_cfg.configured = 1;

        char ipstr[16];
        ip_to_str(net_cfg.ip, ipstr);
        serial_puts("[dhcp] configured: ");
        serial_puts(ipstr);
        serial_putc('\n');
        dhcp_state = 0;
        return 1;
    }

    /* Failed — restore old IP if any */
    net_cfg.ip = old_ip;
    dhcp_state = 0;
    serial_puts("[dhcp] timeout — no DHCP server found\n");
    return 0;
}

/* ========================================================================
 * IPv4 receive
 * ======================================================================== */

static void ipv4_handle(const uint8_t *frame, uint16_t len) {
    if (len < ETH_HLEN + sizeof(Ipv4Header)) return;
    const Ipv4Header *ip = (const Ipv4Header *)(frame + ETH_HLEN);

    uint8_t ihl = (ip->ver_ihl & 0x0F) * 4;
    if (ihl < 20) return;

    uint16_t total = ntohs(ip->total_len);
    if (total < ihl) return;
    uint16_t payload_len = total - ihl;

    uint32_t dst = ntohl(*(uint32_t *)ip->dst);
    uint32_t src = ntohl(*(uint32_t *)ip->src);

    /* Accept broadcast, our IP, or any IP if unconfigured (for DHCP) */
    if (dst != 0xFFFFFFFF && dst != net_cfg.ip && net_cfg.configured) return;

    const uint8_t *payload = frame + ETH_HLEN + ihl;

    switch (ip->protocol) {
        case IP_PROTO_ICMP:
            icmp_handle(src, payload, payload_len);
            break;
        case IP_PROTO_TCP:
            tcp_recv(src, payload, payload_len);
            break;
        case IP_PROTO_UDP:
            udp_handle(src, payload, payload_len);
            break;
        default:
            break;
    }
}

/* ========================================================================
 * Main poll + init
 * ======================================================================== */

void ip_poll(void) {
    uint16_t len = net_recv(rx_buf, sizeof(rx_buf));
    if (len == 0) return;
    if (len < ETH_HLEN) return;

    const EthHeader *eh = (const EthHeader *)rx_buf;
    uint16_t type = ntohs(eh->type);

    switch (type) {
        case ETH_TYPE_ARP:
            arp_handle(rx_buf, len);
            break;
        case ETH_TYPE_IPV4:
            ipv4_handle(rx_buf, len);
            break;
        default:
            break;
    }
}

void ip_init(void) {
    net_memset(&net_cfg, 0, sizeof(net_cfg));
    net_memset(arp_cache, 0, sizeof(arp_cache));
    net_memset(udp_binds, 0, sizeof(udp_binds));

    serial_puts("[ip] IPv4/ARP/UDP/ICMP stack initialized\n");
}

void ip_set_static(uint32_t ip, uint32_t netmask, uint32_t gateway) {
    net_cfg.ip         = ip;
    net_cfg.netmask    = netmask;
    net_cfg.gateway    = gateway;
    net_cfg.configured = 1;

    char ipstr[16];
    ip_to_str(ip, ipstr);
    serial_puts("[ip] static config: ");
    serial_puts(ipstr);
    serial_putc('\n');
}

const NetConfig *ip_get_config(void) {
    return &net_cfg;
}
