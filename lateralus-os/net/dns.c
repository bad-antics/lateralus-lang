/* ═══════════════════════════════════════════════════════════════════════
 * LateralusOS — DNS Resolver Implementation
 * ═══════════════════════════════════════════════════════════════════════
 * Minimal stub resolver:
 *   - Encodes A-record queries per RFC 1035
 *   - Parses responses with pointer compression
 *   - 16-entry name cache
 *   - Blocking resolve with 3-second timeout
 *
 * Copyright (c) 2025-2026 bad-antics. All rights reserved.
 * ═══════════════════════════════════════════════════════════════════════ */

#include "dns.h"
#include "ip.h"
#include "../drivers/net.h"

/* ── Externs ──────────────────────────────────────────────────────────── */
extern void serial_puts(const char *s);
extern void serial_putc(char c);
extern void k_print(const char *s);
extern volatile uint64_t tick_count;

/* ── Local helpers ────────────────────────────────────────────────────── */

static void dns_memcpy(void *dst, const void *src, uint64_t n) {
    uint8_t *d = (uint8_t *)dst;
    const uint8_t *s = (const uint8_t *)src;
    while (n--) *d++ = *s++;
}

static void dns_memset(void *dst, uint8_t val, uint64_t n) {
    uint8_t *d = (uint8_t *)dst;
    while (n--) *d++ = val;
}

static uint64_t dns_strlen(const char *s) {
    uint64_t n = 0;
    while (s[n]) n++;
    return n;
}

static int dns_strcmp(const char *a, const char *b) {
    while (*a && *b && *a == *b) { a++; b++; }
    return (unsigned char)*a - (unsigned char)*b;
}

static void dns_strcpy(char *dst, const char *src) {
    while (*src) *dst++ = *src++;
    *dst = '\0';
}

static char dns_tolower(char c) {
    return (c >= 'A' && c <= 'Z') ? c + 32 : c;
}

static int dns_strcasecmp(const char *a, const char *b) {
    while (*a && *b) {
        char la = dns_tolower(*a), lb = dns_tolower(*b);
        if (la != lb) return la - lb;
        a++; b++;
    }
    return dns_tolower(*a) - dns_tolower(*b);
}

/* ── Byte-order (duplicated from ip.c for compilation independence) ──── */

static inline uint16_t dns_htons(uint16_t h) {
    return (h >> 8) | (h << 8);
}
static inline uint16_t dns_ntohs(uint16_t n) { return dns_htons(n); }

static inline uint32_t dns_htonl(uint32_t h) {
    return ((h >> 24) & 0xFF) |
           ((h >>  8) & 0xFF00) |
           ((h <<  8) & 0xFF0000) |
           ((h << 24) & 0xFF000000u);
}
static inline uint32_t dns_ntohl(uint32_t n) { return dns_htonl(n); }

/* ── Serial logging helpers ───────────────────────────────────────────── */

static void dns_serial_hex16(uint16_t v) {
    const char *hex = "0123456789abcdef";
    serial_putc(hex[(v >> 12) & 0xF]);
    serial_putc(hex[(v >>  8) & 0xF]);
    serial_putc(hex[(v >>  4) & 0xF]);
    serial_putc(hex[ v        & 0xF]);
}

static void dns_serial_u32(uint32_t v) {
    char buf[12];
    int pos = 0;
    if (v == 0) { serial_putc('0'); return; }
    while (v > 0) { buf[pos++] = '0' + (v % 10); v /= 10; }
    for (int i = pos - 1; i >= 0; i--) serial_putc(buf[i]);
}

/* ── State ────────────────────────────────────────────────────────────── */

static DnsCacheEntry dns_cache[DNS_CACHE_SIZE];
static uint16_t      dns_query_id = 0x4C54;  /* "LT" */
static volatile uint32_t dns_reply_ip;        /* result from callback */
static volatile uint32_t dns_reply_ttl;
static volatile int      dns_reply_ready;     /* 1 when answer received */

/* ── DNS name encoding ────────────────────────────────────────────────── */

/* Encode "example.com" → "\x07example\x03com\x00"
 * Returns bytes written, or 0 on error. */
