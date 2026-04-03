/* ═══════════════════════════════════════════════════════════════════════
 * LateralusOS — TCP Transport Layer
 * ═══════════════════════════════════════════════════════════════════════
 * Minimal TCP implementation over IPv4 providing:
 *   - Connection state machine (RFC 793 simplified)
 *   - Three-way handshake (SYN → SYN+ACK → ACK)
 *   - Sequence / acknowledgment number tracking
 *   - Basic send and receive with 4 KB per-connection buffers
 *   - Graceful close (FIN → ACK) and RST support
 *   - Retransmit timer for SYN and FIN
 *
 * Limitations (research OS scope):
 *   - No window scaling or flow control beyond buffer fullness
 *   - No congestion control (no slow-start / AIMD)
 *   - No out-of-order reassembly (drops OOO segments)
 *   - No urgent pointer support
 *   - Fixed 4 KB receive buffer per connection
 *
 * Copyright (c) 2025-2026 bad-antics. All rights reserved.
 * ═══════════════════════════════════════════════════════════════════════ */

#ifndef LATERALUS_TCP_H
#define LATERALUS_TCP_H

#include "../gui/types.h"

/* ── TCP header (RFC 793 §3.1) ────────────────────────────────────────── */

typedef struct __attribute__((packed)) {
    uint16_t src_port;    /* big-endian */
    uint16_t dst_port;    /* big-endian */
    uint32_t seq_num;     /* big-endian */
    uint32_t ack_num;     /* big-endian */
    uint8_t  data_off;    /* upper 4 bits = offset (in 32-bit words) */
    uint8_t  flags;
    uint16_t window;      /* big-endian */
    uint16_t checksum;    /* big-endian */
    uint16_t urgent;      /* big-endian */
} TcpHeader;

/* ── TCP flags ────────────────────────────────────────────────────────── */

#define TCP_FIN   0x01
#define TCP_SYN   0x02
#define TCP_RST   0x04
#define TCP_PSH   0x08
#define TCP_ACK   0x10
#define TCP_URG   0x20

/* ── TCP connection states (RFC 793 §3.2) ─────────────────────────────── */

#define TCP_STATE_CLOSED       0
#define TCP_STATE_LISTEN       1
#define TCP_STATE_SYN_SENT     2
#define TCP_STATE_SYN_RECEIVED 3
#define TCP_STATE_ESTABLISHED  4
#define TCP_STATE_FIN_WAIT_1   5
#define TCP_STATE_FIN_WAIT_2   6
#define TCP_STATE_CLOSE_WAIT   7
#define TCP_STATE_CLOSING      8
#define TCP_STATE_LAST_ACK     9
#define TCP_STATE_TIME_WAIT   10

/* ── Constants ────────────────────────────────────────────────────────── */

#define TCP_MAX_CONNECTIONS  8
#define TCP_RECV_BUF_SIZE   4096
#define TCP_MSS             1460     /* Max Segment Size (Ethernet MTU - headers) */
#define TCP_WINDOW_SIZE     4096     /* Advertised window */
#define TCP_RETRANSMIT_MS   3000     /* Retransmit timer (ms) */
#define TCP_MAX_RETRIES     5
#define TCP_TIME_WAIT_MS    5000     /* TIME_WAIT duration (shortened for demo) */

/* ── TCP connection block ─────────────────────────────────────────────── */

typedef struct {
    /* Connection identification */
    uint32_t local_ip;
    uint16_t local_port;
    uint32_t remote_ip;
    uint16_t remote_port;

    /* State machine */
    uint8_t  state;

    /* Sequence numbers */
    uint32_t snd_una;     /* oldest unacknowledged seq */
    uint32_t snd_nxt;     /* next seq to send */
    uint32_t snd_iss;     /* initial send seq number */
    uint32_t rcv_nxt;     /* next seq expected */
    uint32_t rcv_irs;     /* initial receive seq number */

    /* Receive buffer (circular) */
    uint8_t  recv_buf[TCP_RECV_BUF_SIZE];
    uint16_t recv_head;   /* read position */
    uint16_t recv_tail;   /* write position */
    uint16_t recv_count;  /* bytes available */

    /* Retransmit / timer */
    uint64_t last_send_tick;
    uint8_t  retries;

    /* Close tracking */
    uint64_t time_wait_tick;  /* when TIME_WAIT started */
} TcpConnection;

/* ── Public API ───────────────────────────────────────────────────────── */

/* Initialize TCP subsystem. Call after ip_init(). */
void tcp_init(void);

/* Process incoming TCP segment.
   Called by IP layer when protocol == 6 (TCP). */
void tcp_recv(uint32_t src_ip, const void *segment, uint16_t seg_len);

/* Periodic tick handler — call from timer or scheduler.
   Handles retransmits and TIME_WAIT cleanup. */
void tcp_tick(void);

/* ── Connection API ─── */

/* Open a TCP connection (active open / connect).
   Returns connection index (0..MAX-1), or -1 on failure.
   This initiates the three-way handshake (non-blocking start). */
int tcp_connect(uint32_t dst_ip, uint16_t dst_port, uint16_t src_port);

/* Start listening on a port (passive open).
   Returns connection index or -1. */
int tcp_listen(uint16_t port);

/* Send data on an established connection.
   Returns bytes queued (may be less than len), or -1 on error. */
int tcp_send(int conn_id, const void *data, uint16_t len);

/* Read received data from connection.
   Returns bytes read, 0 if nothing available, -1 on error/closed. */
int tcp_read(int conn_id, void *buf, uint16_t buf_size);

/* Initiate graceful close (sends FIN).
   Returns 0 on success, -1 on error. */
int tcp_close(int conn_id);

/* Get connection state by index. Returns TCP_STATE_* constant. */
int tcp_get_state(int conn_id);

/* Dump connection table to serial for debugging. */
void tcp_dump(void);

/* Get number of active (non-CLOSED) connections. */
int tcp_active_count(void);

#endif /* LATERALUS_TCP_H */
