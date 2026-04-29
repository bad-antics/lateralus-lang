#!/usr/bin/env python3
"""Render 'nullsec Tool Protocol' in canonical style."""
from pathlib import Path
from _lateralus_template import render_paper

OUT = Path(__file__).resolve().parents[1] / "pdf" / "nullsec-tool-protocol.pdf"

render_paper(
    out_path=str(OUT),
    title="nullsec Tool Protocol",
    subtitle="The typed inter-tool communication protocol for nullsec pipeline tools",
    meta="bad-antics &middot; April 2026 &middot; nullsec / Lateralus Language Research",
    abstract=(
        "nullsec tools communicate via a typed protocol that enables pipeline composition "
        "without text parsing. The protocol defines: a binary-encoded message format "
        "(CBOR-based), a typed schema registry for common security data types (hosts, "
        "ports, vulnerabilities, credentials), and a streaming mode for large datasets. "
        "This paper specifies the protocol, the schema registry, and the rules for "
        "adding new schemas. It also describes how the protocol integrates with the "
        "Lateralus pipeline type system to provide compile-time validation of "
        "tool-to-tool connections."
    ),
    sections=[
        ("1. Why a Typed Protocol", [
            "Traditional Unix philosophy: tools communicate via plain text (grep, "
            "awk, sed form the glue). This works for simple cases but fails when "
            "tool output is structured: nmap XML, JSON APIs, binary captures. "
            "Each tool must implement its own parser for upstream tool output, "
            "creating a fan-out of brittle parsers.",
            "The nullsec protocol provides a typed binary message format. "
            "A tool that produces a <code>HostScanResult</code> need not serialize "
            "to text; the next tool receives the structured value directly. No "
            "parsers, no fragile grep patterns, no lost precision.",
        ]),
        ("2. Message Format: CBOR with Type Tags", [
            "Messages are encoded in CBOR (Concise Binary Object Representation, "
            "RFC 8949) with nullsec-specific type tags. Each message starts with "
            "a nullsec header:",
            ("code",
             "// Message envelope\n"
             "struct Message {\n"
             "    magic:      [u8; 4],  // 0x4E534543 ('NSEC')\n"
             "    version:    u16,\n"
             "    schema_id:  u32,      // identifies the payload type\n"
             "    payload_sz: u32,\n"
             "    payload:    CBOR,     // schema-typed CBOR value\n"
             "    checksum:   u32,      // CRC32 of header + payload\n"
             "}"),
            "The <code>schema_id</code> maps to an entry in the schema registry. "
            "The receiving tool looks up the schema, validates the payload against "
            "it, and deserializes into the corresponding Lateralus type.",
        ]),
        ("3. Schema Registry", [
            "The schema registry is a TOML file listing all known schema IDs "
            "and their Lateralus type names:",
            ("code",
             "# nullsec/schemas/registry.toml\n"
             "[schemas]\n"
             "1   = \"nullsec::schema::HostScanResult\"\n"
             "2   = \"nullsec::schema::PortResult\"\n"
             "3   = \"nullsec::schema::VulnReport\"\n"
             "4   = \"nullsec::schema::Credential\"\n"
             "5   = \"nullsec::schema::DnsRecord\"\n"
             "6   = \"nullsec::schema::HttpRequest\"\n"
             "7   = \"nullsec::schema::HttpResponse\"\n"
             "8   = \"nullsec::schema::CertificateInfo\""),
            "Adding a new schema requires: defining the Lateralus type in "
            "<code>nullsec::schema</code>, assigning it the next available ID, "
            "adding it to the registry TOML, and submitting a PR to the nullsec "
            "repository. The PR must include a round-trip test and a migration "
            "guide if the new schema supersedes an existing one.",
        ]),
        ("4. Streaming Mode", [
            "For large datasets (full /8 port scans, packet captures), "
            "the protocol supports streaming: a stream is a sequence of "
            "messages with the same schema ID, terminated by a sentinel "
            "end-of-stream message.",
            ("code",
             "// Streaming producer\n"
             "let stream = nullsec::Stream::new(schema::HOST_SCAN_RESULT);\n"
             "for host in scan_results {\n"
             "    stream.send(host)?;\n"
             "}\n"
             "stream.finish()?\n\n"
             "// Streaming consumer\n"
             "let incoming = nullsec::Stream::receive(schema::HOST_SCAN_RESULT);\n"
             "for result in incoming {\n"
             "    let r: HostScanResult = result?;\n"
             "    process(r);\n"
             "}"),
            "The streaming API backpressures automatically: the producer blocks "
            "if the consumer's receive buffer is full. This prevents memory "
            "exhaustion when scanning large networks.",
        ]),
        ("5. Pipeline Integration", [
            "The nullsec protocol integrates with the Lateralus pipeline type "
            "system: a tool's input and output schema IDs are part of its "
            "function signature. The compiler checks that adjacent tools in a "
            "pipeline have compatible schemas.",
            ("code",
             "// Tool signatures (from the nullsec crate documentation)\n"
             "fn port_scan(targets: Vec<IpNet>) -> Stream<HostScanResult>  // schema 1\n"
             "fn service_detect(host: HostScanResult) -> HostScanResult    // schema 1 in/out\n"
             "fn vuln_scan(host: HostScanResult) -> Stream<VulnReport>     // schema 3\n\n"
             "// Pipeline: compiler verifies schema compatibility at each boundary\n"
             "let report = [\"192.168.1.0/24\"]\n"
             "    |>> port_scan\n"
             "    |>  service_detect\n"
             "    |>> vuln_scan"),
        ]),
        ("6. Authentication and Integrity", [
            "In multi-host deployments (distributed scanning from multiple nodes), "
            "messages are authenticated with Ed25519 signatures. Each node has "
            "a long-term key pair; the signature covers the full message envelope "
            "including the header.",
            ("code",
             "struct AuthenticatedMessage {\n"
             "    message:   Message,\n"
             "    sender_id: Ed25519PublicKey,\n"
             "    signature: Ed25519Sig,\n"
             "}\n\n"
             "fn verify(msg: &AuthenticatedMessage) -> Result<(), AuthError> {\n"
             "    let body = encode_cbor(&msg.message);\n"
             "    ed25519::verify(&msg.sender_id, &body, &msg.signature)\n"
             "}"),
            "The signing key is stored in the nullsec trust store and rotated "
            "every 30 days. Nodes that have not rotated their keys are "
            "automatically quarantined by the cluster manager.",
        ]),
        ("7. Versioning and Forward Compatibility", [
            "Schema versions are included in the schema ID encoding: "
            "the upper 16 bits of the 32-bit schema ID are the schema "
            "version number, and the lower 16 bits are the schema identifier. "
            "A tool that receives a schema version higher than it supports "
            "can still process the known fields (forward compatibility is "
            "guaranteed by the CBOR map structure: unknown fields are ignored).",
            ("code",
             "// Schema ID encoding\n"
             "const HOST_SCAN_RESULT_V1: u32 = 0x0001_0001;\n"
             "const HOST_SCAN_RESULT_V2: u32 = 0x0002_0001;  // adds geolocation field\n\n"
             "// A v1 consumer receiving a v2 message:\n"
             "// - reads schema_id 0x0002_0001\n"
             "// - knows only v1 fields (host, open_ports, scan_time)\n"
             "// - ignores unknown geolocation field (CBOR map, forward-compatible)\n"
             "// - parses successfully"),
        ]),
        ("8. Reference Implementation", [
            "The reference implementation of the nullsec protocol is in "
            "<code>nullsec::proto</code>, a Lateralus library that provides "
            "the <code>Message</code>, <code>Stream</code>, and "
            "<code>AuthenticatedMessage</code> types, plus the CBOR "
            "serialization and deserialization for all registered schemas.",
            "The reference implementation is approximately 600 lines of "
            "Lateralus and is tested against 50 round-trip property tests "
            "(generated using the <code>quickcheck</code> library) and "
            "interoperability tests with a Python reference client.",
        ]),
    ],
)

print(f"wrote {OUT}")
