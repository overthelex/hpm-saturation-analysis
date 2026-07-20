# Certified Penetration-Safety Envelopes for Directed-Energy Area Defense against Adversarial Drone Swarms

**Research proposal · v0.1 · 2026-07-20**

> Written in English as a submission skeleton (target venues are anglophone). Companion
> analysis in this repo (`hpm-saturation-model.md`, `hectare-results.md`,
> `zenith-drop-results.md`) provides the calibrated simulator and the empirical phenomena
> this proposal formalizes.

---

## 1. Abstract

Directed-energy (high-power-microwave, HPM) weapons are being fielded as the primary
counter to drone swarms, on the premise that a single "one-to-many" pulse defeats many
targets at once. Yet whether a given emplacement actually *holds* against an adversarial
swarm — and against which swarm configurations it fails — is decided today by ad-hoc
live-fire demos, not by any principled guarantee. We propose to import and extend the
machinery of **certified robustness** from machine learning to physical area defense: given
a defense configuration `d`, compute a **certified penetration-safety envelope** `A_safe(d)`
— a region of attacker configurations for which the defense provably holds (leak below a
threshold), with a stated statistical confidence — together with the **worst-case adversarial
swarm** `a*` that maximizes penetration. The core technical problem is that the input space
is a structured, physically-constrained *attack configuration* (swarm size, approach
geometry, altitude, target hardening, timing), and the objective is a stochastic, expensive,
black-box simulation with a **rare-event** tail near the safe region. We combine (i)
level-set active learning of the failure boundary, (ii) physics-structured black-box
adversarial search, and (iii) rare-event estimation for statistical certification. As a
sharp validation, we ask whether the adversarial search **rediscovers known vulnerability
modes** (the zenith ballistic drop; the hardening-induced range collapse `R_eff ∝ 1/E_kill`)
without being told they exist. Contributions: a formal certificate for area defense, a
sample-efficient method to compute it, and an open, calibrated benchmark simulator.

---

## 2. Positioning: field and gap

The work sits at the intersection of **operations research (counter-UAS / salvo & raid
theory)**, **applied probability (stochastic geometry, rare-event simulation)**, **algorithmic
game theory (attacker–defender / security games)**, and **trustworthy ML (certified
robustness, adversarial examples)**. The novelty is a *methodological transfer* that turns an
engineering simulation into a provable statement about a physical system.

**What exists (and why it is not this):**
- *Certified robustness in ML* — randomized smoothing (Cohen et al., 2019), convex/IBP
  certificates (Wong & Kolter, 2018) — certifies a classifier over an `L_p` ball of a fixed
  input. Here the "input" is a structured physical attack, the model is a black-box
  stochastic simulator, and the perturbation set is a physics-constrained budget, not an
  `L_p` ball.
- *Falsification / testing of cyber-physical systems* — S-TaLiRo, Breach, temporal-logic
  falsification (Fainekos & Pappas; Donzé) — finds **one** counterexample. We instead want the
  **certified safe set** and its geometry, plus the scaling of the boundary.
- *Stackelberg security games* (Tambe et al.) — solve allocation equilibria on discrete/graph
  structures; they do not certify a continuous physics-constrained penetration boundary.
- *Counter-UAS / DEW OR* — salvo models (Hughes, 1995), Probability of Raid Annihilation
  (DTIC ADA444529) — give aggregate exchange metrics, not a per-configuration certificate or
  a learned failure manifold.
- *Level-set estimation & Bayesian optimization* (Gotovos et al., 2013; Bryan et al.'s
  straddle; safe BO) and *rare-event simulation* (subset simulation, Au & Beck, 2001;
  multilevel splitting) — are our **tools**, not previously combined into a certificate for
  adversarial physical defense.

**The gap we fill:** a *certified penetration-safety envelope* for directed-energy area
defense — the first framework that (a) defines a statistical safety certificate over a
structured attack space, (b) computes it sample-efficiently for a black-box stochastic
defense simulator with a rare-event tail, and (c) is validated by automatic rediscovery of
physically-grounded adversarial modes.

---

## 3. Formal problem

**System as a stochastic map.** Let `d ∈ D` be a defense configuration (aperture count `M`,
positions, beam half-angle `θ`, effective range `R_eff`, engagement cycle `t_c`, one-to-many
capacity `n_cone`, elevation limit `el_max`, mobility `orbit_rate`, kinetic-layer budget, …)
and `a ∈ A` an attack configuration (swarm size `N`, approach point process / scenario, ISR
level, altitude distribution, per-drone hardening `E_kill`, drop parameters, timing). A
simulator `S` maps them to a penetration (leak) fraction under randomness `ω`:

