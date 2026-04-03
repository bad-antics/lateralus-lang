/* ═══════════════════════════════════════════════════════════════════════
 * LateralusOS — DNS Resolver
 * ═══════════════════════════════════════════════════════════════════════
 * Minimal DNS stub resolver providing:
 *   - A record (IPv4) queries
 *   - DNS response parsing
 *   - Name cache (16 entries, LRU eviction)
 *   - Blocking resolve with timeout
 *
 * Uses the UDP infrastructure from net/ip.{h,c}.
 *
 * Copyright (c) 2025-2026 bad-antics. All rights reserved.
 * ═══════════════════════════════════════════════════════════════════════ */

#ifndef LATERALUS_DNS_H
#define LATERALUS_DNS_H

#include "../gui/types.h"

/* ── DNS constants ────────────────────────────────────────────────────── */

#define DNS_PORT          53
#define DNS_LOCAL_PORT    10053    /* our ephemeral source port */

#define DNS_TYPE_A        1       /* IPv4 address */
#define DNS_TYPE_AAAA     28      /* IPv6 address (not supported) */
#define DNS_TYPE_CNAME    5
#define DNS_CLASS_IN      1       /* Internet */

#define DNS_FLAG_QR       0x8000  /* response flag */
#define DNS_FLAG_RD       0x0100  /* recursion desired */
#define DNS_FLAG_RA       0x0080  /* recursion available */

#define DNS_RCODE_OK      0
#define DNS_RCODE_NXDOMAIN 3

#define DNS_CACHE_SIZE    16
#define DNS_MAX_NAME      128     /* max hostname length */
#define DNS_TIMEOUT_MS    3000    /* 3-second timeout per query */
#define DNS_MAX_RETRIES   2       /* retry count */

/* ── DNS header (RFC 1035, §4.1.1) ───────────────────────────────────── */

typedef struct __attribute__((packed)) {
    uint16_t id;          /* query ID */
    uint16_t flags;       /* QR, Opcode, AA, TC, RD, RA, RCODE */
    uint16_t qdcount;     /* number of questions */
    uint16_t ancount;     /* number of answers */
    uint16_t nscount;     /* authority records */
    uint16_t arcount;     /* additional records */
} DnsHeader;

/* ── DNS cache entry ──────────────────────────────────────────────────── */

typedef struct {
    char     name[DNS_MAX_NAME];  /* hostname */
    uint32_t ip;                  /* resolved IPv4 (host order) */
    uint32_t ttl;                 /* TTL from response (seconds) */
    uint32_t timestamp;           /* tick count when cached */
    uint8_t  valid;               /* 1 if entry is valid */
} DnsCacheEntry;

/* ── Public API ───────────────────────────────────────────────────────── */

/* Initialise the DNS resolver (call after ip_init) */
void dns_init(void);

/* Resolve a hostname to an IPv4 address (blocking, with timeout).
 * Returns the IPv4 address in host byte order, or 0 on failure.
 * Checks the cache first; sends a DNS query if not cached. */
uint32_t dns_resolve(const char *hostname);

/* Flush the DNS cache */
void dns_cache_flush(void);

/* Print the DNS cache contents to the console */
void dns_cache_dump(void);

/* Get the number of cached DNS entries */
int dns_cache_count(void);

#endif /* LATERALUS_DNS_H */
