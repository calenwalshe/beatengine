# Param Effects Cheatsheet

This guides natural-language intent to concrete parameter edits (dot-paths) for the engine and presets.

- “More ghost kicks” → `layers.kick.ghost_pre1_prob += 0.05 … 0.15` (cap at 0.6)
- “Push hats earlier” → `layers.hat_c.beat_bins_ms` early-skew or `hat_c.swing_percent += 0.01`
- “Less swing” → `layers.hat_c.swing_percent -= 0.02` (keep within 0.50–0.62)
- “Open hats ratchet more” → `layers.hat_o.ratchet_prob += 0.03`
- “Thin hats near kick” → `thin_bias -= 0.05` (more negative = more thinning)
- “Faster rotation drift” → `layers.kick.rotation_rate_per_bar += 0.01`
- “Denser closed hats” → `layers.hat_c.fills += 1` (≤ steps)
- “Sparser hats” → `targets.hat_density_target -= 0.05`, or add `EVERY_N` with `negate:true`
- “Tighter microtiming” → `targets.T_ms_cap -= 2` and shrink `beat_bin_cap_ms`
- “Keep kick immutable” → `guard.kick_immutable = true`
- “Allow kick variation” → `guard.kick_immutable = false`, adjust `kick.displace_into_2_prob`
- “Higher energy” → bump `accent.prob`, `accent.velocity_scale`, and widen `S` band slightly

Ranges and clamps should respect guardrails and tests. Modulators should keep `max_delta_per_bar` small (≤ 0.02–0.03).

