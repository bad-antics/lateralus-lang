/* ═══════════════════════════════════════════════════════════════════════
 * LateralusOS — TCP Transport Layer Implementation
 * ═══════════════════════════════════════════════════════════════════════
 * Implements the TCP state machine per RFC 793 (simplified).
 * Built on top of the IPv4 stack in net/ip.c.
 *
 * Copyright (c) 2025-2026 bad-antics. All rights reserved.
 * ═══════════════════════════════════════════════════════════════════════ */

#include "tcp.h"
#include "ip.h"

/* ── External symbols ─────────────────────────────────────────────────── */

extern void  serial_puts(const char *s);
extern volatile uint64_t tick_count;

/* ── Local helpers ────────────────────────────────────────────────────── */

static void tcp_memcpy(void *dst, const void *src, uint32_t n) {
    uint8_t *d = (uint8_t *)dst;
    const uint8_t *s = (const uint8_t *)src;
    while (n--) *d++ = *s++;
}

static void tcp_memset(void *dst, uint8_t val, uint32_t n) {
    uint8_t *d = (uint8_t *)dst;
    while (n--) *d++ = val;
}

/* Byte-order helpers (duplicated for compilation independence) */
static inline uint16_t tcp_htons(uint16_t x) {
    return (uint16_t)((x >> 8) | (x << 8));
}
static inline uint16_t tcp_ntohs(uint16_t x) { return tcp_htons(x); }

static inline uint32_t tcp_htonl(uint32_t x) {
    return ((x >> 24) & 0xFF) |
           ((x >>  8) & 0xFF00) |
           ((x <<  8) & 0xFF0000) |
           ((x << 24) & 0xFF000000u);
}
static inline uint32_t tcp_ntohl(uint32_t x) { return tcp_htonl(x); }

/* Serial output helpers */
static void tcp_serial_u32(uint32_t val) {
    if (val == 0) { serial_puts("0"); return; }
    char buf[12]; int p = 0;
    char rev[12]; int rp = 0;
    while (val > 0 && rp < 11) { rev[rp++] = '0' + (val % 10); val /= 10; }
    while (rp > 0) buf[p++] = rev[--rp];
    buf[p] = '\0';
    serial_puts(buf);
}

static void tcp_serial_hex16(uint16_t val) {
    char buf[8]; int i;
    const char *hex = "0123456789abcdef";
    buf[0] = '0'; buf[1] = 'x';
    for (i = 0; i < 4; i++) buf[2+i] = hex[(val >> (12 - 4*i)) & 0xF];
    buf[6] = '\0';
    serial_puts(buf);
}

/* ── Connection pool ──────────────────────────────────────────────────── */

static TcpConnection conns[TCP_MAX_CONNECTIONS];
static uint32_t tcp_seq_seed = 0;  /* simple ISN generator */

/* Generate an initial sequence number (simple, not cryptographic) */
static uint32_t tcp_gen_isn(void) {
    tcp_seq_seed += (uint32_t)tick_count * 1103515245u + 12345u;
    return tcp_seq_seed;
}

/* Find a connection matching the 4-tuple (or partial for LISTEN) */
static int tcp_find_conn(uint32_t local_ip, uint16_t local_port,
                         uint32_t remote_ip, uint16_t remote_port) {
    /* First: exact 4-tuple match */
    for (int i = 0; i < TCP_MAX_CONNECTIONS; i++) {
        if (conns[i].state == TCP_STATE_CLOSED) continue;
        if (conns[i].local_port == local_port &&
            conns[i].remote_port == remote_port &&
            conns[i].remote_ip == remote_ip) {
            return i;
        }
    }
    /* Second: LISTEN match (wildcard remote) */
    for (int i = 0; i < TCP_MAX_CONNECTIONS; i++) {
        if (conns[i].state == TCP_STATE_LISTEN &&
            conns[i].local_port == local_port) {
            return i;
        }
    }
    (void)local_ip;
    return -1;
}

