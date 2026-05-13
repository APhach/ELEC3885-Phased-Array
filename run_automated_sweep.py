import os
import time
import shutil
import subprocess
import sys
import numpy as np


# ============================================================
# CONFIGURATION
# ============================================================

RESULTS_DIR = "test_results"

TEMP_BITS_FILE = r"/home/gdp-group-four/myapp/temp_bits.bin"
TEMP_SYMBOLS_FILE = r"/home/gdp-group-four/myapp/temp_symbols.bin"

FLOWGRAPH_MODULE = "validation_flow"
FLOWGRAPH_CLASS = "validation_flow"

CAPTURE_DURATION = 10
PROCESS_TIMEOUT = 15
COOLDOWN_TIME = 4


# ============================================================
# MAIN SWEEP
# ============================================================

def run_automated_sweep():

    os.makedirs(RESULTS_DIR, exist_ok=True)

    ebn0_values = np.arange(0.0, 12.5, 0.5)

    print("\n===================================================")
    print("Starting Automated Eb/N0 Validation Sweep")
    print("===================================================\n")

    for ebn0_db in ebn0_values:

        # ----------------------------------------------------
        # Convert Eb/N0(dB) -> Linear
        # ----------------------------------------------------

        ebn0_linear = 10 ** (ebn0_db / 10.0)

        # ----------------------------------------------------
        # QPSK Complex AWGN Noise Voltage
        #
        # Assumes:
        # - RMS AGC normalises signal amplitude to 1.0
        # - QPSK => 2 bits/symbol
        #
        # sigma = sqrt(1 / (4 * Eb/N0))
        # ----------------------------------------------------

        noise_voltage = np.sqrt(1.0 / (4.0 * ebn0_linear))

        print(f"Target Eb/N0 : {ebn0_db:.1f} dB")
        print(f"Noise Voltage: {noise_voltage:.6f}")

        # ----------------------------------------------------
        # Remove stale files
        # ----------------------------------------------------

        if os.path.exists(TEMP_BITS_FILE):
            os.remove(TEMP_BITS_FILE)

        if os.path.exists(TEMP_SYMBOLS_FILE):
            os.remove(TEMP_SYMBOLS_FILE)

        # ----------------------------------------------------
        # Generate isolated worker
        # ----------------------------------------------------

        worker_code = f'''
import time
from {FLOWGRAPH_MODULE} import {FLOWGRAPH_CLASS}

tb = {FLOWGRAPH_CLASS}()

tb.set_noise_voltage({noise_voltage})

tb.start()

time.sleep({CAPTURE_DURATION})

tb.stop()
tb.wait()

time.sleep(1)
'''

        with open("temp_worker.py", "w") as f:
            f.write(worker_code.strip())

        # ----------------------------------------------------
        # Execute isolated worker
        # ----------------------------------------------------

        process = subprocess.Popen(
            [sys.executable, "temp_worker.py"]
        )

        try:
            process.wait(timeout=PROCESS_TIMEOUT)

        except subprocess.TimeoutExpired:

            print("WARNING: SDR timeout detected.")
            print("Force terminating worker process...")

            process.kill()
            process.wait()

        # ----------------------------------------------------
        # Allow filesystem + SDR hardware to settle
        # ----------------------------------------------------

        time.sleep(1)

        # ----------------------------------------------------
        # Save outputs
        # ----------------------------------------------------

        safe_name = f"{ebn0_db:.1f}".replace(".", "p")

        bits_dest = os.path.join(
            RESULTS_DIR,
            f"rx_bits_ebn0_{safe_name}.bin"
        )

        symbols_dest = os.path.join(
            RESULTS_DIR,
            f"rx_symbols_ebn0_{safe_name}.bin"
        )

        if os.path.exists(TEMP_BITS_FILE):

            shutil.move(TEMP_BITS_FILE, bits_dest)

            print(f"Saved bits    -> {bits_dest}")

        else:

            print("WARNING: No bit file generated.")

        if os.path.exists(TEMP_SYMBOLS_FILE):

            shutil.move(TEMP_SYMBOLS_FILE, symbols_dest)

            print(f"Saved symbols -> {symbols_dest}")

        else:

            print("WARNING: No symbol file generated.")

        # ----------------------------------------------------
        # Hardware cooldown
        # ----------------------------------------------------

        print(f"Cooling hardware for {COOLDOWN_TIME}s...\n")

        time.sleep(COOLDOWN_TIME)

    # --------------------------------------------------------
    # Cleanup
    # --------------------------------------------------------

    if os.path.exists("temp_worker.py"):
        os.remove("temp_worker.py")

    print("===================================================")
    print("Sweep Complete")
    print("===================================================")


if __name__ == "__main__":
    run_automated_sweep()
