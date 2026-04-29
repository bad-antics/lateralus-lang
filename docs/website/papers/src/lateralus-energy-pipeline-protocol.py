#!/usr/bin/env python3
"""Render 'Lateralus Energy Pipeline Protocol' in canonical style."""
from pathlib import Path
from _lateralus_template import render_paper

OUT = Path(__file__).resolve().parents[1] / "pdf" / "lateralus-energy-pipeline-protocol.pdf"

render_paper(
    out_path=str(OUT),
    title="Lateralus Energy Pipeline Protocol",
    subtitle="A typed pipeline model for monitoring and controlling distributed energy systems",
    meta="bad-antics &middot; April 2026 &middot; Lateralus Language Research",
    abstract=(
        "This paper defines the Lateralus Energy Pipeline Protocol (LEPP), a "
        "typed data exchange protocol for distributed off-grid energy systems. "
        "LEPP uses the Lateralus pipeline model to express energy flows between "
        "generators, storage units, and loads. Each component exposes a typed "
        "pipeline interface; the system controller composes these interfaces into "
        "a whole-system pipeline. LEPP provides: real-time telemetry, "
        "deterministic fault response, and formal energy balance verification "
        "at the type level."
    ),
    sections=[
        ("1. Motivation", [
            "Off-grid energy systems consist of heterogeneous components from "
            "multiple vendors: solar charge controllers, battery management systems, "
            "inverters, generator controllers, and load management units. These "
            "components communicate via incompatible protocols (Modbus RTU, CAN bus, "
            "proprietary UART, or none at all).",
            "LEPP provides a unified typed interface layer. Each component exposes "
            "a LEPP adapter; the system controller communicates with all components "
            "through a single typed pipeline. Adapters translate between LEPP "
            "messages and the component's native protocol.",
        ]),
        ("2. Core Types", [
            "LEPP defines four core measurement types:",
            ("code",
             "// Power and energy\n"
             "record PowerSample  { watts: f32, timestamp: Instant }\n"
             "record EnergySample { watt_hours: f32, period_ms: u32 }\n\n"
             "// State of charge and voltage\n"
             "record BatteryState { soc_pct: f32, voltage_v: f32,\n"
             "                      current_a: f32, temp_c: f32 }\n\n"
             "// Component health\n"
             "record HealthStatus { component_id: ComponentId,\n"
             "                      fault_code: Option<FaultCode>,\n"
             "                      uptime_s: u64 }"),
            "All measurements are timestamped with monotonic clock values. "
            "The protocol uses 32-bit floats for measurements (sufficient for "
            "energy system precision) to reduce bandwidth on low-speed serial links.",
        ]),
        ("3. Pipeline Interface Definition", [
            "Each LEPP component exposes a typed pipeline interface with three channels:",
            ("code",
             "// LEPP component interface\n"
             "interface EnergyComponent {\n"
             "    // Telemetry: component pushes measurements\n"
             "    fn telemetry_stream() -> Pipeline<(), PowerSample>\n\n"
             "    // Control: controller pushes commands\n"
             "    fn control_sink() -> Pipeline<ControlCommand, Result<(), FaultCode>>\n\n"
             "    // Health: periodic health check\n"
             "    fn health_check() -> Pipeline<(), HealthStatus>\n"
             "}"),
            "The controller composes component pipelines into a system pipeline. "
            "Type checking at composition time verifies that control commands "
            "sent to a component match the commands it accepts — a command "
            "type mismatch is a compile error.",
        ]),
        ("4. Energy Balance Verification", [
            "LEPP uses phantom type parameters to track energy balance at the "
            "type level. The controller's power dispatch function is typed to "
            "reject configurations where generation is less than load:",
            ("code",
             "// Phantom types for energy accounting\n"
             "type Watts<N: u32>;   // N watts available\n\n"
             "fn dispatch<G: u32, L: u32>(\n"
             "    generation: PowerSource<Watts<G>>,\n"
             "    load:       LoadSink<Watts<L>>,\n"
             ") -> DispatchPlan\n"
             "where\n"
             "    G >= L  // compile error if generation < load\n"
             "{  ...  }"),
            "In practice, generation and load are dynamic values, so the phantom "
            "type check operates at the configuration level (static capacity "
            "planning) rather than the instantaneous dispatch level. Runtime "
            "balance is enforced by the fault propagation pipeline.",
        ]),
        ("5. Fault Propagation", [
            "LEPP uses the <code>|?></code> operator to propagate faults through "
            "the energy dispatch pipeline. A fault in any stage triggers the "
            "fault handler, which activates the safe shutdown sequence:",
            ("code",
             "fn energy_dispatch_loop(system: &SystemState) -> Result<(), Fault> {\n"
             "    system\n"
             "        |>  read_all_telemetry\n"
             "        |?> check_battery_limits       // fault if SOC < 10%\n"
             "        |?> check_generator_health     // fault if temp > 85°C\n"
             "        |>  compute_dispatch_plan\n"
             "        |?> send_control_commands      // fault on comms error\n"
             "        |>  log_dispatch_record\n"
             "}"),
            "When a fault is raised, the pipeline aborts and the fault is passed "
            "to the safe-shutdown handler. The handler follows a deterministic "
            "sequence: disconnect loads in priority order, then disconnect sources, "
            "then notify the operator.",
        ]),
        ("6. Transport Layer", [
            "LEPP messages are serialized using CBOR (Concise Binary Object "
            "Representation, RFC 8949) for compact encoding on serial links. "
            "The transport options are:",
            ("code",
             "Transport         Baud / bandwidth    Typical use\n"
             "-----------------------------------------------\n"
             "RS-485 (Modbus)   9600-115200 baud    Legacy components\n"
             "CAN 2.0B          1 Mbit/s            Modern components\n"
             "Ethernet/TCP      100 Mbit/s          Networked inverters\n"
             "Meshtastic/LoRa   250 kbaud            Remote monitoring"),
            "Each transport has a LEPP adapter that handles framing, CRC, and "
            "retry logic. The pipeline interface above the adapter is transport-"
            "agnostic; swapping a component's transport requires only replacing "
            "its adapter.",
        ]),
        ("7. Reference Implementation", [
            "The LEPP reference implementation is part of the Lateralus standard "
            "library under <code>lateralus-energy</code>. It provides:",
            ("list", [
                "Adapter implementations for Modbus RTU, CAN bus, and TCP.",
                "Simulator adapters for testing without physical hardware.",
                "A system dashboard that renders the energy pipeline in the terminal.",
                "A logging backend that records all telemetry to a SQLite database.",
            ]),
            ("code",
             "# Run the system dashboard against a QEMU-simulated system\n"
             "ltl run lateralus-energy::dashboard \\\n"
             "    --config examples/5kw-solar-hho.toml \\\n"
             "    --transport simulator"),
        ]),
        ("8. Future Work", [
            "Planned extensions to LEPP:",
            ("list", [
                "<b>Formal energy balance proofs</b>: use the Lateralus formal "
                "verification framework to prove that a given system configuration "
                "maintains energy balance under all possible fault scenarios.",
                "<b>Grid-tie mode</b>: extend LEPP to model bidirectional grid "
                "connection (net metering), where the grid acts as an infinite "
                "storage/source component.",
                "<b>Multi-site federation</b>: federate multiple off-grid sites "
                "via Meshtastic mesh networking, allowing peer-to-peer energy "
                "trading between proximate sites.",
            ]),
        ]),
    ],
)

print(f"wrote {OUT}")