/* Find a free connection slot */
static int tcp_alloc_conn(void) {
    for (int i = 0; i < TCP_MAX_CONNECTIONS; i++) {
        if (conns[i].state == TCP_STATE_CLOSED) return i;
    }
    return -1;
}

/* ── TCP checksum ─────────────────────────────────────────────────────── */

/* TCP checksum over pseudo-header + TCP header + data */
static uint16_t tcp_checksum(uint32_t src_ip, uint32_t dst_ip,
                             const void *tcp_seg, uint16_t tcp_len) {
    uint32_t sum = 0;

    /* Pseudo-header */
    uint32_t src_be = tcp_htonl(src_ip);
    uint32_t dst_be = tcp_htonl(dst_ip);
    sum += (src_be >> 16) & 0xFFFF;
    sum += src_be & 0xFFFF;
    sum += (dst_be >> 16) & 0xFFFF;
    sum += dst_be & 0xFFFF;
    sum += tcp_htons(6);           /* protocol = TCP */
    sum += tcp_htons(tcp_len);

    /* TCP header + data */
    const uint16_t *p = (const uint16_t *)tcp_seg;
    uint16_t remaining = tcp_len;
    while (remaining > 1) {
        sum += *p++;
        remaining -= 2;
    }
    if (remaining == 1) {
        uint8_t last = *(const uint8_t *)p;
        sum += (uint16_t)last;
    }

    /* Fold */
    while (sum >> 16)
        sum = (sum & 0xFFFF) + (sum >> 16);

    return (uint16_t)~sum;
}

/* ── Send a TCP segment ───────────────────────────────────────────────── */

static int tcp_send_segment(int conn_id, uint8_t flags,
                            const void *data, uint16_t data_len) {
    TcpConnection *c = &conns[conn_id];
    const NetConfig *cfg = ip_get_config();
    if (!cfg || !cfg->configured) return -1;

    /* Build TCP segment: header + payload */
    uint16_t seg_len = sizeof(TcpHeader) + data_len;
    uint8_t seg_buf[sizeof(TcpHeader) + TCP_MSS];
    if (seg_len > sizeof(seg_buf)) return -1;

    tcp_memset(seg_buf, 0, seg_len);
    TcpHeader *hdr = (TcpHeader *)seg_buf;

    hdr->src_port = tcp_htons(c->local_port);
    hdr->dst_port = tcp_htons(c->remote_port);
    hdr->seq_num  = tcp_htonl(c->snd_nxt);
    hdr->ack_num  = (flags & TCP_ACK) ? tcp_htonl(c->rcv_nxt) : 0;
    hdr->data_off = (sizeof(TcpHeader) / 4) << 4;  /* 5 words = 20 bytes */
    hdr->flags    = flags;
    hdr->window   = tcp_htons(TCP_WINDOW_SIZE - c->recv_count);
    hdr->checksum = 0;
    hdr->urgent   = 0;

    /* Copy payload */
    if (data && data_len > 0) {
        tcp_memcpy(seg_buf + sizeof(TcpHeader), data, data_len);
    }

    /* Compute checksum */
    hdr->checksum = tcp_checksum(cfg->ip, c->remote_ip, seg_buf, seg_len);

    /* Advance SND.NXT */
    c->snd_nxt += data_len;
    if (flags & (TCP_SYN | TCP_FIN)) c->snd_nxt++;  /* SYN/FIN consume 1 seq */

    c->last_send_tick = tick_count;

    /* Send via IP layer (protocol 6 = TCP) */
    return ip_send(c->remote_ip, 6, seg_buf, seg_len);
}

/* ── Receive buffer helpers ───────────────────────────────────────────── */