static int dns_encode_name(const char *name, uint8_t *buf, int bufsize) {
    int pos = 0;
    const char *p = name;

    while (*p) {
        /* Find next dot or end */
        const char *dot = p;
        while (*dot && *dot != '.') dot++;

        int label_len = (int)(dot - p);
        if (label_len == 0 || label_len > 63) return 0;
        if (pos + 1 + label_len + 1 > bufsize) return 0;

        buf[pos++] = (uint8_t)label_len;
        for (int i = 0; i < label_len; i++)
            buf[pos++] = (uint8_t)p[i];

        p = *dot ? dot + 1 : dot;
    }

    if (pos + 1 > bufsize) return 0;
    buf[pos++] = 0;  /* root label */
    return pos;
}

/* ── DNS name decoding (with pointer compression) ─────────────────────── */

/* Decode a DNS name from a response packet.
 * pkt/pkt_len: full packet data
 * offset: current position in packet
 * out: output buffer (at least DNS_MAX_NAME bytes)
 * Returns the number of bytes consumed from the original offset,
 * or 0 on error. */
static int dns_decode_name(const uint8_t *pkt, int pkt_len,
                           int offset, char *out, int outsize) {
    int out_pos = 0;
    int consumed = 0;
    int jumped = 0;
    int orig_offset = offset;
    int max_jumps = 16;  /* prevent infinite loops */

    while (offset < pkt_len && max_jumps > 0) {
        uint8_t len = pkt[offset];

        if (len == 0) {
            /* End of name */
            if (!jumped) consumed = offset - orig_offset + 1;
            break;
        }

        if ((len & 0xC0) == 0xC0) {
            /* Pointer compression */
            if (offset + 1 >= pkt_len) return 0;
            int ptr = ((len & 0x3F) << 8) | pkt[offset + 1];
            if (!jumped) consumed = offset - orig_offset + 2;
            offset = ptr;
            jumped = 1;
            max_jumps--;
            continue;
        }

        /* Regular label */
        if (len > 63) return 0;
        offset++;
        if (offset + len > pkt_len) return 0;

        if (out_pos > 0 && out_pos < outsize - 1)
            out[out_pos++] = '.';

        for (int i = 0; i < len && out_pos < outsize - 1; i++)
            out[out_pos++] = (char)pkt[offset + i];

        offset += len;
    }

    out[out_pos] = '\0';
    return consumed ? consumed : (offset - orig_offset + 1);
}

/* ── DNS cache ────────────────────────────────────────────────────────── */

static DnsCacheEntry *dns_cache_lookup(const char *name) {
    for (int i = 0; i < DNS_CACHE_SIZE; i++) {
        if (dns_cache[i].valid && dns_strcasecmp(dns_cache[i].name, name) == 0) {
            /* Check TTL expiry (tick_count is ms, TTL is seconds) */
            uint64_t elapsed_s = (tick_count - dns_cache[i].timestamp) / 1000;
            if (dns_cache[i].ttl > 0 && elapsed_s >= dns_cache[i].ttl) {
                dns_cache[i].valid = 0;  /* expired */
                return (DnsCacheEntry *)0;
            }
            return &dns_cache[i];
        }
    }
    return (DnsCacheEntry *)0;
}

static void dns_cache_add(const char *name, uint32_t ip, uint32_t ttl) {
    /* Find empty slot */
    for (int i = 0; i < DNS_CACHE_SIZE; i++) {
        if (!dns_cache[i].valid) {
            dns_strcpy(dns_cache[i].name, name);
            dns_cache[i].ip        = ip;
            dns_cache[i].ttl       = ttl;
            dns_cache[i].timestamp = (uint32_t)tick_count;
            dns_cache[i].valid     = 1;
            return;
        }
    }
    /* Evict slot 0 (simple LRU approximation) */
    dns_strcpy(dns_cache[0].name, name);
    dns_cache[0].ip        = ip;
    dns_cache[0].ttl       = ttl;
    dns_cache[0].timestamp = (uint32_t)tick_count;
    dns_cache[0].valid     = 1;
}

/* ── DNS response callback (registered with udp_bind) ─────────────────── */

