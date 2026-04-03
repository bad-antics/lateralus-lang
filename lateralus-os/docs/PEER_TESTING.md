# LateralusOS — Peer Testing Plan

**Version 1.0 | Copyright (c) 2025 bad-antics. All rights reserved.**

---

## 1. Overview

This document defines the security framework, distribution process, and
feedback system for LateralusOS peer testing. The goal is to expand testing
coverage while protecting proprietary intellectual property.

---

## 2. Security Controls

### 2.1 Build Watermarking

Every test build distributed to a peer tester contains a **unique,
cryptographically verifiable watermark** embedded at multiple levels:

| Layer        | Method                              | Detection |
|-------------|--------------------------------------|-----------|
| Binary      | Unique byte sequences in .rodata     | Hex scan  |
| Filesystem  | /etc/lateralus/watermark.sig         | File read |
| Kernel      | Embedded in kernel log banner        | Serial    |
| Network     | Mesh agent reports build ID          | Remote    |
| Crypto      | HMAC-SHA256 of (build_id + tester_id)| Verify    |

Watermarks are generated using `tools/mkimage.py --watermark <tester_id>`
and verified with `crypto_svc::verify_watermark()`.

### 2.2 Build Expiration

Test builds include a **time bomb** that disables the OS after a configured
period:

- Default expiration: **30 days** from build date
- Grace period: **7 days** of warnings before hard stop
- Renewal: New build required (with fresh watermark)
- Master builds (proprietary): No expiration

### 2.3 Feature Gating

Test builds have certain features **disabled or limited**:

| Feature              | Test Build        | Master Build    |
|---------------------|-------------------|------------------|
| Compiler source     | Obfuscated        | Full source      |
| Encryption engine   | API only          | Full source      |
| Mesh deployment     | Local only        | Full mesh        |
| Max processes       | 16                | 256              |
| Debug logging       | Always on         | Configurable     |
| Telemetry           | Required          | Optional         |

### 2.4 Anti-Tamper

- Binary integrity checks on boot (SHA-256 of kernel sections)
- Obfuscated proprietary modules (compiler, crypto engine)
- Stack canaries and control-flow integrity in security-critical paths
- No debug symbols in test distributions
- Serial output includes build fingerprint

---

## 3. Tester Onboarding

### 3.1 Requirements

Peer testers must:

1. Sign a **Non-Disclosure Agreement** (NDA)
2. Provide hardware specifications for target test machines
3. Agree to telemetry data collection during testing
4. Report findings exclusively through the designated channel
5. Destroy all test builds upon request or expiration

### 3.2 NDA Terms (Summary)

- **Duration**: 2 years from last access to test materials
- **Scope**: All LateralusOS internals, architecture, capabilities
- **Permitted**: Discussing publicly available features only
- **Prohibited**: Source code sharing, binary redistribution,
  reverse engineering, benchmark publication without approval
- **Breach**: Immediate access revocation + legal remedies

### 3.3 Tester Tiers

| Tier       | Access Level         | Max Testers | Requirements        |
|-----------|---------------------|-------------|---------------------|
| Alpha     | Full kernel + shell  | 3           | NDA + track record  |
| Beta      | Single edition       | 10          | NDA                 |
| Community | Freeware edition     | Unlimited   | Terms acceptance    |

---

## 4. Test Distribution Process

### 4.1 Build Pipeline

```
Source → Compile → Watermark → Sign → Encrypt → Distribute
         ↓           ↓          ↓        ↓          ↓
      ltlc+gcc    mkimage    sha256   gpg/age   secure channel
```

### 4.2 Distribution Channels

- **Alpha**: Encrypted archive via secure file transfer (age + SSH)
- **Beta**: Password-protected download link (time-limited, single-use)
- **Community**: Public download (freeware editions only)

### 4.3 Build Commands

