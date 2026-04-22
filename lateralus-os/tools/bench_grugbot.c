/* ===========================================================================
 * tools/bench_grugbot.c — native benchmark for the grugbot420 engine
 * ===========================================================================
 * Mirrors the exact response engine from gui/terminal.c and apps/apps.c
 * (xorshift32 PRNG, case-insensitive substring match, keyword dispatcher,
 * wisdom/joke/smoke tables) and times it against a varied corpus.
 *
 * Build & run:
 *     gcc -O2 -Wall -std=c99 tools/bench_grugbot.c -o build/bench_grugbot
 *     ./build/bench_grugbot [iterations]
 * =========================================================================== */

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <inttypes.h>
#include <string.h>
#include <time.h>
#include <ctype.h>

/* -------- wisdom / joke / smoke tables (copied from grugbot engine) ----- */

static const char *GRUG_WISDOM[] = {
    "grug say: complexity very very bad. simple good.",
    "grug say: factory factory factory make grug head hurt.",
    "grug say: name variable what it be. 'data' mean nothing.",
    "grug say: if code hard to delete, code already own you.",
    "grug say: type system friend, not enemy. type catch bug.",
    "grug brain small, so grug keep function small too.",
    "grug say: senior dev is one who know where bodies buried.",
    "grug say: meeting is where productivity go to die.",
    "grug say: ship small, ship often, fix in prod, grug not scared.",
    "grug say: premature optimization root of all bug. measure first.",
    "grug say: DRY is lie. same shape not same meaning.",
    "grug say: if test hard to write, code shape wrong.",
    "grug say: comment say WHY. code already say WHAT.",
    "grug say: log loud when bad, silent when good.",
};
static const int GRUG_WISDOM_N = sizeof(GRUG_WISDOM)/sizeof(GRUG_WISDOM[0]);

static const char *GRUG_JOKES[] = {
    "why function cross road? because callback on other side.",
    "grug have 99 problem but null pointer not one. grug also have null.",
    "how many grug to change lightbulb? none. grug afraid of dark.",
    "grug try recursion to understand recursion. grug still trying.",
    "wife say get bread, if egg get 12. he come home with 12 bread.",
};
static const int GRUG_JOKES_N = sizeof(GRUG_JOKES)/sizeof(GRUG_JOKES[0]);

static const char *GRUG_SMOKE[] = {
    "grug puff... semicolons are just fences for thoughts.",
    "grug puff... garbage collector is just letting go man.",
    "grug puff... monad is just burrito of sadness.",
    "grug puff... every for-loop is a tiny universe bro.",
    "grug puff... types are vibes and vibes are types.",
    "grug puff... the real bug was friends we made along the way.",
};
static const int GRUG_SMOKE_N = sizeof(GRUG_SMOKE)/sizeof(GRUG_SMOKE[0]);

/* -------- engine state ------------------------------------------------- */

typedef struct {
    uint32_t rng;
    int      mood;
    int      hits;
    /* Counters — so the dispatcher has an observable effect and the
     * compiler can't DCE the calls. */
    uint64_t bytes_out;
    uint64_t responses;
} Grug;

static uint32_t grug_rand(Grug *g) {
    uint32_t x = g->rng;
    if (x == 0) x = 0x420BADA5u;
    x ^= x << 13; x ^= x >> 17; x ^= x << 5;
    g->rng = x;
    return x & 0x7fffffffu;
}

static int grug_has(const char *hay, const char *needle) {
    if (!hay || !needle || !*needle) return 0;
    for (int i = 0; hay[i]; i++) {
        int j = 0;
        while (needle[j]) {
            char a = hay[i + j];
            char b = needle[j];
            if (!a) return 0;
            if (a >= 'A' && a <= 'Z') a += 32;
            if (b >= 'A' && b <= 'Z') b += 32;
            if (a != b) break;
            j++;
        }
        if (!needle[j]) return 1;
    }
    return 0;
}

static int grug_streq_ci(const char *a, const char *b) {
    for (int i = 0;; i++) {
        char x = a[i], y = b[i];
        if (x >= 'A' && x <= 'Z') x += 32;
        if (y >= 'A' && y <= 'Z') y += 32;
        if (x != y) return 0;
        if (!x) return 1;
    }
}