static void dns_recv(uint32_t src_ip, uint16_t src_port,
                     const void *payload, uint16_t len) {
    (void)src_ip;
    (void)src_port;

    if (len < sizeof(DnsHeader)) return;

    const uint8_t *pkt = (const uint8_t *)payload;
    const DnsHeader *hdr = (const DnsHeader *)pkt;

    /* Verify it's a response to our query */
    uint16_t flags = dns_ntohs(hdr->flags);
    if (!(flags & DNS_FLAG_QR)) return;  /* not a response */

    uint16_t id = dns_ntohs(hdr->id);
    if (id != dns_query_id) return;  /* wrong ID */

    uint16_t rcode = flags & 0x000F;
    uint16_t ancount = dns_ntohs(hdr->ancount);
    uint16_t qdcount = dns_ntohs(hdr->qdcount);

    serial_puts("[dns] response: rcode=");
    dns_serial_u32(rcode);
    serial_puts(" answers=");
    dns_serial_u32(ancount);
    serial_putc('\n');

    if (rcode != DNS_RCODE_OK || ancount == 0) {
        dns_reply_ip = 0;
        dns_reply_ready = 1;
        return;
    }

    /* Skip past the question section */
    int offset = sizeof(DnsHeader);
    for (uint16_t q = 0; q < qdcount; q++) {
        /* Skip the QNAME */
        char tmpname[DNS_MAX_NAME];
        int consumed = dns_decode_name(pkt, len, offset, tmpname, sizeof(tmpname));
        if (consumed == 0) return;
        offset += consumed;
        offset += 4;  /* skip QTYPE (2) + QCLASS (2) */
        if (offset > len) return;
    }

    /* Parse answer records — look for the first A record */
    for (uint16_t a = 0; a < ancount; a++) {
        if (offset >= len) break;

        /* Decode the name in the answer */
        char aname[DNS_MAX_NAME];
        int consumed = dns_decode_name(pkt, len, offset, aname, sizeof(aname));
        if (consumed == 0) break;
        offset += consumed;

        if (offset + 10 > len) break;  /* TYPE(2) + CLASS(2) + TTL(4) + RDLENGTH(2) = 10 */

        uint16_t atype  = dns_ntohs(*(uint16_t *)(pkt + offset)); offset += 2;
        uint16_t aclass = dns_ntohs(*(uint16_t *)(pkt + offset)); offset += 2;
        uint32_t attl   = dns_ntohl(*(uint32_t *)(pkt + offset)); offset += 4;
        uint16_t rdlen  = dns_ntohs(*(uint16_t *)(pkt + offset)); offset += 2;
        (void)aclass;

        if (offset + rdlen > len) break;

        if (atype == DNS_TYPE_A && rdlen == 4) {
            /* IPv4 address — big-endian in packet, convert to host order */
            uint32_t ip = ((uint32_t)pkt[offset] << 24) |
                          ((uint32_t)pkt[offset+1] << 16) |
                          ((uint32_t)pkt[offset+2] << 8) |
                          ((uint32_t)pkt[offset+3]);

            char ipstr[16];
            ip_to_str(ip, ipstr);
            serial_puts("[dns] A record: ");
            serial_puts(aname);
            serial_puts(" → ");
            serial_puts(ipstr);
            serial_puts(" ttl=");
            dns_serial_u32(attl);
            serial_putc('\n');

            dns_reply_ip  = ip;
            dns_reply_ttl = attl;
            dns_reply_ready = 1;
            return;
        }

        /* Skip RDATA for non-A records */
        offset += rdlen;
    }

    /* No A record found */
    dns_reply_ip = 0;
    dns_reply_ready = 1;
}

/* ── Build and send a DNS query ───────────────────────────────────────── */

static int dns_send_query(const char *hostname) {
    const NetConfig *cfg = ip_get_config();
    if (!cfg || !cfg->configured || cfg->dns == 0) {
        serial_puts("[dns] error: no DNS server configured\n");
        return -1;
    }

    /* Build the query packet */
    uint8_t pkt[512];
    dns_memset(pkt, 0, sizeof(pkt));

    DnsHeader *hdr = (DnsHeader *)pkt;
    dns_query_id++;
    hdr->id      = dns_htons(dns_query_id);
    hdr->flags   = dns_htons(DNS_FLAG_RD);  /* recursion desired */
    hdr->qdcount = dns_htons(1);
    hdr->ancount = 0;
    hdr->nscount = 0;
    hdr->arcount = 0;

    int offset = sizeof(DnsHeader);

    /* Encode the hostname as DNS QNAME */
    int name_len = dns_encode_name(hostname, pkt + offset, (int)sizeof(pkt) - offset - 4);
    if (name_len == 0) {
        serial_puts("[dns] error: invalid hostname\n");
        return -1;
    }
    offset += name_len;

    /* QTYPE = A (1), QCLASS = IN (1) */
    *(uint16_t *)(pkt + offset) = dns_htons(DNS_TYPE_A);   offset += 2;
    *(uint16_t *)(pkt + offset) = dns_htons(DNS_CLASS_IN); offset += 2;

    serial_puts("[dns] query: ");
    serial_puts(hostname);
    serial_puts(" → ");
    char dnsstr[16];
    ip_to_str(cfg->dns, dnsstr);
    serial_puts(dnsstr);
    serial_putc('\n');

    /* Send via UDP */
    return udp_send(cfg->dns, DNS_PORT, DNS_LOCAL_PORT,
                    pkt, (uint16_t)offset);
}

