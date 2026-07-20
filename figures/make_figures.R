#!/usr/bin/env Rscript
# Publication-quality figures (ggplot2) for the HPM saturation analysis.
# Outputs crisp SVG (renders natively on GitHub) + PNG.
# Run:  Rscript figures/make_figures.R
suppressMessages({library(ggplot2); library(dplyr); library(viridis); library(scales)})

setwd(dirname(sub("--file=", "", grep("--file=", commandArgs(FALSE), value = TRUE)[1])))

theme_pub <- function() {
  theme_minimal(base_size = 13) +
    theme(panel.grid = element_blank(),
          plot.title = element_text(face = "bold", size = 14),
          plot.subtitle = element_text(color = "grey30", size = 10),
          legend.position = "right",
          axis.title = element_text(size = 12))
}
save_both <- function(p, name, w = 7, h = 5) {
  grDevices::svg(paste0(name, ".svg"), width = w, height = h); print(p); dev.off()
  grDevices::png(paste0(name, ".png"), width = w, height = h, units = "in", res = 130)
  print(p); dev.off()
  cat("wrote", name, ".svg/.png\n")
}

## ---- Fig 1: angular-saturation phase map (theta x t_c) ----
sat <- read.csv("data_saturation.csv")
# analytic Sigma=1 boundary: t_c* = (Reff-Rc)/v * (1-cos theta)
th_seq <- seq(min(sat$theta), max(sat$theta), length.out = 200)
bnd <- data.frame(theta = th_seq, t_c = (500 - 50) / 30 * (1 - cos(th_seq * pi / 180)))
p1 <- ggplot(sat, aes(theta, t_c, fill = leak)) +
  geom_raster(interpolate = TRUE) +
  scale_fill_viridis(name = "leak", limits = c(0, 1), option = "D") +
  geom_line(data = bnd, aes(theta, t_c), inherit.aes = FALSE,
            color = "white", linewidth = 1.1, linetype = "dashed") +
  annotate("text", x = 11, y = 1.45, label = "penetrated\n(Σ > 1)", color = "white",
           fontface = "bold", size = 3.6, hjust = 0) +
  annotate("text", x = 26, y = 0.35, label = "defense holds\n(Σ < 1)", color = "white",
           fontface = "bold", size = 3.6, hjust = 0.5) +
  coord_cartesian(xlim = range(sat$theta), ylim = range(sat$t_c), expand = FALSE) +
  labs(title = "Angular saturation of a single HPM aperture",
       subtitle = "leak fraction vs beam half-angle θ and engagement cycle t_c;  dashed = closed-form Σ=1 boundary",
       x = "beam half-angle  θ  (deg)", y = "engagement cycle  t_c  (s)") +
  theme_pub()
save_both(p1, "fig_saturation_phase", 7.5, 5)

## ---- Fig 2: 1-ha / 4-installations breakthrough (R_eff x N) ----
hec <- read.csv("data_hectare.csv") %>%
  mutate(R_eff = factor(R_eff, levels = c(1000, 500, 200, 50)),
         N = factor(N, levels = c(100, 300, 600, 1000, 2000)))
p2 <- ggplot(hec, aes(N, R_eff, fill = leak)) +
  geom_tile(color = "white", linewidth = 0.6) +
  geom_text(aes(label = sprintf("%.2f", leak),
                color = leak > 0.5), size = 4, show.legend = FALSE) +
  scale_color_manual(values = c("grey15", "white")) +
  scale_fill_viridis(name = "leak", limits = c(0, 1), option = "C") +
  labs(title = "1 hectare, 4 corner installations — breakthrough",
       subtitle = "calibrated θ=30°, n_cone=49;  R_eff is EFFECTIVE range (falls ~10× per +20 dB drone shielding)",
       x = "swarm size  N", y = "effective range  R_eff  (m)") +
  theme_pub() + theme(panel.grid = element_blank())
save_both(p2, "fig_hectare_breakthrough", 7.5, 4.2)

## ---- Fig 3: T_r/τ saturation-ratio sensitivity (analytic) ----
grid <- expand.grid(theta = seq(5, 32, length.out = 160),
                    t_c = seq(0.1, 1.0, length.out = 160)) %>%
  mutate(S = 1 / (1 - cos(theta * pi / 180)),
         Sigma = S * t_c * 30 / (500 - 50))
p3 <- ggplot(grid, aes(theta, t_c, fill = pmin(Sigma, 3))) +
  geom_raster() +
  scale_fill_viridis(name = "Σ = T_r/τ", option = "B",
                     breaks = c(0, 1, 2, 3), labels = c("0", "1", "2", "≥3")) +
  geom_contour(aes(z = Sigma), breaks = 1, color = "cyan", linewidth = 1.0) +
  annotate("text", x = 8, y = 0.9, label = "Σ = 1\nbreakthrough", color = "cyan",
           fontface = "bold", size = 3.6, hjust = 0) +
  coord_cartesian(expand = FALSE) +
  labs(title = "Saturation ratio Σ = T_r/τ  (analytic)",
       subtitle = "one aperture holds where Σ<1; the pencil↔shield beam width is the dominant lever",
       x = "beam half-angle  θ  (deg)", y = "engagement cycle  t_c  (s)") +
  theme_pub()
save_both(p3, "fig_sigma_sensitivity", 7.5, 5)

cat("\nAll figures written to figures/ (SVG + PNG)\n")
