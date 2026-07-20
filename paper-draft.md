# Certified Penetration-Safety Envelopes for Directed-Energy Area Defense against Adversarial Drone Swarms

**Working draft · v0.1 · 2026-07-20**

> Draft assembled from the E1–E3 prototypes in this repository. Numbers are from the
> order-of-magnitude simulator (`hpm-saturation-model.md`); treat as a preliminary-results
> skeleton, not a finished paper. E4 (rare-event tail certification) and E5 (sensitivity)
> are in progress.

---

## Abstract

High-power-microwave (HPM) weapons are being fielded as the primary counter to drone
swarms, on the premise that one "one-to-many" pulse defeats many targets at once. Whether a
given emplacement actually *holds* against an adversarial swarm — and against which swarm
configurations it fails — is today decided by ad-hoc live-fire demonstrations, not by any
principled guarantee. We import and extend the machinery of **certified robustness** from
machine learning to physical area defense. Given a defense configuration `d`, we compute a
**certified penetration-safety envelope** `Â`: a region of attacker configurations for which
the defense provably holds (penetration below a threshold) at a stated statistical
confidence, together with the **worst-case adversarial swarm** that maximizes penetration.
The technical obstacle is that the "input" is a structured, physically-constrained attack
configuration and the objective is a stochastic, expensive, black-box simulation with a
rare-event tail near the safe region. We combine (i) level-set active learning of the
failure boundary, (ii) physics-structured black-box adversarial search, and (iii) conformal
certification. On a calibrated directed-energy counter-swarm simulator we show that (E1) a
Gaussian-process surrogate under level-set active learning recovers the failure boundary
using 14% of a dense-grid budget and 79% more accurately than random sampling; (E2) black-box
adversarial search **autonomously rediscovers** two independently-derived vulnerability modes
(a zenith ballistic drop and a target-hardening range collapse) from a bare "maximize
penetration" objective; and (E3) a distribution-free conformal certificate yields a
certified-safe envelope with valid coverage, zero false-safe region, 93% tightness, and which
**survives an active adversarial search**.

---

## 1. Introduction

Cheap drone swarms have shifted the economics of air defense: a $10k airframe cannot be met
by a $1M interceptor at scale. High-power-microwave (HPM) directed-energy weapons answer this
with a soft-kill "one-to-many" pulse that disables the electronics of every drone in a beam
volume at negligible cost per shot. But directed energy has structural blind spots — a
beam can only point one way at a time (angular saturation), a ring of emitters cannot fire
inward without fratricide, and a soft-kill weapon cannot stop an inert falling mass. Whether
a fielded configuration is *safe* against a determined swarm is currently answered by
live-fire demonstrations that sample a handful of scenarios.

We ask instead for a **guarantee**: a certified region of attacker configurations for which a
given defense provably holds, and the worst-case attack that breaks it. This is precisely the
question **certified robustness** answers for machine-learning classifiers, and **falsification**
answers (partially) for cyber-physical systems. We transfer and adapt that machinery to
physical area defense.

**Contributions.**
1. A formal framework — the *certified penetration-safety envelope* and the adversarial-swarm
   objective for area defense (§3).
2. A method combining level-set active learning, physics-structured black-box adversarial
   search, and conformal certification, for a black-box stochastic defense simulator (§4).
3. Empirical validation on a calibrated directed-energy counter-swarm simulator, including
   **automatic rediscovery** of independently-derived adversarial modes (§5).

---

## 2. Related work

**Certified robustness in ML** (randomized smoothing, Cohen et al. 2019; convex/IBP
certificates, Wong & Kolter 2018) certifies a classifier over an `L_p` ball of a fixed input.
Our "input" is a structured physical attack, the model is a black-box stochastic simulator,
and the perturbation set is a physics-constrained budget. **Falsification of cyber-physical
systems** (S-TaLiRo; Breach — Fainekos & Pappas 2009; Donzé 2010) finds *one* counterexample;
we compute the *certified safe set* and verify it. **Stackelberg security games** (Tambe 2011)
solve allocation equilibria on discrete structures, not a continuous physics-constrained
penetration boundary. **Counter-UAS / DEW operations research** (salvo models, Hughes 1995;
Probability of Raid Annihilation) gives aggregate exchange metrics, not per-configuration
certificates. **Level-set estimation and Bayesian optimization** (Gotovos et al. 2013; safe
BO) and **rare-event simulation** (subset simulation, Au & Beck 2001) are our tools; we
combine them into a certificate for adversarial physical defense — the gap we fill.

---

## 3. Problem formulation

**System as a stochastic map.** A defense configuration `d ∈ D` (emitter count, positions,
beam half-angle `θ`, effective range `R_eff`, engagement cycle `t_c`, one-to-many capacity
`n_cone`, elevation limit, mobility, kinetic budget) and an attack configuration `a ∈ A`
(swarm size `N`, approach geometry, altitude, target hardening `E_kill`, timing) map through a
simulator `S` to a penetration (leak) fraction under randomness `ω`:

```
leak = S(d, a; ω) ∈ [0,1],   L(d,a) = E_ω[ S(d,a; ω) ].
```

**Failure boundary.** For a leak threshold `τ`, `∂_τ(d) = { a : L(d,a) = τ }` separates the
safe region `A_safe(d) = { a : L(d,a) < τ }` from the penetrated region.

**Certificate.** A certified penetration-safety envelope is a set `Â ⊆ A` and confidence
`1−α` with

```
Pr[ ∀ a ∈ Â : L(d,a) < τ ] ≥ 1 − α,
```

the outer probability over the estimation procedure. Dually the **adversarial swarm** is
`a*(d) = argmax_{a ∈ A_budget} L(d,a)`; the defense is certified on `A_budget` iff
`L(d, a*(d)) < τ`.