/* ── Public API ───────────────────────────────────────────────────────── */

void dns_init(void) {
    dns_memset(dns_cache, 0, sizeof(dns_cache));
    dns_reply_ready = 0;
    dns_reply_ip    = 0;

    /* Register UDP callback for DNS responses */
    if (udp_bind(DNS_LOCAL_PORT, dns_recv) < 0) {
        serial_puts("[dns] warning: could not bind UDP port\n");
    }

    serial_puts("[dns] resolver initialized\n");
}

uint32_t dns_resolve(const char *hostname) {
    if (!hostname || hostname[0] == '\0') return 0;

    /* Check if it's already an IP address (dotted decimal) */
    uint32_t direct_ip = ip_from_str(hostname);
    if (direct_ip) return direct_ip;

    /* Check cache */
    DnsCacheEntry *cached = dns_cache_lookup(hostname);
    if (cached) {
        serial_puts("[dns] cache hit: ");
        serial_puts(hostname);
        serial_putc('\n');
        return cached->ip;
    }

    /* Send DNS query with retries */
    for (int attempt = 0; attempt <= DNS_MAX_RETRIES; attempt++) {
        dns_reply_ready = 0;
        dns_reply_ip    = 0;
        dns_reply_ttl   = 0;

        if (dns_send_query(hostname) < 0) return 0;

        /* Blocking wait with timeout */
        uint64_t deadline = tick_count + DNS_TIMEOUT_MS;
        while (!dns_reply_ready && tick_count < deadline) {
            ip_poll();  /* process incoming packets */
        }

        if (dns_reply_ready && dns_reply_ip != 0) {
            /* Cache the result */
            uint32_t ttl = dns_reply_ttl;
            if (ttl == 0) ttl = 300;   /* default 5 minutes */
            if (ttl > 86400) ttl = 86400;  /* cap at 24 hours */
            dns_cache_add(hostname, dns_reply_ip, ttl);
            return dns_reply_ip;
        }

        if (dns_reply_ready && dns_reply_ip == 0) {
            /* Got NXDOMAIN or no A record — don't retry */
            serial_puts("[dns] NXDOMAIN: ");
            serial_puts(hostname);
            serial_putc('\n');
            return 0;
        }

        serial_puts("[dns] timeout, retrying...\n");
    }

    serial_puts("[dns] failed to resolve: ");
    serial_puts(hostname);
    serial_putc('\n');
    return 0;
}

void dns_cache_flush(void) {
    dns_memset(dns_cache, 0, sizeof(dns_cache));
    serial_puts("[dns] cache flushed\n");
}

void dns_cache_dump(void) {
    k_print("DNS Cache:\n");
    int found = 0;
    for (int i = 0; i < DNS_CACHE_SIZE; i++) {
        if (!dns_cache[i].valid) continue;
        found++;

        char ipstr[16];
        ip_to_str(dns_cache[i].ip, ipstr);

        k_print("  ");
        k_print(dns_cache[i].name);
        k_print(" → ");
        k_print(ipstr);
        k_print(" (ttl=");

        /* Print TTL remaining */
        uint64_t elapsed_s = (tick_count - dns_cache[i].timestamp) / 1000;
        uint32_t remaining = 0;
        if (dns_cache[i].ttl > elapsed_s)
            remaining = dns_cache[i].ttl - (uint32_t)elapsed_s;

        char buf[12];
        int pos = 0;
        uint32_t v = remaining;
        if (v == 0) { buf[pos++] = '0'; }
        else { while (v > 0) { buf[pos++] = '0' + (v % 10); v /= 10; } }
        buf[pos] = '\0';
        /* reverse */
        for (int l = 0, r = pos - 1; l < r; l++, r--) {
            char t = buf[l]; buf[l] = buf[r]; buf[r] = t;
        }
        k_print(buf);
        k_print("s)\n");
    }
    if (!found) k_print("  (empty)\n");
}

int dns_cache_count(void) {
    int count = 0;
    for (int i = 0; i < DNS_CACHE_SIZE; i++) {
        if (dns_cache[i].valid) count++;
    }
    return count;
}