static int recv_buf_write(TcpConnection *c, const uint8_t *data, uint16_t len) {
    uint16_t written = 0;
    while (written < len && c->recv_count < TCP_RECV_BUF_SIZE) {
        c->recv_buf[c->recv_tail] = data[written++];
        c->recv_tail = (c->recv_tail + 1) % TCP_RECV_BUF_SIZE;
        c->recv_count++;
    }
    return written;
}

static int recv_buf_read(TcpConnection *c, uint8_t *buf, uint16_t buf_size) {
    uint16_t read = 0;
    while (read < buf_size && c->recv_count > 0) {
        buf[read++] = c->recv_buf[c->recv_head];
        c->recv_head = (c->recv_head + 1) % TCP_RECV_BUF_SIZE;
        c->recv_count--;
    }
    return read;
}

/* ── State name for debugging ─────────────────────────────────────────── */

static const char *tcp_state_name(int state) {
    switch (state) {
    case TCP_STATE_CLOSED:       return "CLOSED";
    case TCP_STATE_LISTEN:       return "LISTEN";
    case TCP_STATE_SYN_SENT:     return "SYN_SENT";
    case TCP_STATE_SYN_RECEIVED: return "SYN_RCVD";
    case TCP_STATE_ESTABLISHED:  return "ESTAB";
    case TCP_STATE_FIN_WAIT_1:   return "FIN_WAIT1";
    case TCP_STATE_FIN_WAIT_2:   return "FIN_WAIT2";
    case TCP_STATE_CLOSE_WAIT:   return "CLOSE_WAIT";
    case TCP_STATE_CLOSING:      return "CLOSING";
    case TCP_STATE_LAST_ACK:     return "LAST_ACK";
    case TCP_STATE_TIME_WAIT:    return "TIME_WAIT";
    default:                     return "???";
    }
}

/* ═══════════════════════════════════════════════════════════════════════
 * Public API
 * ═══════════════════════════════════════════════════════════════════════ */

void tcp_init(void) {
    tcp_memset(conns, 0, sizeof(conns));
    for (int i = 0; i < TCP_MAX_CONNECTIONS; i++) {
        conns[i].state = TCP_STATE_CLOSED;
    }
    tcp_seq_seed = (uint32_t)(tick_count * 6364136223846793005ULL + 1);
    serial_puts("[tcp] TCP transport initialized (");
    tcp_serial_u32(TCP_MAX_CONNECTIONS);
    serial_puts(" slots, ");
    tcp_serial_u32(TCP_RECV_BUF_SIZE);
    serial_puts("B rx buffer)\n");
}

/* ── tcp_recv: process incoming TCP segment ───────────────────────────── */