```
leak = S(d, a; ω) ∈ [0,1],     L(d,a) = E_ω[ S(d,a; ω) ].
```

**Failure boundary.** Fix a leak threshold `τ` (e.g. τ = 1/N for "≥1 penetrator", or τ = 0.1).
For a fixed defense `d`, the **failure manifold** is the level set

```
∂_τ(d) = { a ∈ A : L(d,a) = τ },
```

separating `A_safe(d) = { a : L(d,a) < τ }` from the penetrated region.

**Certificate.** A **certified penetration-safety envelope** is a set `Â ⊆ A` and a
confidence `1−α` such that

```
Pr[ ∀ a ∈ Â :  L(d,a) < τ ]  ≥  1 − α,
```

where the outer probability is over the estimation procedure (surrogate + finite samples).
Dually, the **adversarial swarm** is `a*(d) = argmax_{a ∈ A_budget} L(d,a)`, and the defense
is *certified* on `A_budget` iff `L(d, a*(d)) < τ`.

**Why hard.** `L` is (i) black-box and non-differentiable, (ii) expensive (each evaluation is
a Monte-Carlo of a 3-D agent simulation), (iii) stochastic with heteroscedastic noise, and
(iv) **rare-event**: over most of `A_safe`, `S = 0` for nearly all seeds, so naïve Monte-Carlo
cannot estimate small penetration probabilities or locate the boundary from the safe side.

---

## 4. Method

**M1 — Failure-boundary active learning.** Model `L(d,·)` with a heteroscedastic Gaussian
process (or Bayesian NN) surrogate `Ĝ`. Use level-set estimation acquisition (LSE / straddle:
sample where the surrogate is most ambiguous about `L ⋛ τ`, i.e. maximize
`|μ(a)−τ| − β·σ(a)` sign-straddling) to concentrate queries on `∂_τ` rather than uniformly.
Deliverable: an ε-accurate boundary at a fraction of the query budget of dense Monte-Carlo.

**M2 — Physics-structured adversarial search.** Find `a*` by gradient-free optimization
(CMA-ES / Bayesian optimization) over `A`, respecting physical constraints (kinematics,
altitude ≤ range, timing feasibility) via reparameterization and penalty. This is the
black-box analogue of PGD for a physical adversary. **Validation hook:** does the search
autonomously rediscover the zenith ballistic drop and the hardening collapse? Automatic
rediscovery of independently-derived modes is strong evidence the method finds *real*
vulnerabilities, not artifacts.

**M3 — Rare-event certification.** Near and inside `A_safe`, estimate the small penetration
probability `p(a) = Pr_ω[ S(d,a;ω) ≥ τ ]` with **subset simulation / multilevel splitting**
and importance sampling, instead of naïve MC. Turn the surrogate + rare-event estimates into
a statistical certificate via conformal prediction (distribution-free coverage) or PAC-style
bounds over `Ĝ`, yielding the `(Â, 1−α)` of §3 with quantified **tightness** (volume of `Â`
vs the true safe set estimated by dense MC on held-out slices).

**M4 — Sensitivity attribution → design guidance.** Compute Sobol indices and Shapley values
over defense/attack parameters to rank what governs the boundary (expected leaders: target
hardening `E_kill`, `el_max`, kinetic budget). This converts a certificate into actionable
design guidance ("to certify against budget `A_budget`, `el_max ≥ …` and kinetic magazine `≥ …`").

---

## 5. Experimental plan (on the calibrated simulator in this repo)

The repo's simulator is the oracle `S` (scenarios S0–S6, open-source-calibrated parameters).

- **E1 — Surrogate fidelity.** Learn `L` on low-dim slices (e.g. the `N × R_eff` hectare
  slice, already computed) and validate `Ĝ` against dense Monte-Carlo ground truth
  (boundary-error, calibration of `σ`).
- **E2 — Adversarial rediscovery.** Run M2 over the full `A`; measure whether `a*` recovers
  the zenith drop (leak≈1.0) and the `R_eff ∝ 1/E_kill` collapse. Report query cost to first
  breaking configuration.
- **E3 — Certification.** Produce `Â(d)` for representative defenses (4-corner hectare;
  ring `M`; hybrid with kinetic layer); report certificate validity (empirical coverage on
  held-out attacks) and tightness.
- **E4 — Rare-event.** Estimate small `p(a)` with subset simulation; report variance reduction
  vs naïve MC at fixed budget.