```bash
# Alpha build for tester "alice"
make EDITION=research clean kernel
python tools/mkimage.py \
    --kernel build/lateralus.elf \
    --edition research \
    --watermark "alice-2025-alpha" \
    --sign \
    
    --output builds/lateralus-research-alice.iso

# Verify watermark
python -c "
from tools.mkimage import sha256_file
print(sha256_file('builds/lateralus-research-alice.iso'))
"
```

---

## 5. Testing Focus Areas

### 5.1 Phase 1: Boot & Stability (Weeks 1-2)

- [ ] Boot on QEMU (x86_64, ARM, RISC-V)
- [ ] Boot on real hardware (if available)
- [ ] Kernel panic handling — trigger and verify recovery
- [ ] Memory stress — allocate/free cycles
- [ ] Scheduler — spawn max processes, verify preemption
- [ ] Timer accuracy — verify tick rate

### 5.2 Phase 2: I/O & Drivers (Weeks 3-4)

- [ ] Serial output — all log levels
- [ ] VGA display — all colors, scrolling, cursor
- [ ] Keyboard — all keys, modifiers, special combos
- [ ] PCI enumeration — correct device detection
- [ ] Disk — read/write/verify sectors
- [ ] Network — NIC detection, MAC address, basic TX/RX

### 5.3 Phase 3: Filesystem & Shell (Weeks 5-6)

- [ ] LateralusFS — format, mount, create/read/write/delete files
- [ ] FAT32 — mount USB/SD, read files
- [ ] Shell — all built-in commands
- [ ] Pipeline operator (`|>`) in shell
- [ ] Environment variables
- [ ] Command history

### 5.4 Phase 4: Services & Mesh (Weeks 7-8)

- [ ] Crypto service — key generation, encrypt/decrypt cycle
- [ ] System monitor — stats accuracy
- [ ] Mesh agent — node discovery on local network
- [ ] Mesh deploy — push agent to connected node
- [ ] IPC — channels, message queues, shared memory

### 5.5 Phase 5: Edition-Specific (Weeks 9-10)

- [ ] Industrial — real-time scheduling, watchdog
- [ ] Research — data acquisition, large heap
- [ ] Embedded — minimal footprint, cooperative scheduling
- [ ] Workstation — full feature set

---

## 6. Feedback System

### 6.1 Bug Reports

Testers submit bug reports with:

- **Build ID**: From `/etc/lateralus/watermark.sig` or serial banner
- **Edition**: Which edition was being tested
- **Steps to reproduce**: Exact commands/actions
- **Expected vs actual**: What should happen vs what happened
- **Serial log**: Attached serial output (mandatory)
- **Screenshots**: VGA output if applicable
- **Hardware**: CPU, RAM, storage, NIC details

### 6.2 Severity Levels

| Level    | Description                          | Response Time |
|----------|--------------------------------------|---------------|
| P0       | Kernel panic / data loss             | 24 hours      |
| P1       | Feature broken, no workaround        | 48 hours      |
| P2       | Feature broken, workaround exists    | 1 week        |
| P3       | Minor issue / cosmetic               | Next release  |

### 6.3 Communication

- **Primary**: Designated private repository (issues/discussions)
- **Urgent (P0)**: Direct message to bad-antics
- **Updates**: Weekly build notes + changelog

---

## 7. Tester Credits

All peer testers who contribute meaningful feedback will receive:

- **Named credit** in CREDITS.md and release notes
- **Early access** to new editions and features
- **Priority consideration** for future collaboration
- **Community freeware license** in perpetuity

Credit format:
```
## Peer Testers
- [Name/Handle] — [Edition(s) tested] — [Contribution summary]
```

---

## 8. Leak Response

In the event of unauthorized distribution:

1. **Identify source** via watermark verification
2. **Revoke access** for identified tester
3. **Rotate keys** and watermark scheme
4. **Legal action** per NDA terms
5. **Notify** remaining testers of security update

All test builds phone home (if network available) with a periodic
heartbeat containing only the build ID — no personal data. This enables
detection of unauthorized deployments.

---

*Peer Testing Plan v1.0 — Effective 2025*
*Maintained by bad-antics*
