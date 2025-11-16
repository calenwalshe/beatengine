#!/usr/bin/env bash
set -euo pipefail

# Generate 10 bassline variants for a given drum config using combo_cli.
# Usage: scripts/make_bass_variants.sh CONFIG_PATH OUT_DIR [KEY] [MODE]

CFG=${1:-}
OUTDIR=${2:-out/warehouse_sync_pack}
KEY=${3:-A}
MODE=${4:-minor}

if [[ -z "${CFG}" ]]; then
  echo "Usage: $0 CONFIG_PATH OUT_DIR [KEY] [MODE]" >&2
  exit 2
fi

mkdir -p "${OUTDIR}"

# Render drums once
PYTHONPATH=src python -m techno_engine.combo_cli \
  --drum "${CFG}" \
  --drum_out "${OUTDIR}/drums.mid" \
  --bass_out "${OUTDIR}/bass_base.mid" \
  --key "${KEY}" --mode "${MODE}" --density 0.40 --degree minor || true

declare -a MOTIFS=(
  root_fifth
  root_b7
  root_fifth_octave
  pentatonic_bounce
  dorian_sway
  root_only
  root_fifth
  root_b7
  root_fifth_octave
  pentatonic_bounce
)

declare -a PHRASES=(
  rise
  bounce
  fall
  surge
  collapse
  rise
  bounce
  fall
  surge
  collapse
)

declare -a DENSITIES=(0.34 0.36 0.38 0.40 0.42 0.44 0.46 0.40 0.37 0.43)
declare -a ROOTS=(43 45 47 45 43 47 45 43 47 45)

for i in $(seq 0 9); do
  motif=${MOTIFS[$i]}
  phrase=${PHRASES[$i]}
  dens=${DENSITIES[$i]}
  root=${ROOTS[$i]}
  out_bass="${OUTDIR}/bass_${i}_${motif}_${phrase}_d${dens}.mid"
  PYTHONPATH=src python -m techno_engine.combo_cli \
    --drum "${CFG}" \
    --drum_out "${OUTDIR}/drums.mid" \
    --bass_out "${out_bass}" \
    --key "${KEY}" --mode "${MODE}" \
    --root_note ${root} \
    --motif "${motif}" --phrase "${phrase}" \
    --density ${dens} --degree minor
done

echo "Generated drums + 10 basslines in ${OUTDIR}"

