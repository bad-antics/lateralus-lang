#!/usr/bin/env python3
"""Render 'Indefinite Off-Grid Power via HHO Fuel Cells' in canonical style."""
from pathlib import Path
from _lateralus_template import render_paper

OUT = Path(__file__).resolve().parents[1] / "pdf" / "indefinite-off-grid-hho-fuel-cells.pdf"

render_paper(
    out_path=str(OUT),
    title="Indefinite Off-Grid Power via HHO Fuel Cells",
    subtitle="Closed-loop hydrogen generation, storage, and recombination for sustained off-grid energy",
    meta="bad-antics &middot; April 2026 &middot; Off-Grid Systems Research",
    abstract=(
        "This paper describes a closed-loop off-grid energy system based on "
        "HHO (hydrogen-oxygen, 'Brown's gas') electrolysis and recombination. "
        "The system uses surplus solar or wind energy to electrolyze water into "
        "hydrogen and oxygen gas; the gases are stored and later recombined in "
        "a fuel cell or combustion generator to produce electricity on demand. "
        "The closed loop uses water as both the energy storage medium and the "
        "reaction product, eliminating fuel replenishment. This paper analyzes "
        "the thermodynamic efficiency, safety requirements, and practical "
        "implementation of such a system at the 5-50 kW scale."
    ),
    sections=[
        ("1. The Closed-Loop Concept", [
            "A conventional off-grid solar system stores energy in lead-acid or "
            "lithium batteries. Batteries degrade over 3-10 year cycles, require "
            "replacement, and cannot store energy for seasonal variation. An HHO "
            "closed-loop system has different characteristics:",
            ("code",
             "Energy source (solar/wind)\n"
             "    → Electrolyzer (splits H2O → H2 + O2)\n"
             "    → Gas storage (compressed H2 and O2 tanks)\n"
             "    → Fuel cell or H2 generator (recombines H2 + O2 → H2O + electricity)\n"
             "    → Water recapture (returns H2O to electrolyzer feed)\n"
             "    → (cycle repeats)"),
            "The critical property is that water is neither consumed nor depleted: "
            "the same water molecules cycle through electrolysis and recombination "
            "indefinitely. The energy store is the gas pressure in the tanks, "
            "not the chemical state of a battery.",
        ]),
        ("2. Thermodynamic Efficiency Analysis", [
            "The round-trip efficiency of the HHO cycle is constrained by physics:",
            ("code",
             "Electrolysis (practical):   55–70% efficient (LHV basis)\n"
             "Gas compression:            90–95% efficient\n"
             "Storage (30-day):           ~99% (minimal gas loss with quality seals)\n"
             "Fuel cell (PEM):            50–60% efficient\n"
             "                            ────────────────────────────\n"
             "Round-trip:                 25–40% (vs. 85–95% for Li-ion)"),
            "The round-trip efficiency is lower than battery storage, but this "
            "is the correct comparison for seasonal storage (months, not hours). "
            "At seasonal timescales, battery self-discharge and degradation "
            "dominate; HHO tanks lose negligible pressure over months.",
        ]),
        ("3. Electrolyzer Design", [
            "For the 5-50 kW scale, alkaline electrolyzers (KOH electrolyte) "
            "provide the best balance of cost, efficiency, and durability. "
            "PEM electrolyzers are more efficient but significantly more expensive "
            "and sensitive to water purity.",
            ("code",
             "Design parameters (10 kW system):\n"
             "  Input power:        10 kW DC at 48-400V\n"
             "  H2 production:      ~1.8 Nm3/hr at 10 kW (LHV)\n"
             "  O2 production:      ~0.9 Nm3/hr (stoichiometric)\n"
             "  Electrolyte:        25% KOH solution\n"
             "  Operating temp:     60-80°C (optimal efficiency)\n"
             "  Cell voltage:       1.8-2.1 V per cell\n"
             "  Stack pressure:     10-30 bar (matched to storage)"),
            "Key design consideration: the electrolyzer must handle variable input "
            "power (solar curves). Alkaline electrolyzers tolerate 20-100% of rated "
            "power; minimum power threshold prevents electrolyte contamination.",
        ]),
        ("4. Gas Storage and Safety", [
            "Hydrogen storage at 200-350 bar in steel or composite cylinders is "
            "the practical choice at this scale. Safety requirements are stringent:",
            ("list", [
                "<b>Separation</b>: H2 and O2 tanks must be stored separately "
                "and in ventilated enclosures. Mixed HHO gas is explosive at "
                "4-75% H2 in air concentration.",
                "<b>Grounding</b>: all metallic surfaces must be bonded and "
                "grounded to prevent static discharge ignition.",
                "<b>Leak detection</b>: catalytic H2 sensors (not electrochemical) "
                "with automatic shutoff valves on any detected leak.",
                "<b>Pressure relief</b>: certified PRV on each tank, sized for "
                "worst-case thermal expansion (fire exposure scenario).",
                "<b>Purge lines</b>: inert gas (N2) purge capability for "
                "maintenance and emergency procedures.",
            ]),
        ]),
        ("5. Fuel Cell Selection and Sizing", [
            "For recombination, a PEM fuel cell stack is preferred over an H2 "
            "combustion generator for grid-quality AC output:",
            ("code",
             "PEM fuel cell (preferred):\n"
             "  Electrical efficiency:  50-60% (DC output)\n"
             "  Output quality:         DC → inverter → AC\n"
             "  Noise:                  near-silent\n"
             "  Maintenance:            membrane replacement every 5-10 years\n"
             "  Water output:           0.9 kg/kWh (recaptured)\n\n"
             "H2 combustion generator (alternative):\n"
             "  Electrical efficiency:  25-35%\n"
             "  Output quality:         AC direct (but requires governor)\n"
             "  Noise:                  loud (combustion)\n"
             "  Maintenance:            engine overhaul every 2000-5000 hours"),
            "The PEM fuel cell is the better choice for sustained off-grid use "
            "despite higher upfront cost. The combustion generator is suitable "
            "as backup for fault conditions.",
        ]),
        ("6. Water Management", [
            "Water quality is critical: the electrolyzer requires deionized water "
            "(< 1 µS/cm conductivity) and the fuel cell produces slightly acidic "
            "water (from membrane operation). The closed loop water management:",
            ("code",
             "Fuel cell water output\n"
             "    → Condensate collection tank\n"
             "    → Deionization column (mixed-bed resin)\n"
             "    → Conductivity sensor (reject if > 1 µS/cm)\n"
             "    → Electrolyzer feed tank\n"
             "    → (electrolyzer refill as needed)"),
            "The deionization resin requires periodic regeneration or replacement "
            "(approximately annually at 10 kW continuous operation). Total water "
            "in the loop: approximately 200-500 liters for a 10 kW / 500 kWh system.",
        ]),
        ("7. System Integration and Control", [
            "The system controller manages energy dispatch between three modes:",
            ("list", [
                "<b>Surplus mode</b>: solar/wind exceeds load. Excess power routed "
                "to electrolyzer. Electrolysis rate proportional to surplus.",
                "<b>Balance mode</b>: solar/wind matches load. Electrolyzer and "
                "fuel cell both idle. Battery buffer (small, for transients) absorbs variation.",
                "<b>Deficit mode</b>: solar/wind insufficient. Fuel cell activates "
                "to supplement. H2 consumption rate proportional to deficit.",
            ]),
            "The control algorithm is implemented as a Lateralus pipeline: "
            "sensor readings flow through the pipeline and emerge as actuator commands "
            "for the electrolyzer power controller and fuel cell load regulator.",
        ]),
        ("8. Practical Economics", [
            "At current (2026) component prices, the HHO closed-loop system is "
            "economically competitive with battery storage only for storage durations "
            "exceeding approximately 3 days:",
            ("code",
             "10 kW system, 500 kWh storage:\n"
             "  Li-ion battery system:     ~$75,000 (15-year life, 2 replacement cycles)\n"
             "  HHO closed-loop system:    ~$120,000 (25+ year life, no major replacement)\n"
             "  Break-even duration:       >72 hours storage requirement\n\n"
             "For seasonal storage (months), HHO is the only practical option —\n"
             "no battery chemistry can economically store energy across seasons."),
            "The primary use case is remote locations with extreme seasonal variation: "
            "high northern latitudes, isolated islands, and research stations where "
            "resupply is expensive and infrequent.",
        ]),
    ],
)

print(f"wrote {OUT}")
