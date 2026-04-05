/* =======================================================================
 * LateralusOS — PC Speaker Driver
 * =======================================================================
 * PIT Channel 2 tone generation with non-blocking melodies.
 *
 * Copyright (c) 2025 bad-antics. All rights reserved.
 * ======================================================================= */

#ifndef LATERALUS_SPEAKER_H
#define LATERALUS_SPEAKER_H

#include "../gui/types.h"

/* Port I/O (defined in kernel_stub.c) */
extern void    outb(uint16_t port, uint8_t val);
extern uint8_t inb(uint16_t port);

/* -- Tone control ------------------------------------------------------- */

/* Play a tone at given frequency (Hz). Runs until speaker_stop(). */
void speaker_play_tone(uint32_t freq);

/* Stop the current tone */
void speaker_stop(void);

/* Start a timed tone that auto-stops after duration_ms.
   Requires speaker_tick() to be called from the timer. */
void speaker_start_timed(uint32_t freq, uint32_t duration_ms,
                          uint64_t current_tick);

/* Call from timer ISR / main loop at 1kHz to handle auto-stop and melodies */
void speaker_tick(uint64_t current_tick);

/* -- Pre-defined sounds ------------------------------------------------- */

/* Schedule a startup melody (ascending C-E-G-C) */
void speaker_boot_chime(uint64_t current_tick);

/* Schedule an error beep (low tone) */
void speaker_error_beep(uint64_t current_tick);

/* Schedule a short keyclick sound */
void speaker_keyclick(uint64_t current_tick);

/* Schedule a window-open chime */
void speaker_window_open(uint64_t current_tick);

/* Schedule a notification sound */
void speaker_notify(uint64_t current_tick);

/* Is a sound currently playing? */
uint8_t speaker_is_playing(void);

#endif /* LATERALUS_SPEAKER_H */
