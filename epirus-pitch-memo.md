# Counter-Swarm Red-Team of Leonidas — Operational Envelope & Fixes

**One-page technical memo · Independent defensive analysis · 2026-07-20**

---

## Thesis

Leonidas' effector is strong — GaN solid-state power and one-to-many pulse make raw
*firepower* a non-bottleneck. The exploitable limits of any single-aperture HPM line are
**geometric, sensor, and thermal**, not energy. This memo defines *where* the public
"49 drones, one pulse" claim holds, *where* it breaks, and three fixes — two of which
independently validate Epirus' own roadmap (mobile Leonidas, Gen II) with numbers.

*All figures are order-of-magnitude on open-source assumptions (Wikipedia, Epirus press,
1/r² physics). With classified R_eff / θ / t_c / duty they re-solve in an hour. Method and
envelope are the product, not the specific numbers.*

---

## Three lead findings (napkin-verifiable)

**1 — Angular saturation, not power, sets the ceiling.**
A single aperture scans `S = 1/(1−cosθ)` sectors; revisit `T_r = S·t_c` vs target transit
`τ = (R_eff−R_c)/v`. **Breakthrough when `T_r > τ`, independent of N.** A pencil beam (5–10°)
saturates at **tens** of synchronized targets; a wide "shield" (30°) holds. This *is* the
"create a sector/shield in the sky" mode — quantified. Beam-footprint diameter at 500 m:
87 m (5°) vs 577 m (30°); a "seam" is literally the meters between footprints.

**2 — A ring of apertures has a by-design blind interior.**
Ring units point *outward*; the inward hemisphere is a no-fire zone (firing inward washes
the protected asset / opposite aperture — fratricide). No-fire half-angle to the asset
`α = arcsin(ρ/R_ring)` (up to ~37° for a tight ring). Plus a zenith gap of 0.4–6% of the
upper hemisphere by elevation limit. **A drone that crosses the ring is in the rear of all
M apertures at once** — this is the multi-altitude englobing attack, and it is real.

**3 — The exchange ratio inverts at the seam.**
Attritioning one aperture head-on costs the swarm ~150 airframes (~$2.2M) — CER ≈ 0.09,
defense-favorable. **But breaking through a geometric seam costs only ~50 airframes
(~$0.75M) — CER ≈ 0.03.** That collapse is the number a program office reacts to, and it
is exactly what the fixes below close.

---

## Three fixes (two validate Epirus' roadmap)

| Fix | What it closes | Payoff |
|---|---|---|
| **Mobility (repositioning apertures)** | Seam-routing needs current ISR; at 5 m/s an aperture moves 300 m in 60 s — past the seam the swarm aimed at | **Validates "Leonidas on wheels/legs" with numbers** |
| **Harden friendlies + inner kinetic bubble** | Shielding shrinks the fratricide arc; kinetics own the interior HPM can't fire into | Sizes the hybrid system offer |
| **Beam-width / t_c doctrine** | Wide-shield mode and shorter engage cycle push `T_r/τ` below 1 | Tunes existing hardware, no new build |

---

## What I'd deliver

1. **This envelope memo**, re-run on Epirus' real parameters (NDA) — exact `N_min`, leak
   curves, CER by configuration.
2. **A working simulation** (3D agent model; engine in progress) that reproduces the
   49-drone result and shows the seam where it fails — the demo that de-risks the doctrine.
3. **Siting + hybrid sizing doctrine**: M, ring radius, elevation staggering, kinetic
   magazine depth, EMCON to deny configuration knowledge.

Honest scope: I do not claim to beat the effector — the attack lives on geometry, sensor
saturation (track capacity `T_max`, not the pulse), and thermal duty over a 60-second
swarm. Every finding is defensive; every fix strengthens the product.

*Backing analysis: `hpm-saturation-model.md`, `hpm-swarm-sim-design.md`.*
