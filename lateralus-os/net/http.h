/* =======================================================================
 * LateralusOS — HTTP/1.1 Client
 * Minimal HTTP client built on the TCP transport layer.
 * Supports GET requests with response parsing.
 *
 * Part of LateralusOS v0.3.0
 * ======================================================================= */

#ifndef LATERALUS_HTTP_H
#define LATERALUS_HTTP_H

#include "../gui/types.h"

/* -- Constants ---------------------------------------------------------- */

#define HTTP_MAX_URL_LEN      256
#define HTTP_MAX_HOST_LEN     128
#define HTTP_MAX_PATH_LEN     128
#define HTTP_MAX_HEADERS      16
#define HTTP_MAX_HEADER_LEN   256
#define HTTP_RESP_BUF_SIZE    4096   /* Response buffer (headers + body) */
#define HTTP_CONNECT_TIMEOUT  5000   /* 5 seconds connect timeout (ms) */
#define HTTP_READ_TIMEOUT     10000  /* 10 seconds read timeout (ms) */
#define HTTP_DEFAULT_PORT     80

/* -- HTTP methods ------------------------------------------------------- */

#define HTTP_METHOD_GET   0
#define HTTP_METHOD_HEAD  1
#define HTTP_METHOD_POST  2

/* -- HTTP response ------------------------------------------------------ */

typedef struct {
    int      status_code;                        /* 200, 404, etc. */
    char     status_text[32];                    /* "OK", "Not Found", etc. */
    char     content_type[64];                   /* Content-Type header */
    int      content_length;                     /* Content-Length (-1 if unknown) */
    int      header_end;                         /* Offset where body begins */
    char     buf[HTTP_RESP_BUF_SIZE];            /* Raw response data */
    int      buf_len;                            /* Bytes received */
    int      ok;                                 /* 1 if status 2xx, 0 otherwise */
    int      error;                              /* 0=success, -1=dns fail, -2=connect fail,
                                                    -3=timeout, -4=send fail, -5=recv fail */
} HttpResponse;

/* -- URL components ----------------------------------------------------- */

typedef struct {
    char     host[HTTP_MAX_HOST_LEN];
    char     path[HTTP_MAX_PATH_LEN];
    uint16_t port;
} HttpUrl;

/* -- Public API --------------------------------------------------------- */

/* Initialize HTTP subsystem. Call after tcp_init(). */
void http_init(void);

/* Parse a URL into host/path/port components.
   Supports: http://host[:port][/path]
   Returns 0 on success, -1 on parse failure. */
int http_parse_url(const char *url, HttpUrl *out);

/* Perform an HTTP GET request.
   Blocks until response received or timeout.
   Returns pointer to static HttpResponse (valid until next call).
   Caller should check resp->error and resp->ok. */
HttpResponse *http_get(const char *host, uint16_t port, const char *path);

/* Convenience: GET by full URL string.
   Parses URL, resolves DNS, connects, sends GET, reads response. */
HttpResponse *http_get_url(const char *url);

/* Get pointer to response body (after headers).
   Returns NULL if no body or parse error. */
const char *http_body(const HttpResponse *resp);

/* Get response body length.
   Returns 0 if no body. */
int http_body_len(const HttpResponse *resp);

#endif /* LATERALUS_HTTP_H */
