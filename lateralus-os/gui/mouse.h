/* =======================================================================
 * LateralusOS — PS/2 Mouse Driver
 * =======================================================================
 * Handles IRQ12 (PS/2 mouse) — decodes 3-byte packets into dx/dy/btns.
 * ======================================================================= */

#ifndef LATERALUS_MOUSE_H
#define LATERALUS_MOUSE_H

#include "types.h"

/* -- Mouse state -------------------------------------------------------- */

typedef struct {
    int8_t   dx;
    int8_t   dy;
    uint8_t  left;
    uint8_t  right;
    uint8_t  middle;
    uint8_t  packet[3];
    uint8_t  cycle;        /* which byte of the 3-byte packet we're on */
    uint8_t  ready;        /* 1 when a full 3-byte packet is ready */
} MouseState;

/* -- API ---------------------------------------------------------------- */

/* Initialize the PS/2 mouse (enable IRQ12, send commands) */
void mouse_init(void);

/* Feed a byte from the mouse data port (called from IRQ12 handler) */
void mouse_handle_byte(uint8_t byte);

/* Get current decoded mouse state */
MouseState *mouse_get_state(void);

#endif /* LATERALUS_MOUSE_H */
