"""
ber_sweep.py -- automated noise-voltage sweep for the validation flowgraph.

For each noise-voltage setting:
  1. Cold-start the flowgraph
  2. Wait WARMUP_S seconds for Pluto + sync to converge (data not used)
  3. Collect MEASURE_S seconds of bits/symbols into the file sinks
  4. Stop, rename output files, write a manifest row

A manifest CSV is produced alongside the binary captures so the
downstream analysis script can iterate without re-parsing filenames.
"""

import csv
import os
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np

from validation_flow import validation_flow


# ---------------------------------------------------------------------------
# Sweep configuration
# ---------------------------------------------------------------------------

# Total per-point runtime = WARMUP_S + MEASURE_S seconds.
# WARMUP_S is discarded; MEASURE_S is what ends up in the saved files.
WARMUP_S        = 5.0    # let Pluto + symbol sync + Costas converge
MEASURE_S       = 30.0   # data collection window

# Linear pass. Replace with a manual list or log-spaced array once you
# know roughly where the BER waterfall sits.
NOISE_VOLTAGES  = np.linspace(0.0, 15.0, 20)

# File sink names as written in the GRC flowgraph.
TEMP_BITS       = "temp_bits.bin"
TEMP_SYMBOLS    = "temp_symbols.bin"

# Where to put everything.
OUT_DIR         = Path("test_results")
MANIFEST_PATH   = OUT_DIR / "manifest.csv"

# Minimum saved-file size to consider the capture "valid", in bytes.
# At samp_rate / sps symbol rate, MEASURE_S seconds gives roughly
#   bits  ~= 2 * (samp_rate / sps) * MEASURE_S
# Set conservatively to catch totally-empty captures.
MIN_VALID_BYTES = 1024


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def safe_label(nv: float) -> str:
    """Filesystem-safe label for a noise voltage value."""
    return f"{nv:.4f}".replace(".", "p")


def truncate_if_present(path: str) -> None:
    """Delete a leftover capture file so we always start fresh."""
    if os.path.exists(path):
        os.remove(path)


def safe_move(src: str, dst: Path) -> int:
    """Move src -> dst. Returns the file size, or 0 if src missing/empty."""
    if not os.path.exists(src):
        return 0
    size = os.path.getsize(src)
    if size == 0:
        os.remove(src)
        return 0
    shutil.move(src, dst)
    return size


def countdown(prefix: str, seconds: float) -> None:
    """sleep(seconds) but print progress so we know we're still alive."""
    end = time.time() + seconds
    while True:
        remaining = end - time.time()
        if remaining <= 0:
            break
        print(f"\r  {prefix}: {remaining:5.1f} s remaining ", end="", flush=True)
        time.sleep(min(0.5, remaining))
    print(f"\r  {prefix}: done                ")


# ---------------------------------------------------------------------------
# Main sweep
# ---------------------------------------------------------------------------

def run_one(nv: float, idx: int, total: int) -> dict:
    print(f"\n[{idx+1}/{total}] noise_voltage = {nv:.4f}")

    label   = safe_label(nv)
    started = datetime.utcnow().isoformat(timespec="seconds")

    # Cold start
    truncate_if_present(TEMP_BITS)
    truncate_if_present(TEMP_SYMBOLS)

    tb = validation_flow()
    tb.set_noise_voltage(nv)
    tb.start()

    try:
        # Warmup: file sinks are recording but we'll truncate after.
        # The file sinks write continuously; we can't actually mask the
        # first N seconds without two-sink trickery. So instead we just
        # let the warmup data sit at the front of the file and note the
        # offset in the manifest. The analysis script skips the first
        # WARMUP_S worth of bytes.
        countdown("warmup ", WARMUP_S)
        countdown("measure", MEASURE_S)
    finally:
        tb.stop()
        tb.wait()

    bits_path    = OUT_DIR / f"rx_bits_nv_{label}.bin"
    symbols_path = OUT_DIR / f"rx_symbols_nv_{label}.bin"

    bits_size    = safe_move(TEMP_BITS,    bits_path)
    symbols_size = safe_move(TEMP_SYMBOLS, symbols_path)

    valid = bits_size >= MIN_VALID_BYTES and symbols_size >= MIN_VALID_BYTES
    if not valid:
        print(f"  WARNING: capture undersized (bits={bits_size}, "
              f"symbols={symbols_size})")

    return {
        "idx":              idx,
        "noise_voltage":    f"{nv:.6f}",
        "bits_file":        bits_path.name if bits_size else "",
        "symbols_file":     symbols_path.name if symbols_size else "",
        "bits_bytes":       bits_size,
        "symbols_bytes":    symbols_size,
        "warmup_s":         WARMUP_S,
        "measure_s":        MEASURE_S,
        "valid":            int(valid),
        "started_utc":      started,
    }


def run_automated_sweep():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    fields = [
        "idx", "noise_voltage",
        "bits_file", "symbols_file",
        "bits_bytes", "symbols_bytes",
        "warmup_s", "measure_s",
        "valid", "started_utc",
    ]
    with open(MANIFEST_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()

        for i, nv in enumerate(NOISE_VOLTAGES):
            try:
                row = run_one(float(nv), i, len(NOISE_VOLTAGES))
            except KeyboardInterrupt:
                print("\nInterrupted by user.")
                sys.exit(1)
            except Exception as e:
                print(f"  ERROR running nv={nv}: {e}")
                row = {
                    "idx": i, "noise_voltage": f"{nv:.6f}",
                    "bits_file": "", "symbols_file": "",
                    "bits_bytes": 0, "symbols_bytes": 0,
                    "warmup_s": WARMUP_S, "measure_s": MEASURE_S,
                    "valid": 0,
                    "started_utc": datetime.utcnow().isoformat(timespec="seconds"),
                }
            writer.writerow(row)
            f.flush()


if __name__ == "__main__":
    t0 = time.time()
    run_automated_sweep()
    elapsed = time.time() - t0
    print(f"\nDone. {elapsed/60:.1f} min total. "
          f"Captures in {OUT_DIR}/, manifest at {MANIFEST_PATH}.")