**Why hard.** `L` is black-box, non-differentiable, expensive (each evaluation is a
Monte-Carlo of a 3-D agent simulation), stochastic, and **rare-event** near `A_safe` (leak is
0 for most seeds).

*Simulator.* We use an open 3-D time-stepped agent model of directed-energy counter-swarm
engagement (angular/temporal saturation, fratricide no-fire regions, elevation gap, soft-kill
physics, optional kinetic layer), calibrated to open-source parameters and validated against
closed-form saturation thresholds (`hpm-saturation-model.md`; `README-sim.md`).

---

## 4. Method

**M1 — Failure-boundary active learning.** Model `L(d,·)` with a Gaussian-process surrogate
`Ĝ`. Query with a level-set (straddle) acquisition `1.96·σ(a) − |μ(a)−τ|`, concentrating
oracle calls on `∂_τ` rather than uniformly.

**M2 — Physics-structured adversarial search.** Find `a*` by gradient-free optimization
(differential evolution) over `A`, respecting physical constraints via reparameterization.
This is the black-box analogue of a white-box adversarial attack for a physical adversary.

**M3 — Conformal certification.** From a held-out calibration set, one-sided split-conformal
nonconformity scores `s_i = y_i − μ(x_i)` give a margin `q` (their `⌈(n+1)(1−α)⌉` order
statistic) and a distribution-free upper bound `U(a) = μ(a) + q` with
`Pr[L(a) ≤ U(a)] ≥ 1−α`. The certified-safe set is `Â = { a : U(a) < τ }`, verified by an
active adversarial search (M2) restricted to `Â`.

---

## 5. Experiments

We validate each method on a single-aperture 2-D slice `(θ, t_c)` at fixed `R_eff=500 m,
R_c=50 m, v=30 m/s, N=80`, chosen because it has a **closed-form failure boundary**
`Σ = S(θ)·t_c·v/(R_eff−R_c) = 1` for independent validation. Larger-`d` and multi-modal
attack spaces are used in E2.

### 5.1 E1 — surrogate & boundary recovery

At a tight budget of 24 oracle queries (14% of a dense 13×13 Monte-Carlo grid), the GP
surrogate recovers the failure boundary to **0.038 s** in `t_c`; level-set active learning is
**79% more accurate on the boundary** than same-budget random sampling (0.038 vs 0.179 s),
while global surrogate RMSE is comparable (0.027 vs 0.037). The learned and Monte-Carlo
boundaries both coincide with the analytic `Σ=1` curve.

![E1](analysis/e1_surrogate.png)

### 5.2 E2 — adversarial rediscovery

Against a calibrated 4-emitter defense (`θ=30°, n_cone=49, el_max=80°, R_eff=500 m`) that
holds against a direct attack (leak 0.000), black-box search with only a "maximize
penetration" objective **autonomously rediscovers two independently-derived modes**:
(1) a **zenith ballistic drop** — climb above the cone-of-silence floor (869 m) and free-fall,
immune to soft-kill (leak → 1.000); (2) a **hardening/`R_eff` collapse** — shield the drones
~22 dB, collapsing effective range 500 → 40 m (leak → 1.000). Both were derived analytically
before the search; the optimizer found them with no prior knowledge — evidence that the method
finds *real* vulnerabilities.

![E2](analysis/e2_trace.png)

### 5.3 E3 — certification

With `τ=0.15` and `1−α = 90%`, the conformal certificate passes all four checks:
**coverage 0.938** (≥0.90), **soundness 0.000** (no false-safe region), **tightness 0.929**
(recovers 93% of the truly-safe region), and **adversarial verification** — a black-box search
restricted to `Â` cannot exceed leak **0.125 < τ**. The certified-safe envelope sits
conservatively inside the true safe region, with no false-safe points; that margin is the
price of a sound distribution-free guarantee.

![E3](analysis/e3_certificate.png)

*(E4 — subset-simulation certification of the small penetration probability `Pr_ω[leak≥τ]`,
strengthening the marginal guarantee toward a per-config tail bound — in progress.)*

---

## 6. Discussion & limitations

The certificate is *with respect to the simulator model*; parameters are order-of-magnitude
on open sources, and the method is fidelity-agnostic — it transfers verbatim to a
higher-fidelity or classified simulator. Conformal coverage here is **marginal** (per-point);
a `∀ a ∈ Â` set-guarantee needs a union/rare-event strengthening (E4). Validation is on a 2-D
slice with a homoscedastic noise model; scaling certification to high-dimensional attack
spaces (structured decomposition; certify per scenario family) is the main open problem.
Ethically, the work is framed defensively — it certifies that a defense holds or reveals a gap
to close (e.g. the top-attack hole → add an overhead kinetic layer) — and abstracts away from
any specific fielded weapon.

---

## 7. Conclusion

We recast "does this air defense hold?" as a certification problem and transferred certified-
robustness machinery to physical directed-energy area defense. On a calibrated simulator, a GP
surrogate under level-set active learning recovers the failure boundary sample-efficiently,
black-box adversarial search autonomously rediscovers real vulnerability modes, and a conformal
certificate yields a verified penetration-safety envelope. The pieces compose into a pipeline
that turns an engineering simulation into a provable, adversarially-verified statement about a
physical defense.

## References

(abbreviated — see `research-proposal-certified-defense.md` §11)
Cohen et al. 2019 · Wong & Kolter 2018 · Gotovos et al. 2013 · Au & Beck 2001 ·
Fainekos & Pappas 2009 · Donzé 2010 · Tambe 2011 · Hughes 1995 · Frazier 2018.
