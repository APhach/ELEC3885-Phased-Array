import multiprocessing
import time
import os
import shutil
import numpy as np

def worker_process(nv):
    # We import and run the flowgraph INSIDE the isolated background process
    from validation_flow import validation_flow 
    tb = validation_flow()
    tb.set_noise_voltage(nv)
    tb.start()
    
    # Keep the flowgraph running indefinitely. 
    # The main script will forcefully terminate this after 5 seconds.
    while True:
        time.sleep(0.5)

def run_automated_sweep():
    noise_voltages = np.linspace(0.0, 15.0, 20)
    
    # MUST MATCH the absolute paths typed into your GRC File Sinks!
    temp_bits_file = r"C:\path\to\your\temp_bits.bin"
    temp_symbols_file = r"C:\path\to\your\temp_symbols.bin"
    
    os.makedirs("test_results", exist_ok=True)

    for nv in noise_voltages:
        print(f"--- Running Test: Noise Voltage = {nv:.2f} ---")
        
        # 1. Spawn the flowgraph in a completely isolated process
        p = multiprocessing.Process(target=worker_process, args=(nv,))
        p.start()
        
        # 2. Let it collect data for exactly 5 seconds
        time.sleep(5) 
        
        # 3. THE NUCLEAR OPTION: Forcefully terminate the process.
        # This completely bypasses the PlutoSDR hardware freeze.
        p.terminate()
        p.join() 
        
        time.sleep(1) # Brief pause for Windows file system to release the lock
        
        # 4. Safely rename and move the files
        safe_nv = f"{nv:.2f}".replace('.', 'p') 
        
        try:
            if os.path.exists(temp_bits_file):
                shutil.move(temp_bits_file, f"test_results/rx_bits_nv_{safe_nv}.bin")
            if os.path.exists(temp_symbols_file):
                shutil.move(temp_symbols_file, f"test_results/rx_symbols_nv_{safe_nv}.bin")
            print(f"Data saved for NV {nv:.2f}. \n")
        except Exception as e:
            print(f"Failed to move files: {e} \n")

if __name__ == '__main__':
    run_automated_sweep()
    print("Automated sweep complete. You can now run the analysis script.")