void tcp_recv(uint32_t src_ip, const void *segment, uint16_t seg_len) {
    if (seg_len < sizeof(TcpHeader)) return;

    const TcpHeader *hdr = (const TcpHeader *)segment;
    uint16_t src_port = tcp_ntohs(hdr->src_port);
    uint16_t dst_port = tcp_ntohs(hdr->dst_port);
    uint32_t seq      = tcp_ntohl(hdr->seq_num);
    uint32_t ack      = tcp_ntohl(hdr->ack_num);
    uint8_t  flags    = hdr->flags;
    uint16_t hdr_len  = (hdr->data_off >> 4) * 4;

    if (hdr_len < sizeof(TcpHeader) || hdr_len > seg_len) return;

    const uint8_t *payload     = (const uint8_t *)segment + hdr_len;
    uint16_t       payload_len = seg_len - hdr_len;

    const NetConfig *cfg = ip_get_config();
    uint32_t local_ip = cfg ? cfg->ip : 0;

    int ci = tcp_find_conn(local_ip, dst_port, src_ip, src_port);

    /* ── RST handling ──────────────────────────────────────────── */
    if (flags & TCP_RST) {
        if (ci >= 0 && conns[ci].state != TCP_STATE_CLOSED) {
            serial_puts("[tcp] RST received, conn ");
            tcp_serial_u32(ci);
            serial_puts(" → CLOSED\n");
            conns[ci].state = TCP_STATE_CLOSED;
        }
        return;
    }

    /* ── No matching connection ────────────────────────────────── */
    if (ci < 0) {
        /* Send RST for unexpected segments (unless it's already a RST) */
        /* We'd need a temp connection to send RST — skip for now */
        return;
    }

    TcpConnection *c = &conns[ci];

    /* ── State machine ─────────────────────────────────────────── */
    switch (c->state) {

    case TCP_STATE_LISTEN:
        if (flags & TCP_SYN) {
            /* Incoming connection — complete handshake */
            c->remote_ip   = src_ip;
            c->remote_port = src_port;
            c->rcv_irs     = seq;
            c->rcv_nxt     = seq + 1;
            c->snd_iss     = tcp_gen_isn();
            c->snd_nxt     = c->snd_iss;
            c->snd_una     = c->snd_iss;
            c->state       = TCP_STATE_SYN_RECEIVED;
            c->retries     = 0;

            serial_puts("[tcp] SYN received on :");
            tcp_serial_u32(dst_port);
            serial_puts(" from ");
            tcp_serial_u32(src_ip);
            serial_puts(":");
            tcp_serial_u32(src_port);
            serial_puts("\n");

            /* Send SYN+ACK */
            tcp_send_segment(ci, TCP_SYN | TCP_ACK, 0, 0);
        }
        break;

    case TCP_STATE_SYN_SENT:
        if ((flags & (TCP_SYN | TCP_ACK)) == (TCP_SYN | TCP_ACK)) {
            /* Server responded to our SYN */
            if (ack == c->snd_nxt) {
                c->rcv_irs = seq;
                c->rcv_nxt = seq + 1;
                c->snd_una = ack;
                c->state   = TCP_STATE_ESTABLISHED;
                c->retries = 0;

                serial_puts("[tcp] conn ");
                tcp_serial_u32(ci);
                serial_puts(" ESTABLISHED\n");

                /* Send ACK */
                tcp_send_segment(ci, TCP_ACK, 0, 0);
            }
        } else if (flags & TCP_SYN) {
            /* Simultaneous open — send SYN+ACK */
            c->rcv_irs = seq;
            c->rcv_nxt = seq + 1;
            c->state   = TCP_STATE_SYN_RECEIVED;
            tcp_send_segment(ci, TCP_SYN | TCP_ACK, 0, 0);
        }
        break;

    case TCP_STATE_SYN_RECEIVED:
        if (flags & TCP_ACK) {
            if (ack == c->snd_nxt) {
                c->snd_una = ack;
                c->state   = TCP_STATE_ESTABLISHED;
                c->retries = 0;
                serial_puts("[tcp] conn ");
                tcp_serial_u32(ci);
                serial_puts(" ESTABLISHED (server)\n");
            }
        }
        break;

    case TCP_STATE_ESTABLISHED:
        /* ACK for our data */
        if (flags & TCP_ACK) {
            if (ack > c->snd_una) {
                c->snd_una = ack;
                c->retries = 0;
            }
        }

        /* Incoming data */
        if (payload_len > 0) {
            if (seq == c->rcv_nxt) {
                /* In-order segment */
                int written = recv_buf_write(c, payload, payload_len);
                c->rcv_nxt += (uint32_t)written;

                /* ACK the data */
                tcp_send_segment(ci, TCP_ACK, 0, 0);
            }
            /* else: out-of-order — drop (simplified) */
        }

        /* FIN from peer */
        if (flags & TCP_FIN) {
            c->rcv_nxt = seq + payload_len + 1;  /* FIN consumes 1 seq */
            c->state   = TCP_STATE_CLOSE_WAIT;

            serial_puts("[tcp] conn ");
            tcp_serial_u32(ci);
            serial_puts(" → CLOSE_WAIT (peer sent FIN)\n");

            /* ACK the FIN */
            tcp_send_segment(ci, TCP_ACK, 0, 0);
        }
        break;

    case TCP_STATE_FIN_WAIT_1:
        if (flags & TCP_ACK) {
            if (ack == c->snd_nxt) {
                c->snd_una = ack;
                if (flags & TCP_FIN) {
                    /* Simultaneous close */
                    c->rcv_nxt = seq + 1;
                    c->state = TCP_STATE_TIME_WAIT;
                    c->time_wait_tick = tick_count;
                    tcp_send_segment(ci, TCP_ACK, 0, 0);
                } else {
                    c->state = TCP_STATE_FIN_WAIT_2;
                }
            }
        } else if (flags & TCP_FIN) {
            /* FIN without ACK of our FIN — simultaneous close */
            c->rcv_nxt = seq + 1;
            c->state = TCP_STATE_CLOSING;
            tcp_send_segment(ci, TCP_ACK, 0, 0);
        }
        break;

    case TCP_STATE_FIN_WAIT_2:
        if (flags & TCP_FIN) {
            c->rcv_nxt = seq + 1;
            c->state = TCP_STATE_TIME_WAIT;
            c->time_wait_tick = tick_count;

            serial_puts("[tcp] conn ");
            tcp_serial_u32(ci);
            serial_puts(" → TIME_WAIT\n");

            tcp_send_segment(ci, TCP_ACK, 0, 0);
        }
        break;

    case TCP_STATE_CLOSING:
        if ((flags & TCP_ACK) && ack == c->snd_nxt) {
            c->snd_una = ack;
            c->state = TCP_STATE_TIME_WAIT;
            c->time_wait_tick = tick_count;
        }
        break;

    case TCP_STATE_LAST_ACK:
        if ((flags & TCP_ACK) && ack == c->snd_nxt) {
            serial_puts("[tcp] conn ");
            tcp_serial_u32(ci);
            serial_puts(" → CLOSED (last ACK received)\n");
            c->state = TCP_STATE_CLOSED;
        }
        break;

    case TCP_STATE_TIME_WAIT:
        /* Retransmitted FIN — re-ACK */
        if (flags & TCP_FIN) {
            tcp_send_segment(ci, TCP_ACK, 0, 0);
            c->time_wait_tick = tick_count;  /* restart timer */
        }
        break;

    default:
        break;
    }
}

