/* =======================================================================
 * LateralusOS — HTTP/1.1 Client Implementation
 * Minimal HTTP client built on top of the TCP transport layer.
 *
 * Part of LateralusOS v0.3.0
 * ======================================================================= */

#include "http.h"
#include "tcp.h"
#include "ip.h"
#include "dns.h"

/* -- Local helpers ------------------------------------------------------ */

static void http_memset(void *dst, uint8_t val, int len) {
    uint8_t *d = (uint8_t *)dst;
    for (int i = 0; i < len; i++) d[i] = val;
}

static void http_memcpy(void *dst, const void *src, int len) {
    uint8_t *d = (uint8_t *)dst;
    const uint8_t *s = (const uint8_t *)src;
    for (int i = 0; i < len; i++) d[i] = s[i];
}

static int http_strlen(const char *s) {
    int len = 0;
    while (s[len]) len++;
    return len;
}

static int http_strcmp(const char *a, const char *b) {
    while (*a && *a == *b) { a++; b++; }
    return (unsigned char)*a - (unsigned char)*b;
}

static int http_strncmp(const char *a, const char *b, int n) {
    for (int i = 0; i < n; i++) {
        if (a[i] != b[i]) return (unsigned char)a[i] - (unsigned char)b[i];
        if (a[i] == '\0') return 0;
    }
    return 0;
}

static int http_strncasecmp(const char *a, const char *b, int n) {
    for (int i = 0; i < n; i++) {
        char ca = a[i], cb = b[i];
        if (ca >= 'A' && ca <= 'Z') ca += 32;
        if (cb >= 'A' && cb <= 'Z') cb += 32;
        if (ca != cb) return (unsigned char)ca - (unsigned char)cb;
        if (ca == '\0') return 0;
    }
    return 0;
}

static char *http_strchr(const char *s, char c) {
    while (*s) {
        if (*s == c) return (char *)s;
        s++;
    }
    return (char *)0;
}

static int http_atoi(const char *s) {
    int val = 0;
    int neg = 0;
    while (*s == ' ') s++;
    if (*s == '-') { neg = 1; s++; }
    while (*s >= '0' && *s <= '9') {
        val = val * 10 + (*s - '0');
        s++;
    }
    return neg ? -val : val;
}

static void http_itoa(int val, char *buf, int buf_size) {
    if (buf_size < 2) { if (buf_size) buf[0] = '\0'; return; }
    char tmp[16];
    int pos = 0;
    int neg = 0;
    if (val < 0) { neg = 1; val = -val; }
    if (val == 0) { tmp[pos++] = '0'; }
    else { while (val > 0 && pos < 15) { tmp[pos++] = '0' + (val % 10); val /= 10; } }

    int out = 0;
    if (neg && out < buf_size - 1) buf[out++] = '-';
    for (int i = pos - 1; i >= 0 && out < buf_size - 1; i--)
        buf[out++] = tmp[i];
    buf[out] = '\0';
}

/* Serial debug output */
extern void serial_puts(const char *s);

static void http_debug(const char *msg) {
    serial_puts("[http] ");
    serial_puts(msg);
    serial_puts("\n");
}

/* Scheduler sleep (milliseconds) */
extern void sched_sleep(uint32_t ms);

/* Tick counter for timeouts */
extern volatile uint64_t tick_count;

/* -- Static response buffer --------------------------------------------- */

static HttpResponse http_resp;

/* -- Next ephemeral source port ----------------------------------------- */

static uint16_t http_next_port = 49152;

static uint16_t http_alloc_port(void) {
    uint16_t p = http_next_port++;
    if (http_next_port > 65000) http_next_port = 49152;
    return p;
}

/* =======================================================================
 * http_init()
 * ======================================================================= */

void http_init(void) {
    http_next_port = 49152;
    serial_puts("[http] HTTP/1.1 client initialized\n");
}

/* =======================================================================
 * http_parse_url()  —  Parse "http://host[:port][/path]"
 * ======================================================================= */

int http_parse_url(const char *url, HttpUrl *out) {
    http_memset(out, 0, sizeof(HttpUrl));
    out->port = HTTP_DEFAULT_PORT;

    /* Skip scheme */
    if (http_strncmp(url, "http://", 7) == 0) {
        url += 7;
    } else if (http_strncmp(url, "https://", 8) == 0) {
        /* HTTPS not supported — but accept the URL, just use port 443 */
        url += 8;
        out->port = 443;
    }

    /* Extract host (up to ':', '/', or end) */
    int hi = 0;
    while (*url && *url != ':' && *url != '/' && hi < HTTP_MAX_HOST_LEN - 1) {
        out->host[hi++] = *url++;
    }
    out->host[hi] = '\0';

    if (hi == 0) return -1;  /* empty host */

    /* Optional port */
    if (*url == ':') {
        url++;
        out->port = (uint16_t)http_atoi(url);
        while (*url >= '0' && *url <= '9') url++;
    }

    /* Path (default to "/") */
    if (*url == '/') {
        int pi = 0;
        while (*url && pi < HTTP_MAX_PATH_LEN - 1) {
            out->path[pi++] = *url++;
        }
        out->path[pi] = '\0';
    } else {
        out->path[0] = '/';
        out->path[1] = '\0';
    }

    return 0;
}

