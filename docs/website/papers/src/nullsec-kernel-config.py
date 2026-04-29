#!/usr/bin/env python3
"""Render 'nullsec Kernel Configuration Guide' in canonical style."""
from pathlib import Path
from _lateralus_template import render_paper

OUT = Path(__file__).resolve().parents[1] / "pdf" / "nullsec-kernel-config.pdf"

render_paper(
    out_path=str(OUT),
    title="nullsec Kernel Configuration Guide",
    subtitle="Hardening, networking, and forensic capture for security research platforms",
    meta="bad-antics &middot; April 2026 &middot; nullsec / Lateralus Language Research",
    abstract=(
        "This guide documents the kernel configuration choices made for nullsec. "
        "The configuration balances security hardening (to protect the platform "
        "itself) with forensic visibility (to capture traffic and system calls "
        "for security research). We document every non-default kernel option, "
        "the rationale for each choice, and the trade-offs between hardening "
        "and capability. The guide applies to both the nullsec Linux build "
        "(x86-64) and the Lateralus OS kernel (RISC-V)."
    ),
    sections=[
        ("1. Hardening vs Capability Trade-Off", [
            "A security research platform faces a unique tension: it must be "
            "hardened against external attack (because researchers often run it "
            "on networks with adversarial traffic) while simultaneously providing "
            "deep visibility into its own operation (for analyzing malware, "
            "monitoring network captures, and performing forensic analysis).",
            "The nullsec kernel configuration resolves this by separating "
            "hardening (kernel-level protections) from capability (user-space "
            "tooling access). Hardening options that would prevent security "
            "research (e.g., restricting raw socket access) are kept disabled "
            "in research mode and enabled in lab mode.",
        ]),
        ("2. Memory Hardening", [
            "The following memory hardening options are enabled in both modes:",
            ("code",
             "CONFIG_RANDOMIZE_BASE=y          # KASLR: randomize kernel load address\n"
             "CONFIG_RANDOMIZE_MEMORY=y        # ASLR for kernel memory regions\n"
             "CONFIG_PAGE_TABLE_ISOLATION=y    # KPTI: mitigate Meltdown\n"
             "CONFIG_HARDENED_USERCOPY=y       # validate usercopy bounds\n"
             "CONFIG_SLAB_FREELIST_RANDOM=y    # randomize slab freelist order\n"
             "CONFIG_SLAB_FREELIST_HARDENED=y  # detect double-free in slab\n"
             "CONFIG_INIT_STACK_ALL_ZERO=y     # zero-initialize stack variables\n"
             "CONFIG_STACKPROTECTOR_STRONG=y   # stack canaries on all functions"),
            "These options provide defense-in-depth against kernel exploits "
            "that target memory corruption vulnerabilities. They have negligible "
            "performance impact (<2% on typical workloads).",
        ]),
        ("3. Network Visibility Options", [
            "For network security research, the kernel must allow raw socket "
            "access and promiscuous mode without dropping privileges. "
            "The following options are enabled in research mode only:",
            ("code",
             "CONFIG_PACKET=y                  # raw packet sockets (tcpdump)\n"
             "CONFIG_TUN=y                     # TUN/TAP for VPN and proxies\n"
             "CONFIG_NETFILTER=y               # packet filtering (iptables)\n"
             "CONFIG_NETFILTER_NETLINK=y       # nftables support\n"
             "CONFIG_IP_ADVANCED_ROUTER=y      # policy routing\n"
             "CONFIG_NET_IPIP=y                # IP-in-IP tunneling\n"
             "CONFIG_NET_IPGRE=y               # GRE tunneling"),
            "In lab mode (the isolated research environment), these options "
            "remain enabled but the nullsec capability system restricts them "
            "to specific user accounts with the <code>net_research</code> capability.",
        ]),
        ("4. Syscall Auditing and eBPF", [
            "All system calls are audited via the kernel audit subsystem. "
            "The nullsec audit configuration records: process creation and "
            "destruction, network connections, file opens and closes, and "
            "privilege escalation attempts.",
            ("code",
             "CONFIG_AUDIT=y                   # enable audit subsystem\n"
             "CONFIG_AUDITSYSCALL=y            # per-syscall audit records\n"
             "CONFIG_BPF=y                     # Berkeley Packet Filter\n"
             "CONFIG_BPF_SYSCALL=y             # BPF syscall for eBPF programs\n"
             "CONFIG_BPF_JIT=y                 # JIT-compile BPF programs\n"
             "CONFIG_HAVE_EBPF_JIT=y           # architecture supports eBPF JIT"),
            "eBPF programs provide a safe way to add custom telemetry without "
            "loading a kernel module. nullsec ships several eBPF programs for "
            "common research tasks: network traffic sampling, process execution "
            "tracing, and file system activity monitoring.",
        ]),
        ("5. Forensic Capture Configuration", [
            "For forensic analysis, the kernel is configured with persistent "
            "memory for crash dumps and a write-protected audit log partition:",
            ("code",
             "CONFIG_CRASH_DUMP=y              # kdump: capture kernel crash dumps\n"
             "CONFIG_PROC_VMCORE=y             # /proc/vmcore for crash analysis\n"
             "CONFIG_KEXEC=y                   # kexec for crash kernel loading\n"
             "CONFIG_KEXEC_FILE=y              # load crash kernel from file\n"
             "CONFIG_MAGIC_SYSRQ=y             # SysRq key for emergency access\n"
             "CONFIG_MAGIC_SYSRQ_SERIAL=y      # SysRq over serial port"),
            "The audit log is stored on a separate partition with the "
            "<code>dm-integrity</code> device mapper to detect offline tampering. "
            "The partition key is stored in the TPM, ensuring the audit log "
            "is unreadable without physical access to the TPM chip.",
        ]),
        ("6. Disabled Options and Rationale", [
            "The following options are explicitly disabled in nullsec to reduce "
            "attack surface:",
            ("code",
             "# CONFIG_MODULES is not set           # no loadable kernel modules\n"
             "# CONFIG_KEXEC_SIG_FORCE is not set   # allow unsigned kexec for research\n"
             "# CONFIG_BLUETOOTH is not set          # no Bluetooth (unused, reduces attack surface)\n"
             "# CONFIG_FIREWIRE is not set           # no FireWire DMA (security risk)\n"
             "# CONFIG_THUNDERBOLT is not set        # no Thunderbolt DMA attacks"),
            "The most significant disabled option is <code>CONFIG_MODULES</code>: "
            "disabling loadable kernel modules eliminates an entire class of "
            "privilege escalation attacks. All required drivers are compiled into "
            "the kernel. This limits hardware compatibility but improves security.",
        ]),
        ("7. Lateralus OS Equivalent Configuration", [
            "The Lateralus OS kernel (used in the RISC-V nullsec variant) "
            "provides equivalent capabilities via its capability-based security "
            "model rather than Linux's sysctl/capabilities approach:",
            ("code",
             "// Lateralus OS security configuration (capability table)\n"
             "const RESEARCH_CAPS: [Capability] = [\n"
             "    Capability::NetRaw,       // raw socket access\n"
             "    Capability::NetPromiscuous, // promiscuous mode\n"
             "    Capability::AuditRead,    // read audit log\n"
             "    Capability::CrashDump,    // access crash dumps\n"
             "    Capability::EbpfLoad,     // load eBPF programs\n"
             "];"),
            "The Lateralus OS model is more fine-grained than Linux's capability "
            "system: capabilities are scoped to specific resources (e.g., "
            "<code>NetRaw(interface: \"eth0\")</code>) rather than system-wide.",
        ]),
        ("8. Build and Verification", [
            "The nullsec kernel is built reproducibly using the Lateralus build "
            "system. The kernel configuration is version-controlled in the "
            "nullsec repository; any change to the configuration requires a "
            "review approval from a nullsec core maintainer.",
            ("code",
             "# Build the nullsec kernel\n"
             "ltl build --config nullsec-kernel.config linux-kernel\n\n"
             "# Verify the binary matches the published hash\n"
             "sha256sum bzImage\n"
             "# d8f3a2... (matches nullsec/releases/latest/SHA256SUMS)"),
            "The SHA-256 of each kernel image is published with each nullsec "
            "release and should be verified before booting any nullsec image.",
        ]),
    ],
)

print(f"wrote {OUT}")
