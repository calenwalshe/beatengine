# Config Schema Cheatsheet (dot-paths)

Top-level EngineConfig (JSON):
- `mode` — "m1" | "m2" | "m4"
- `bpm`, `ppq`, `bars`, `seed`, `out`, `log_path?`
- `layers.kick|hat_c|hat_o|snare|clap` — LayerConfig
- `targets` — control bands and caps
- `guard` — entrainment guardrails
- `modulators[]` — param_path + mod spec

LayerConfig notable fields:
- `steps`, `fills`, `rot`, `note`, `velocity`
- `swing_percent`, `micro_ms`
- `beat_bins_ms[]`, `beat_bins_probs[]`, `beat_bin_cap_ms`
- `offbeats_only`, `ratchet_prob`, `ratchet_repeat`, `choke_with_note`
- `rotation_rate_per_bar`, `ghost_pre1_prob`, `displace_into_2_prob`
- `conditions[]` — objects with `kind` (PROB, PRE, NOT_PRE, FILL, EVERY_N) and optional `p`, `n`, `offset`, `negate`

Targets:
- `E_target` — entrainment target (default ~0.8)
- `S_low`, `S_high` — syncopation band
- `T_ms_cap` — microtiming cap (ms)
- `H_low`, `H_high` — hats band
- `hat_density_target`, `hat_density_tol`

Guard:
- `min_E`, `max_rot_rate`, `kick_immutable`

Modulator (`modulators[]`):
- `name`, `param_path` (dot-path into engine or layer)
- `mod` object: `mode` (random_walk|ou|sine), `min_val`, `max_val`, `step_per_bar`, `tau?`, `max_delta_per_bar`, `phase?`

Supported param_path examples:
- `thin_bias`
- `hat_c.swing_percent`
- `hat_o.ratchet_prob`
- `kick.rotation_rate_per_bar`
- Any float on a LayerConfig (e.g., `hat_o.swing_percent`)