/* ── tcp_tick: periodic housekeeping ──────────────────────────────────── */

void tcp_tick(void) {
    for (int i = 0; i < TCP_MAX_CONNECTIONS; i++) {
        TcpConnection *c = &conns[i];

        switch (c->state) {
        case TCP_STATE_SYN_SENT:
        case TCP_STATE_SYN_RECEIVED:
            /* Retransmit SYN or SYN+ACK */
            if (tick_count - c->last_send_tick >= TCP_RETRANSMIT_MS) {
                if (c->retries >= TCP_MAX_RETRIES) {
                    serial_puts("[tcp] conn ");
                    tcp_serial_u32(i);
                    serial_puts(" timeout in ");
                    serial_puts(tcp_state_name(c->state));
                    serial_puts("\n");
                    c->state = TCP_STATE_CLOSED;
                } else {
                    c->retries++;
                    serial_puts("[tcp] retransmit ");
                    serial_puts(tcp_state_name(c->state));
                    serial_puts(" conn ");
                    tcp_serial_u32(i);
                    serial_puts(" (retry ");
                    tcp_serial_u32(c->retries);
                    serial_puts(")\n");

                    /* Re-send: reset snd_nxt back to ISS to resend SYN */
                    c->snd_nxt = c->snd_iss;
                    if (c->state == TCP_STATE_SYN_SENT)
                        tcp_send_segment(i, TCP_SYN, 0, 0);
                    else
                        tcp_send_segment(i, TCP_SYN | TCP_ACK, 0, 0);
                }
            }
            break;

        case TCP_STATE_FIN_WAIT_1:
        case TCP_STATE_LAST_ACK:
            /* Retransmit FIN */
            if (tick_count - c->last_send_tick >= TCP_RETRANSMIT_MS) {
                if (c->retries >= TCP_MAX_RETRIES) {
                    serial_puts("[tcp] conn ");
                    tcp_serial_u32(i);
                    serial_puts(" close timeout → CLOSED\n");
                    c->state = TCP_STATE_CLOSED;
                } else {
                    c->retries++;
                    c->snd_nxt--;  /* back up to resend FIN */
                    tcp_send_segment(i, TCP_FIN | TCP_ACK, 0, 0);
                }
            }
            break;

        case TCP_STATE_TIME_WAIT:
            if (tick_count - c->time_wait_tick >= TCP_TIME_WAIT_MS) {
                serial_puts("[tcp] conn ");
                tcp_serial_u32(i);
                serial_puts(" TIME_WAIT expired → CLOSED\n");
                c->state = TCP_STATE_CLOSED;
            }
            break;

        default:
            break;
        }
    }
}

