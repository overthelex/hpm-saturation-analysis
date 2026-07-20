#!/usr/bin/env Rscript
# Unified ggplot2 rendering of the E1-E4 experiment figures.
# Reads CSVs written by analysis/export_e_data.py. Outputs SVG + PNG.
# Run:  Rscript figures/make_e_figures.R
suppressMessages({library(ggplot2); library(dplyr); library(viridis); library(scales)})
setwd(dirname(sub("--file=", "", grep("--file=", commandArgs(FALSE), value = TRUE)[1])))

theme_pub <- function() theme_minimal(base_size = 13) +
  theme(panel.grid = element_blank(),
        plot.title = element_text(face = "bold", size = 14),
        plot.subtitle = element_text(color = "grey30", size = 9.5),
        strip.text = element_text(face = "bold", size = 11),
        legend.position = "right")
save_both <- function(p, name, w = 8, h = 5) {
  grDevices::svg(paste0(name, ".svg"), width = w, height = h); print(p); dev.off()
  grDevices::png(paste0(name, ".png"), width = w, height = h, units = "in", res = 130)
  print(p); dev.off(); cat("wrote", name, "\n")
}
# closed-form Sigma=1 boundary t_c*(theta) for the single-aperture slice
bnd_curve <- function(th_range) {
  th <- seq(th_range[1], th_range[2], length.out = 200)
  data.frame(theta = th, t_c = (500 - 50) / 30 * (1 - cos(th * pi / 180)))
}

## ---- E1: surrogate vs MC truth, with active-learning queries ----
g1 <- read.csv("data_e1_grid.csv"); q1 <- read.csv("data_e1_queries.csv")
long1 <- rbind(
  data.frame(theta = g1$theta, t_c = g1$t_c, value = g1$L_true,
             panel = "MC ground truth"),
  data.frame(theta = g1$theta, t_c = g1$t_c, value = g1$gp_mean,
             panel = "GP surrogate (active learning)"))
long1$panel <- factor(long1$panel, levels = c("MC ground truth",
                                               "GP surrogate (active learning)"))
q1$panel <- factor("GP surrogate (active learning)", levels = levels(long1$panel))
bnd <- bnd_curve(range(g1$theta))
pE1 <- ggplot(long1, aes(theta, t_c, fill = value)) +
  geom_raster(interpolate = TRUE) +
  facet_wrap(~panel) +
  scale_fill_viridis(name = "leak", limits = c(0, 1), oob = scales::squish) +
  geom_line(data = bnd, aes(theta, t_c), inherit.aes = FALSE, color = "white",
            linetype = "dashed", linewidth = 0.9) +
  geom_point(data = q1, aes(theta, t_c), inherit.aes = FALSE, color = "red",
             size = 1.6, shape = 21, fill = "red", stroke = 0.2) +
  coord_cartesian(expand = FALSE) +
  labs(title = "E1 — level-set active learning of the failure boundary",
       subtitle = "GP surrogate matches Monte-Carlo; red = 24 active-learning queries hug the boundary (dashed = analytic Σ=1)",
       x = "beam half-angle θ (deg)", y = "engagement cycle t_c (s)") +
  theme_pub()
save_both(pE1, "fig_e1_surrogate", 9.5, 4.4)

## ---- E2: adversarial-search traces ----
tr <- read.csv("data_e2_trace.csv"); base <- read.csv("data_e2_baseline.csv")$baseline_leak[1]
pE2 <- ggplot(tr, aes(eval, best_leak, color = search)) +
  geom_hline(yintercept = base, linetype = "dashed", color = "grey50") +
  annotate("text", x = Inf, y = base, label = sprintf("  naive direct (%.2f)", base),
           hjust = 1.02, vjust = -0.6, color = "grey40", size = 3) +
  geom_step(linewidth = 1.1, direction = "hv") +
  facet_wrap(~search) +
  scale_color_manual(values = c("geometry -> zenith drop" = "#1f77b4",
                                "hardening -> R_eff collapse" = "#d62728"),
                     guide = "none") +
  ylim(0, 1.02) +
  labs(title = "E2 — black-box adversarial search rediscovers both known modes",
       subtitle = "from a bare 'maximize penetration' objective; both routes drive a holding defense (0) to full breakthrough (1)",
       x = "oracle evaluations", y = "best leak found") +
  theme_pub()
save_both(pE2, "fig_e2_adversarial", 9, 4.2)

## ---- E3: conformal certified-safe envelope ----
g3 <- read.csv("data_e3_grid.csv"); meta <- read.csv("data_e3_meta.csv")
tau <- meta$tau[1]
cert <- g3 %>% filter(certified == 1)
fs <- g3 %>% filter(false_safe == 1)
pE3 <- ggplot(g3, aes(theta, t_c)) +
  geom_raster(aes(fill = L_true)) +
  scale_fill_gradient(name = "true leak", low = "grey92", high = "grey15") +
  geom_tile(data = cert, fill = "#2ca02c", alpha = 0.32) +
  geom_contour(aes(z = U), breaks = tau, color = "#2ca02c", linewidth = 1.0) +
  geom_contour(aes(z = L_true), breaks = tau, color = "cyan3", linewidth = 1.0) +
  {if (nrow(fs) > 0) geom_point(data = fs, color = "red", size = 1) } +
  geom_line(data = bnd_curve(range(g3$theta)), aes(theta, t_c), color = "white",
            linetype = "dotted", linewidth = 0.6) +
  coord_cartesian(expand = FALSE) +
  labs(title = "E3 — conformal penetration-safety certificate",
       subtitle = sprintf("green = certified-safe Â (U<τ, 90%% conf.); cyan = true boundary L=τ=%.2f; Â sits conservatively inside", tau),
       x = "beam half-angle θ (deg)", y = "engagement cycle t_c (s)") +
  theme_pub()
save_both(pE3, "fig_e3_certificate", 8, 5)

## ---- E4: rare-event tail CCDF ----
cc <- read.csv("data_e4_ccdf.csv"); mk <- read.csv("data_e4_marks.csv")
mk$col <- ifelse(mk$level == "rare", "rare (subset-sim only)", "moderate (validation)")
pE4 <- ggplot(cc, aes(x, pmax(ccdf, 1e-4))) +
  geom_step(color = "grey55", linewidth = 0.8) +
  geom_errorbar(data = mk, inherit.aes = FALSE,
                aes(x = tau, ymin = pmax(p_subset - subset_sd, 1e-7),
                    ymax = p_subset + subset_sd, color = col), width = 0.003, linewidth = 0.8) +
  geom_point(data = mk, inherit.aes = FALSE, aes(tau, p_subset, color = col), size = 3) +
  geom_point(data = mk[mk$naive_hits > 0, ], inherit.aes = FALSE,
             aes(tau, p_naive), shape = 4, size = 3, stroke = 1, color = "black") +
  scale_y_log10(limits = c(1e-6, 1.3),
                labels = trans_format("log10", math_format(10^.x))) +
  scale_color_manual(name = "subset-sim", values = c("moderate (validation)" = "#1f77b4",
                                                      "rare (subset-sim only)" = "#d62728")) +
  labs(title = "E4 — rare-event tail probability by subset simulation",
       subtitle = "grey = naive MC CCDF (noise in the tail); o = subset-sim (±sd); x = naive point estimate",
       x = "leak level x  (= penetrators / N)", y = expression(P(leak >= x))) +
  theme_pub()
save_both(pE4, "fig_e4_tail", 8, 5)

cat("\nAll E1-E4 figures rendered in the unified style.\n")
