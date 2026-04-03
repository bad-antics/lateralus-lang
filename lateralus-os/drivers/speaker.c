/* ═══════════════════════════════════════════════════════════════════════
 * LateralusOS — PC Speaker Driver Implementation
 * ═══════════════════════════════════════════════════════════════════════
 * Copyright (c) 2025 bad-antics. All rights reserved.
 * ═══════════════════════════════════════════════════════════════════════ */

#include "speaker.h"

/* ── PIT frequency ────────────────────────────────────────────────────── */

#define PIT_FREQ 1193180   /* PIT base frequency in Hz */

/* ── Note queue for melodies ──────────────────────────────────────────── */

#define MAX_NOTES 8

typedef struct {
    uint32_t freq;
    uint32_t duration_ms;
} Note;

static Note    melody_queue[MAX_NOTES];
static int     melody_count = 0;
static int     melody_idx   = 0;
static uint64_t note_end_tick = 0;
static uint8_t playing = 0;

/* ── Play tone ────────────────────────────────────────────────────────── */

void speaker_play_tone(uint32_t freq) {
    if (freq == 0) { speaker_stop(); return; }

    /* Calculate PIT divisor */
    uint32_t divisor = PIT_FREQ / freq;
    if (divisor == 0) divisor = 1;

    /* Program PIT channel 2 */
    outb(0x43, 0xB6);                           /* Channel 2, mode 3 */
    outb(0x42, (uint8_t)(divisor & 0xFF));       /* Low byte */
    outb(0x42, (uint8_t)((divisor >> 8) & 0xFF)); /* High byte */

    /* Enable speaker (bits 0 and 1 of port 0x61) */
    uint8_t tmp = inb(0x61);
    outb(0x61, tmp | 0x03);

    playing = 1;
}

/* ── Stop tone ────────────────────────────────────────────────────────── */

void speaker_stop(void) {
    uint8_t tmp = inb(0x61);
    outb(0x61, tmp & 0xFC);  /* Clear bits 0 and 1 */
    playing = 0;
}

/* ── Start timed tone ─────────────────────────────────────────────────── */

void speaker_start_timed(uint32_t freq, uint32_t duration_ms,
                          uint64_t current_tick) {
    /* Clear any melody in progress */
    melody_count = 0;
    melody_idx   = 0;

    speaker_play_tone(freq);
    note_end_tick = current_tick + duration_ms;
}

/* ── Schedule melody ──────────────────────────────────────────────────── */

static void _queue_melody(const Note *notes, int count, uint64_t current_tick) {
    melody_count = (count > MAX_NOTES) ? MAX_NOTES : count;
    for (int i = 0; i < melody_count; i++) {
        melody_queue[i] = notes[i];
    }
    melody_idx = 0;

    /* Start first note */
    if (melody_count > 0) {
        speaker_play_tone(melody_queue[0].freq);
        note_end_tick = current_tick + melody_queue[0].duration_ms;
    }
}

/* ── Tick (call at 1kHz) ──────────────────────────────────────────────── */

void speaker_tick(uint64_t current_tick) {
    if (!playing && melody_idx >= melody_count) return;

    if (current_tick >= note_end_tick) {
        speaker_stop();

        /* Advance melody queue */
        melody_idx++;
        if (melody_idx < melody_count) {
            /* Small gap between notes (10ms) */
            if (melody_queue[melody_idx].freq > 0) {
                speaker_play_tone(melody_queue[melody_idx].freq);
            }
            note_end_tick = current_tick + melody_queue[melody_idx].duration_ms;
        }
    }
}

/* ── Boot chime — ascending C-E-G-C ──────────────────────────────────── */

void speaker_boot_chime(uint64_t current_tick) {
    static const Note chime[] = {
        { 523,  120 },   /* C5  */
        { 659,  120 },   /* E5  */
        { 784,  120 },   /* G5  */
        { 1047, 200 },   /* C6  */
    };
    _queue_melody(chime, 4, current_tick);
}

/* ── Error beep — low tone ────────────────────────────────────────────── */

void speaker_error_beep(uint64_t current_tick) {
    static const Note beep[] = {
        { 220, 300 },   /* A3 — low warning tone */
    };
    _queue_melody(beep, 1, current_tick);
}

/* ── Keyclick — very short high tone ──────────────────────────────────── */

void speaker_keyclick(uint64_t current_tick) {
    speaker_start_timed(1200, 3, current_tick);
}

/* ── Window open — pleasant two-note ──────────────────────────────────── */

void speaker_window_open(uint64_t current_tick) {
    static const Note wopen[] = {
        { 880,  60 },    /* A5 */
        { 1175, 80 },    /* D6 */
    };
    _queue_melody(wopen, 2, current_tick);
}

/* ── Notification — gentle ding ───────────────────────────────────────── */

void speaker_notify(uint64_t current_tick) {
    static const Note ding[] = {
        { 1318, 100 },   /* E6 */
    };
    _queue_melody(ding, 1, current_tick);
}

/* ── Query state ──────────────────────────────────────────────────────── */

uint8_t speaker_is_playing(void) {
    return playing || (melody_idx < melody_count);
}
