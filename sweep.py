import os
import time
import shutil
import subprocess
import sys
import numpy as np

def run_automated_sweep():
    # Sweep Eb/N0 from 0.0 dB to 12.0 dB in 0.5 dB increments
    ebn0_targets = np.arange(0.0, 12.5, 0.5)
    
    # --- CRITICAL: THESE MUST MATCH YOUR GRC FILE SINKS EXACTLY ---
    temp_bits_file = r"C:\path\to\your\temp_bits.bin"
    temp_symbols_file = r"C:\path\to\your\temp_symbols.bin"
    
    os.makedirs("test_results", exist_ok=True)

    for ebn0 in ebn0_targets:
        # Calculate the exact GNU Radio Noise Voltage for this Eb/N0
        ebn0_linear = 10 ** (ebn0 / 10.0)
        nv = np.sqrt(1.0 / (2.0 * ebn0_linear))
        
        print(f"--- Target: Eb/N0 = {ebn0:04.1f} dB | Required Noise Voltage = {nv:.4f} V ---")
        
        if os.path.exists(temp_bits_file): os.remove(temp_bits_file)
        if os.path.exists(temp_symbols_file): os.remove(temp_symbols_file)

        # 10-second capture to dilute OS jitter and spin-up errors
        worker_code = f"""
import time
from validation_flow import validation_flow 
tb = validation_flow()
tb.set_noise_voltage({nv})
tb.start()
time.sleep(10) 
tb.stop()
time.sleep(1)
del tb
"""
        with open("temp_worker.py", "w") as f:
            f.write(worker_code.strip())

        process = subprocess.Popen([sys.executable, "temp_worker.py"])
        
        try:
            # 15-second timeout for a 10-second task
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            print("Hardware freeze detected: OS forcefully terminated the worker.")
        
        time.sleep(1) 
        
        # Save the file using the Eb/N0 value, not the voltage!
        safe_ebn0 = f"{ebn0:.1f}".replace('.', 'p') 
        
        if os.path.exists(temp_bits_file):
            shutil.move(temp_bits_file, f"test_results/rx_bits_ebn0_{safe_ebn0}.bin")
            print(f"SUCCESS: Bits saved.")
        else:
            print(f"FAIL: Could not find {temp_bits_file}!")
            
        if os.path.exists(temp_symbols_file):
            shutil.move(temp_symbols_file, f"test_results/rx_symbols_ebn0_{safe_ebn0}.bin")
            print(f"SUCCESS: Symbols saved.")
        else:
            print(f"FAIL: Could not find {temp_symbols_file}!")
            
        print("Hardware cooldown: Waiting 4 seconds...\n")
        time.sleep(4)

    if os.path.exists("temp_worker.py"):
        os.remove("temp_worker.py")
        
    print("Sweep complete. Data is ready for final BER analysis.")

if __name__ == '__main__':
    run_automated_sweep()