/* ── tcp_connect: active open ─────────────────────────────────────────── */

int tcp_connect(uint32_t dst_ip, uint16_t dst_port, uint16_t src_port) {
    int ci = tcp_alloc_conn();
    if (ci < 0) {
        serial_puts("[tcp] no free connection slots\n");
        return -1;
    }

    const NetConfig *cfg = ip_get_config();
    if (!cfg || !cfg->configured) return -1;

    TcpConnection *c = &conns[ci];
    tcp_memset(c, 0, sizeof(*c));

    c->local_ip    = cfg->ip;
    c->local_port  = src_port;
    c->remote_ip   = dst_ip;
    c->remote_port = dst_port;
    c->snd_iss     = tcp_gen_isn();
    c->snd_nxt     = c->snd_iss;
    c->snd_una     = c->snd_iss;
    c->state       = TCP_STATE_SYN_SENT;
    c->retries     = 0;

    serial_puts("[tcp] connecting to ");
    tcp_serial_u32(dst_ip);
    serial_puts(":");
    tcp_serial_u32(dst_port);
    serial_puts(" (conn ");
    tcp_serial_u32(ci);
    serial_puts(")\n");

    /* Send SYN */
    tcp_send_segment(ci, TCP_SYN, 0, 0);

    return ci;
}

/* ── tcp_listen: passive open ─────────────────────────────────────────── */

int tcp_listen(uint16_t port) {
    int ci = tcp_alloc_conn();
    if (ci < 0) {
        serial_puts("[tcp] no free slots for listen\n");
        return -1;
    }

    const NetConfig *cfg = ip_get_config();
    TcpConnection *c = &conns[ci];
    tcp_memset(c, 0, sizeof(*c));

    c->local_ip    = cfg ? cfg->ip : 0;
    c->local_port  = port;
    c->state       = TCP_STATE_LISTEN;

    serial_puts("[tcp] listening on :");
    tcp_serial_u32(port);
    serial_puts(" (conn ");
    tcp_serial_u32(ci);
    serial_puts(")\n");

    return ci;
}

/* ── tcp_send: send data on established connection ────────────────────── */

int tcp_send(int conn_id, const void *data, uint16_t len) {
    if (conn_id < 0 || conn_id >= TCP_MAX_CONNECTIONS) return -1;
    TcpConnection *c = &conns[conn_id];
    if (c->state != TCP_STATE_ESTABLISHED) return -1;
    if (len == 0) return 0;

    /* Clamp to MSS */
    uint16_t send_len = len > TCP_MSS ? TCP_MSS : len;

    return tcp_send_segment(conn_id, TCP_ACK | TCP_PSH, data, send_len);
}

/* ── tcp_read: read from receive buffer ───────────────────────────────── */