/* =======================================================================
 * Build HTTP/1.1 GET request into buffer
 * Returns length of request string
 * ======================================================================= */

static int http_build_get(const char *host, const char *path, char *buf, int buf_size) {
    /* GET /path HTTP/1.1\r\nHost: host\r\nConnection: close\r\nUser-Agent: LateralusOS/0.3\r\n\r\n */
    int pos = 0;

    #define APPEND(s) do { \
        const char *_s = (s); \
        while (*_s && pos < buf_size - 1) buf[pos++] = *_s++; \
    } while(0)

    APPEND("GET ");
    APPEND(path);
    APPEND(" HTTP/1.1\r\n");
    APPEND("Host: ");
    APPEND(host);
    APPEND("\r\n");
    APPEND("Connection: close\r\n");
    APPEND("User-Agent: LateralusOS/0.3.0\r\n");
    APPEND("Accept: */*\r\n");
    APPEND("\r\n");

    buf[pos] = '\0';

    #undef APPEND

    return pos;
}

/* =======================================================================
 * Parse HTTP response headers from buffer
 * ======================================================================= */

static void http_parse_response(HttpResponse *resp) {
    resp->status_code = 0;
    resp->status_text[0] = '\0';
    resp->content_type[0] = '\0';
    resp->content_length = -1;
    resp->header_end = -1;
    resp->ok = 0;

    if (resp->buf_len < 12) return;  /* Too short for "HTTP/1.x NNN" */

    /* Parse status line: "HTTP/1.x NNN Reason\r\n" */
    if (http_strncmp(resp->buf, "HTTP/1.", 7) != 0) return;

    const char *p = resp->buf + 9;  /* skip "HTTP/1.x " */
    resp->status_code = http_atoi(p);
    resp->ok = (resp->status_code >= 200 && resp->status_code < 300) ? 1 : 0;

    /* Extract status text */
    while (*p >= '0' && *p <= '9') p++;
    if (*p == ' ') p++;
    int si = 0;
    while (*p && *p != '\r' && *p != '\n' && si < 31) {
        resp->status_text[si++] = *p++;
    }
    resp->status_text[si] = '\0';

    /* Find end of headers (\r\n\r\n) */
    for (int i = 0; i < resp->buf_len - 3; i++) {
        if (resp->buf[i] == '\r' && resp->buf[i+1] == '\n' &&
            resp->buf[i+2] == '\r' && resp->buf[i+3] == '\n') {
            resp->header_end = i + 4;
            break;
        }
    }

    /* Parse selected headers */
    const char *line = http_strchr(resp->buf, '\n');
    if (line) line++;  /* skip first line (status) */

    while (line && line < resp->buf + (resp->header_end > 0 ? resp->header_end : resp->buf_len)) {
        /* Content-Length */
        if (http_strncasecmp(line, "Content-Length:", 15) == 0) {
            const char *val = line + 15;
            while (*val == ' ') val++;
            resp->content_length = http_atoi(val);
        }
        /* Content-Type */
        else if (http_strncasecmp(line, "Content-Type:", 13) == 0) {
            const char *val = line + 13;
            while (*val == ' ') val++;
            int ci = 0;
            while (*val && *val != '\r' && *val != '\n' && ci < 63) {
                resp->content_type[ci++] = *val++;
            }
            resp->content_type[ci] = '\0';
        }

        /* Next line */
        line = http_strchr(line, '\n');
        if (line) line++;
        else break;

        /* Empty line = end of headers */
        if (*line == '\r' || *line == '\n') break;
    }
}

/* =======================================================================
 * http_get()  —  Perform HTTP GET request (blocking)
 * ======================================================================= */

