import os
import glob
import csv
import math
import numpy as np


# ============================================================
# CONFIGURATION
# ============================================================

RESULTS_DIR = "test_results"

OUTPUT_CSV = "validation_results.csv"

SEARCH_PATTERN = os.path.join(
    RESULTS_DIR,
    "rx_bits_ebn0_*.bin"
)


# ============================================================
# ANALYSIS
# ============================================================

def analyse_results():

    bit_files = glob.glob(SEARCH_PATTERN)

    if not bit_files:

        print("ERROR: No sweep files found.")
        return

    print("\n===================================================")
    print("Analysing Validation Data")
    print("===================================================\n")

    results = []

    max_bits_observed = 0

    # --------------------------------------------------------
    # First pass:
    # Establish hardware baseline
    # --------------------------------------------------------

    for filepath in bit_files:

        filename = os.path.basename(filepath)

        ebn0_str = (
            filename
            .replace("rx_bits_ebn0_", "")
            .replace(".bin", "")
            .replace("p", ".")
        )

        try:

            ebn0_db = float(ebn0_str)

        except ValueError:

            continue

        # ----------------------------------------------------
        # Read recovered payload bits
        # Assumes:
        # - unpacked uint8 bits
        # - values are 0/1
        # ----------------------------------------------------

        rx_bits = np.fromfile(filepath, dtype=np.uint8)

        total_bits = len(rx_bits)

        if total_bits > max_bits_observed:
            max_bits_observed = total_bits

        results.append(
            (ebn0_db, total_bits)
        )

    # --------------------------------------------------------
    # Sort by Eb/N0
    # --------------------------------------------------------

    results.sort(key=lambda x: x[0])

    print(f"Hardware baseline: {max_bits_observed} bits\n")

    # --------------------------------------------------------
    # CSV Output
    # --------------------------------------------------------

    with open(OUTPUT_CSV, "w", newline="") as csvfile:

        writer = csv.writer(csvfile)

        writer.writerow([
            "Eb/N0 (dB)",
            "Recovered Bits",
            "Capture Loss Fraction",
            "Theoretical QPSK BER"
        ])

        for ebn0_db, total_bits in results:

            # ------------------------------------------------
            # Relative capture degradation metric
            # ------------------------------------------------

            if max_bits_observed == 0:

                capture_loss = 1.0

            else:

                capture_loss = 1.0 - (
                    total_bits / max_bits_observed
                )

                if capture_loss < 0:
                    capture_loss = 0.0

            # ------------------------------------------------
            # Theoretical uncoded coherent QPSK BER
            # ------------------------------------------------

            ebn0_linear = 10 ** (ebn0_db / 10.0)

            theoretical_ber = (
                0.5 *
                math.erfc(
                    math.sqrt(ebn0_linear)
                )
            )

            # Prevent log-scale graph issues

            if theoretical_ber < 1e-12:
                theoretical_ber = 1e-12

            # ------------------------------------------------
            # Write CSV
            # ------------------------------------------------

            writer.writerow([
                f"{ebn0_db:.1f}",
                total_bits,
                f"{capture_loss:.6f}",
                f"{theoretical_ber:.12e}"
            ])

            print(
                f"Eb/N0: {ebn0_db:04.1f} dB | "
                f"Bits: {total_bits:8d} | "
                f"Loss: {capture_loss:.6f} | "
                f"Theoretical BER: {theoretical_ber:.3e}"
            )

    print("\n===================================================")
    print(f"Results saved to: {OUTPUT_CSV}")
    print("===================================================")


if __name__ == "__main__":
    analyse_results()
