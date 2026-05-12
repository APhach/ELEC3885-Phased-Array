import os
import time
import shutil
import subprocess
import sys
import numpy as np

def run_automated_sweep():
    # UPDATED: 0.0 V to 20.0 V in increments of 1.0 V
    noise_voltages = np.arange(0.0, 21.0, 1.0)
    
    # --- CRITICAL: THESE MUST MATCH YOUR GRC FILE SINKS EXACTLY ---
    temp_bits_file = r"C:\path\to\your\temp_bits.bin"
    temp_symbols_file = r"C:\path\to\your\temp_symbols.bin"
    
    os.makedirs("test_results", exist_ok=True)

    for nv in noise_voltages:
        print(f"--- Running Test: Noise Voltage = {nv:.2f} ---")
        
        if os.path.exists(temp_bits_file): os.remove(temp_bits_file)
        if os.path.exists(temp_symbols_file): os.remove(temp_symbols_file)

        worker_code = f"""
import time
from validation_flow import validation_flow 
tb = validation_flow()
tb.set_noise_voltage({nv})
tb.start()
time.sleep(5)
tb.stop()
time.sleep(1)
del tb
"""
        with open("temp_worker.py", "w") as f:
            f.write(worker_code.strip())

        process = subprocess.Popen([sys.executable, "temp_worker.py"])
        
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            print("Hardware freeze detected: OS forcefully terminated the worker.")
        
        time.sleep(1) 
        
        safe_nv = f"{nv:.2f}".replace('.', 'p') 
        
        if os.path.exists(temp_bits_file):
            shutil.move(temp_bits_file, f"test_results/rx_bits_nv_{safe_nv}.bin")
            print(f"SUCCESS: Bits saved.")
        else:
            print(f"FAIL: Could not find {temp_bits_file}!")
            
        if os.path.exists(temp_symbols_file):
            shutil.move(temp_symbols_file, f"test_results/rx_symbols_nv_{safe_nv}.bin")
            print(f"SUCCESS: Symbols saved.")
        else:
            print(f"FAIL: Could not find {temp_symbols_file}!")
            
        print("Hardware cooldown: Waiting 4 seconds for PlutoSDR to release context...\n")
        time.sleep(4)

    if os.path.exists("temp_worker.py"):
        os.remove("temp_worker.py")
        
    print("Sweep complete. You can now run the analysis script.")

if __name__ == '__main__':
    run_automated_sweep()
