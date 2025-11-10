# Metrics Cheatsheet (E, S, H, T)

Definitions and intended target ranges used by the controller and tests.

- E (Entrainment) — periodicity/regularity measure over bar-level union mask. Target ~0.8 median.
- S (Syncopation) — sync index in [0,1]; band typically [0.35, 0.55] (M4 may widen).
- H (Hat balance) — closed/open hat activity ratio; guided toward [H_low, H_high].
- T_ms (Micro cap) — aggregate microtiming magnitude; capped per layer by `T_ms_cap`.

Controller behaviour:
- Feedback biases step probabilities toward S band midpoint.
- Density clamps hold hat density near target ± tol.
- Rescue actions (if guard violated): reduce offbeat probs, reset rotations, straighten swing.

Logging (optional):
- Per-bar CSV with E, S, hat density, entropy when `log_path` is set on M4 configs.