/* Pretend-emit: just accumulate length so the optimizer cannot drop work */
static void grug_emit(Grug *g, const char *s) {
    if (!s) return;
    size_t n = strlen(s);
    g->bytes_out += n;
}

static void grug_say(Grug *g, const char *text) {
    grug_emit(g, (g->mood >= 1) ? "[grug420] " : "[grug] ");
    grug_emit(g, text);
    grug_emit(g, "\n");
}

static void grug_handle_cmd(Grug *g, const char *cmd) {
    if (grug_streq_ci(cmd, "/help")) {
        grug_emit(g, "[sys] commands: /help /wisdom /joke /roll /smoke /time /quit\n");
        return;
    }
    if (grug_streq_ci(cmd, "/wisdom")) {
        grug_say(g, GRUG_WISDOM[grug_rand(g) % GRUG_WISDOM_N]); return;
    }
    if (grug_streq_ci(cmd, "/joke")) {
        grug_say(g, GRUG_JOKES[grug_rand(g) % GRUG_JOKES_N]); return;
    }
    if (grug_streq_ci(cmd, "/roll")) {
        char buf[48];
        snprintf(buf, sizeof(buf), "d20 rolls: %u", (unsigned)((grug_rand(g) % 20) + 1));
        grug_say(g, buf); return;
    }
    if (grug_streq_ci(cmd, "/smoke")) {
        g->hits++;
        g->mood = (g->hits >= 3) ? 2 : 1;
        grug_emit(g, "[grug420] *puff puff pass*\n");
        grug_say(g, GRUG_SMOKE[grug_rand(g) % GRUG_SMOKE_N]);
        return;
    }
    grug_emit(g, "[sys] unknown command\n");
}

static void grug_respond(Grug *g, const char *line) {
    g->responses++;
    if (line[0] == '/') { grug_handle_cmd(g, line); return; }
    if (line[0] == 0)   { return; }

    if (grug_has(line, "hi") || grug_has(line, "hello") || grug_has(line, "hey") ||
        grug_has(line, "sup") || grug_has(line, "yo")) {
        grug_say(g, "hi friend. grug here. what on brain?"); return;
    }
    if (grug_has(line, "bug") || grug_has(line, "crash") ||
        grug_has(line, "broken") || grug_has(line, "panic")) {
        static const char *replies[] = {
            "bug not personal. bug just code telling truth.",
            "read stack trace top-down. answer in there.",
            "print statement older than grug. still work.",
        };
        grug_say(g, replies[grug_rand(g) % 3]); return;
    }
    if (grug_has(line, "complex") || grug_has(line, "overengineer") || grug_has(line, "abstract")) {
        grug_say(g, "complexity demon love abstract factory. delete layer."); return;
    }
    if (grug_has(line, "ship") || grug_has(line, "deploy") || grug_has(line, "release") || grug_has(line, "prod")) {
        grug_say(g, "ship it. worst case rollback. best case user smile."); return;
    }
    if (grug_has(line, "test") || grug_has(line, "tdd") || grug_has(line, "unit")) {
        grug_say(g, "test is rope grug tie to past self."); return;
    }
    if (grug_has(line, "refactor") || grug_has(line, "rewrite")) {
        grug_say(g, "rewrite from scratch is trap. small step. commit often."); return;
    }
    if (grug_has(line, "oop") || grug_has(line, "inherit") || grug_has(line, "class")) {
        grug_say(g, "inheritance tall, composition wide. wide better."); return;
    }
    if (grug_has(line, "meeting") || grug_has(line, "standup") || grug_has(line, "agile")) {
        grug_say(g, "meeting should be email. email should be nothing."); return;
    }
    if (grug_has(line, "perf") || grug_has(line, "slow") || grug_has(line, "fast") || grug_has(line, "optim")) {
        grug_say(g, "measure first. optimize hottest spot. not before."); return;
    }
    if (grug_has(line, "type") || grug_has(line, "rust")) {
        grug_say(g, "type system is exoskeleton."); return;
    }
    if (grug_has(line, "ai") || grug_has(line, "llm") || grug_has(line, "copilot") || grug_has(line, "gpt")) {
        grug_say(g, "llm is clever parrot. good first draft, bad last draft."); return;
    }
    if (grug_has(line, "friday") || grug_has(line, "weekend")) {
        grug_say(g, "no deploy friday. grug want pizza not pager."); return;
    }
    if (grug_has(line, "weed") || grug_has(line, "420") ||
        grug_has(line, "blaze") || grug_has(line, "smoke") || grug_has(line, "sesh")) {
        grug_handle_cmd(g, "/smoke"); return;
    }
    if (grug_has(line, "wisdom") || grug_has(line, "advice")) {
        grug_handle_cmd(g, "/wisdom"); return;
    }
    if (grug_has(line, "joke") || grug_has(line, "funny")) {
        grug_handle_cmd(g, "/joke"); return;
    }
    if (grug_has(line, "thanks") || grug_has(line, "thank you") || grug_has(line, "love you")) {
        grug_say(g, "grug love you too."); return;
    }
    if (grug_has(line, "bye") || grug_has(line, "cya") || grug_has(line, "later") || grug_has(line, "goodbye")) {
        grug_say(g, "peace friend."); return;
    }
    grug_say(g, GRUG_WISDOM[grug_rand(g) % GRUG_WISDOM_N]);
}