HttpResponse *http_get(const char *host, uint16_t port, const char *path) {
    /* Clear response */
    http_memset(&http_resp, 0, sizeof(HttpResponse));

    /* Resolve hostname via DNS */
    uint32_t ip = dns_resolve(host);
    if (ip == 0) {
        http_debug("DNS resolution failed");
        http_resp.error = -1;
        return &http_resp;
    }

    char ip_str[20];
    ip_to_str(ip, ip_str);
    serial_puts("[http] resolved ");
    serial_puts(host);
    serial_puts(" -> ");
    serial_puts(ip_str);
    serial_puts("\n");

    /* Allocate ephemeral source port */
    uint16_t src_port = http_alloc_port();

    /* Open TCP connection */
    int conn = tcp_connect(ip, port, src_port);
    if (conn < 0) {
        http_debug("TCP connect failed (no free slots)");
        http_resp.error = -2;
        return &http_resp;
    }

    char buf8[8];
    serial_puts("[http] TCP connecting (conn=");
    http_itoa(conn, buf8, sizeof(buf8));
    serial_puts(buf8);
    serial_puts(", port=");
    http_itoa(src_port, buf8, sizeof(buf8));
    serial_puts(buf8);
    serial_puts(")\n");

    /* Wait for connection to establish */
    uint64_t deadline = tick_count + HTTP_CONNECT_TIMEOUT;
    while (tick_count < deadline) {
        int state = tcp_get_state(conn);
        if (state == TCP_STATE_ESTABLISHED) break;
        if (state == TCP_STATE_CLOSED) {
            http_debug("connection refused/reset");
            http_resp.error = -2;
            return &http_resp;
        }
        sched_sleep(50);  /* check every 50ms */
    }

    if (tcp_get_state(conn) != TCP_STATE_ESTABLISHED) {
        http_debug("connect timeout");
        tcp_close(conn);
        http_resp.error = -3;
        return &http_resp;
    }

    serial_puts("[http] connected, sending GET ");
    serial_puts(path);
    serial_puts("\n");

    /* Build and send GET request */
    char req_buf[512];
    int req_len = http_build_get(host, path, req_buf, sizeof(req_buf));

    int sent = tcp_send(conn, req_buf, (uint16_t)req_len);
    if (sent < 0) {
        http_debug("send failed");
        tcp_close(conn);
        http_resp.error = -4;
        return &http_resp;
    }

    /* Read response */
    deadline = tick_count + HTTP_READ_TIMEOUT;
    http_resp.buf_len = 0;

    while (tick_count < deadline) {
        int state = tcp_get_state(conn);

        /* Try reading */
        int space = HTTP_RESP_BUF_SIZE - 1 - http_resp.buf_len;
        if (space > 0) {
            int n = tcp_read(conn, http_resp.buf + http_resp.buf_len, (uint16_t)space);
            if (n > 0) {
                http_resp.buf_len += n;
                http_resp.buf[http_resp.buf_len] = '\0';
                /* Reset deadline on data received */
                deadline = tick_count + HTTP_READ_TIMEOUT;
            }
        }

        /* Check if we have complete response */
        if (http_resp.buf_len > 0) {
            /* Look for end of headers */
            int hdr_end = -1;
            for (int i = 0; i < http_resp.buf_len - 3; i++) {
                if (http_resp.buf[i] == '\r' && http_resp.buf[i+1] == '\n' &&
                    http_resp.buf[i+2] == '\r' && http_resp.buf[i+3] == '\n') {
                    hdr_end = i + 4;
                    break;
                }
            }

            if (hdr_end > 0) {
                /* Parse Content-Length to see if we have full body */
                http_parse_response(&http_resp);

                if (http_resp.content_length >= 0) {
                    int expected = hdr_end + http_resp.content_length;
                    if (http_resp.buf_len >= expected) break;  /* Got it all */
                }

                /* Connection: close — server will close when done */
                if (state == TCP_STATE_CLOSE_WAIT || state == TCP_STATE_CLOSED) break;
            }
        }

        /* Connection closed by server — we're done */
        if (state == TCP_STATE_CLOSE_WAIT || state == TCP_STATE_CLOSED) break;

        /* Buffer full */
        if (http_resp.buf_len >= HTTP_RESP_BUF_SIZE - 1) break;

        sched_sleep(50);
    }

    /* Close our side */
    tcp_close(conn);

    if (http_resp.buf_len == 0) {
        http_debug("no response data received");
        http_resp.error = -5;
        return &http_resp;
    }

    /* Final parse */
    http_resp.buf[http_resp.buf_len] = '\0';
    http_parse_response(&http_resp);

    serial_puts("[http] response: ");
    http_itoa(http_resp.status_code, buf8, sizeof(buf8));
    serial_puts(buf8);
    serial_puts(" ");
    serial_puts(http_resp.status_text);
    serial_puts(", ");
    http_itoa(http_resp.buf_len, buf8, sizeof(buf8));
    serial_puts(buf8);
    serial_puts(" bytes\n");

    return &http_resp;
}

/* =======================================================================
 * http_get_url()  —  Convenience wrapper: GET by URL string
 * ======================================================================= */

HttpResponse *http_get_url(const char *url) {
    HttpUrl parsed;
    if (http_parse_url(url, &parsed) < 0) {
        http_memset(&http_resp, 0, sizeof(HttpResponse));
        http_debug("URL parse failed");
        http_resp.error = -1;
        return &http_resp;
    }
    return http_get(parsed.host, parsed.port, parsed.path);
}

/* =======================================================================
 * http_body() / http_body_len()  —  Access response body
 * ======================================================================= */

const char *http_body(const HttpResponse *resp) {
    if (!resp || resp->header_end < 0 || resp->header_end >= resp->buf_len)
        return (const char *)0;
    return resp->buf + resp->header_end;
}

int http_body_len(const HttpResponse *resp) {
    if (!resp || resp->header_end < 0 || resp->header_end >= resp->buf_len)
        return 0;
    return resp->buf_len - resp->header_end;
}