- **E5 — Sensitivity.** Sobol/Shapley ranking; check it recovers the hardening / `el_max`
  dominance found analytically.

**Metrics:** boundary-estimation error vs dense-MC; sample efficiency (queries to ε-boundary);
certificate empirical coverage (should ≥ 1−α) and tightness (|Â| / |A_safe|); rare-event
estimator relative variance; attribution fidelity.

---

## 6. Contributions

1. **Formal framework** — the certified penetration-safety envelope and adversarial-swarm
   objective for area defense (§3).
2. **Method** — a sample-efficient pipeline combining level-set active learning,
   physics-structured black-box adversarial search, and rare-event statistical certification
   (§4).
3. **Empirical validation** — automatic rediscovery of independently-derived adversarial
   modes (zenith drop; hardening collapse) plus previously-unenumerated ones, on a calibrated
   directed-energy counter-swarm simulator.
4. **Design guidance** — sensitivity attribution that turns certificates into siting/sizing
   recommendations (kinetic budget, `el_max`, mobility).
5. **Open benchmark** — the simulator and attack/defense configuration space as a reproducible
   testbed for certified physical-defense research.

---

## 7. Anticipated theoretical connection (bridge to a companion result)

The learned boundary `∂_τ(d)` empirically exhibits a **sharp threshold** in swarm size (leak
jumps from 0 to high at a critical `N_c`; cf. `hectare-results.md`). A companion analytical
strand (a separate paper) can model this as a **phase transition** with a scaling law
`N_c ~ f(θ, t_c, R_eff, M)` derived from the angular/temporal saturation of §5 of the model.
Citing it lets this paper *explain* the boundary's shape rather than only estimate it — a
strong "learn + prove" pairing, but each half stands alone.

---

## 8. Venues and timeline

- **Primary (methods/AI):** AAMAS or AAAI (attacker–defender, certification, multi-agent).
  GameSec for the security-game framing.
- **Journal (depth):** *Journal of Defense Modeling & Simulation*, *Reliability Engineering &
  System Safety* (certification/rare-event angle), or *Naval Research Logistics* (OR).
- **Rough timeline (~9–11 mo):** formalization + surrogate (1–3) → adversarial search &
  rediscovery (3–5) → certification method (5–8) → rare-event + sensitivity (7–9) →
  writing (9–11).

---

## 9. Risks and limitations

- **Simulator fidelity.** Parameters are order-of-magnitude on open sources; the certificate
  is "certified *with respect to the model*." Mitigation: the method is fidelity-agnostic and
  transfers verbatim to a higher-fidelity or classified simulator; state this scope honestly.
- **Dimensionality of certification.** Certifying over a high-dim `A` is hard. Mitigation:
  structured decomposition (certify per scenario family), and report certified sub-envelopes
  rather than a single global set.
- **Rare-event bias.** Subset simulation can under-cover; validate against dense MC on
  low-dim held-out slices.
- **Novelty defense.** Be explicit that falsification finds one counterexample while we
  certify a set — reviewers from the CPS-testing community will probe this boundary.

---

## 10. Ethics and dual-use

The work is framed **defensively**: it certifies that a defense holds, or reveals a gap so it
can be closed (e.g. the top-attack hole → add an overhead kinetic layer). To keep it science
rather than weapon engineering, and to reduce dual-use exposure, we (i) abstract away from any
specific fielded weapon ("directed-energy area defense" with open, cited parameters), (ii)
model attacks only at the configuration level needed to locate defensive failure (no
operational routing or guidance design), and (iii) release the simulator and benchmark under
a research license with a responsible-use statement. All parameters trace to open sources.

---

## 11. Key references (to be expanded)

Cohen, Rosenfeld, Kolter (2019) *Certified adversarial robustness via randomized smoothing*.
· Wong & Kolter (2018) *Provable defenses via the convex outer adversarial polytope*.
· Gotovos, Casati, Hitz, Krause (2013) *Active learning for level set estimation*.
· Au & Beck (2001) *Estimation of small failure probabilities — subset simulation*.
· Fainekos & Pappas (2009); Donzé (2010) *Breach* — temporal-logic falsification of CPS.
· Tambe (2011) *Security and Game Theory*.
· Hughes (1995) *Salvo model of warships in missile combat*.
· DTIC ADA444529 — *Probability of Raid Annihilation*.
· Frazier (2018) *A tutorial on Bayesian optimization*.
· (companion) this repo — `hpm-saturation-model.md`, `zenith-drop-results.md`.