/* -------- corpus ------------------------------------------------------- */

static const char *CORPUS[] = {
    "hello grug",
    "i have a bug in my code",
    "complexity is killing my project",
    "should i ship on friday?",
    "talk to me about types",
    "how do i write tests",
    "lets refactor this oop mess",
    "llm wrote my code, is that ok",
    "give me wisdom",
    "tell a joke",
    "blaze it",
    "thanks friend",
    "random question about the weather",
    "/roll",
    "/wisdom",
    "/joke",
    "/help",
    "/smoke",
    "i am struggling with this refactor and performance",
    "overengineered abstract factory of doom",
    "my unit tests are slow",
    "copilot gpt llm ai friday deploy",
    "bye for now",
    "",
};
static const int CORPUS_N = sizeof(CORPUS)/sizeof(CORPUS[0]);

/* -------- main --------------------------------------------------------- */

static double now_sec(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (double)ts.tv_sec + (double)ts.tv_nsec / 1e9;
}
int main(int argc, char **argv) {
    long iters = 1000000;
    if (argc > 1) iters = atol(argv[1]);
    if (iters <= 0) iters = 1000000;

    Grug g = {0};
    g.rng = 0x420BADA5u;

    /* Warmup */
    for (int i = 0; i < 10000; i++) {
        grug_respond(&g, CORPUS[i % CORPUS_N]);
    }
    g.bytes_out = 0;
    g.responses = 0;

    double t0 = now_sec();
    for (long i = 0; i < iters; i++) {
        grug_respond(&g, CORPUS[i % CORPUS_N]);
    }
    double t1 = now_sec();

    double elapsed = t1 - t0;
    double per_call_ns = (elapsed * 1e9) / (double)iters;
    double throughput = (double)iters / elapsed;
    double mb_out = (double)g.bytes_out / (1024.0 * 1024.0);
    double mbps = (mb_out / elapsed);

    printf("======================================================\n");
    printf(" grugbot420 — native benchmark (LateralusOS engine)\n");
    printf("======================================================\n");
    printf(" corpus size:     %d inputs (mix of free text + /cmds)\n", CORPUS_N);
    printf(" iterations:      %ld\n", iters);
    printf(" elapsed:         %.3f s\n", elapsed);
    printf(" responses:       %" PRIu64 "\n", (uint64_t)g.responses);
    printf(" throughput:      %.0f resp/sec\n", throughput);
    printf(" latency:         %.1f ns/call  (%.3f us/call)\n",
           per_call_ns, per_call_ns / 1000.0);
    printf(" output volume:   %.2f MB total, %.1f MB/s\n", mb_out, mbps);
    printf(" final rng state: 0x%08X  hits=%d  mood=%d\n",
           g.rng, g.hits, g.mood);
    printf("======================================================\n");
    return 0;
}