int tcp_read(int conn_id, void *buf, uint16_t buf_size) {
    if (conn_id < 0 || conn_id >= TCP_MAX_CONNECTIONS) return -1;
    TcpConnection *c = &conns[conn_id];

    /* Allow reads in ESTABLISHED and CLOSE_WAIT (peer closed but data may remain) */
    if (c->state != TCP_STATE_ESTABLISHED &&
        c->state != TCP_STATE_CLOSE_WAIT &&
        c->state != TCP_STATE_FIN_WAIT_1 &&
        c->state != TCP_STATE_FIN_WAIT_2) {
        return -1;
    }

    if (c->recv_count == 0) return 0;

    return recv_buf_read(c, (uint8_t *)buf, buf_size);
}

/* ── tcp_close: initiate graceful close ───────────────────────────────── */

int tcp_close(int conn_id) {
    if (conn_id < 0 || conn_id >= TCP_MAX_CONNECTIONS) return -1;
    TcpConnection *c = &conns[conn_id];

    switch (c->state) {
    case TCP_STATE_ESTABLISHED:
        c->state   = TCP_STATE_FIN_WAIT_1;
        c->retries = 0;
        tcp_send_segment(conn_id, TCP_FIN | TCP_ACK, 0, 0);

        serial_puts("[tcp] conn ");
        tcp_serial_u32(conn_id);
        serial_puts(" → FIN_WAIT_1 (closing)\n");
        return 0;

    case TCP_STATE_CLOSE_WAIT:
        c->state   = TCP_STATE_LAST_ACK;
        c->retries = 0;
        tcp_send_segment(conn_id, TCP_FIN | TCP_ACK, 0, 0);

        serial_puts("[tcp] conn ");
        tcp_serial_u32(conn_id);
        serial_puts(" → LAST_ACK\n");
        return 0;

    case TCP_STATE_LISTEN:
    case TCP_STATE_SYN_SENT:
        c->state = TCP_STATE_CLOSED;
        return 0;

    default:
        return -1;  /* already closing */
    }
}

/* ── tcp_get_state ────────────────────────────────────────────────────── */

int tcp_get_state(int conn_id) {
    if (conn_id < 0 || conn_id >= TCP_MAX_CONNECTIONS) return TCP_STATE_CLOSED;
    return conns[conn_id].state;
}

/* ── tcp_dump: debug connection table ─────────────────────────────────── */

void tcp_dump(void) {
    serial_puts("[tcp] Connection table:\n");
    serial_puts("  ID  State       Local      Remote           Seq/Ack\n");
    serial_puts("  --  ----------  ---------  ---------------  -------\n");

    int active = 0;
    for (int i = 0; i < TCP_MAX_CONNECTIONS; i++) {
        TcpConnection *c = &conns[i];
        if (c->state == TCP_STATE_CLOSED) continue;
        active++;

        serial_puts("  ");
        tcp_serial_u32(i);
        serial_puts("   ");
        serial_puts(tcp_state_name(c->state));

        /* Pad state */
        int slen = 0;
        const char *sn = tcp_state_name(c->state);
        while (sn[slen]) slen++;
        for (int p = slen; p < 12; p++) serial_puts(" ");

        serial_puts(":");
        tcp_serial_u32(c->local_port);
        serial_puts("      ");
        tcp_serial_u32(c->remote_ip);
        serial_puts(":");
        tcp_serial_u32(c->remote_port);
        serial_puts("  snd=");
        tcp_serial_u32(c->snd_nxt);
        serial_puts(" rcv=");
        tcp_serial_u32(c->rcv_nxt);
        serial_puts(" rx=");
        tcp_serial_u32(c->recv_count);
        serial_puts("B\n");
    }

    if (active == 0) {
        serial_puts("  (no active connections)\n");
    }
}

/* ── tcp_active_count ─────────────────────────────────────────────────── */

int tcp_active_count(void) {
    int n = 0;
    for (int i = 0; i < TCP_MAX_CONNECTIONS; i++) {
        if (conns[i].state != TCP_STATE_CLOSED) n++;
    }
    return n;
}
