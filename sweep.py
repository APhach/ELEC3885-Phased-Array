import multiprocessing
import time
import os
import shutil
import numpy as np

def worker_process(nv):
    # Run the flowgraph inside the isolated process
    from validation_flow import validation_flow 
    tb = validation_flow()
    tb.set_noise_voltage(nv)
    tb.start()
    
    # Record data for exactly 5 seconds
    time.sleep(5)
    
    # Gracefully command the flowgraph to stop
    tb.stop()
    time.sleep(1)
    
    # CRITICAL: Forcefully sever the hardware connection 
    # before the process closes, so the PlutoSDR is freed up.
    del tb 
    time.sleep(1)

def run_automated_sweep():
    noise_voltages = np.linspace(0.0, 15.0, 20)
    
    # --- CRITICAL: THESE MUST MATCH YOUR GRC FILE SINKS EXACTLY ---
    temp_bits_file = r"C:\path\to\your\temp_bits.bin"
    temp_symbols_file = r"C:\path\to\your\temp_symbols.bin"
    
    os.makedirs("test_results", exist_ok=True)

    for nv in noise_voltages:
        print(f"--- Running Test: Noise Voltage = {nv:.2f} ---")
        
        if os.path.exists(temp_bits_file): os.remove(temp_bits_file)
        if os.path.exists(temp_symbols_file): os.remove(temp_symbols_file)

        p = multiprocessing.Process(target=worker_process, args=(nv,))
        p.start()
        
        # Wait up to 10 seconds for the 7-second worker to finish
        p.join(timeout=10)
        
        if p.is_alive():
            p.terminate()
            p.join()
            print("Hardware freeze detected: Worker forcefully terminated.")
        
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
            
        # CRITICAL HARDWARE FIX: Give the PlutoSDR time to breathe
        print("Hardware cooldown: Waiting 4 seconds for PlutoSDR to release context...\n")
        time.sleep(4) 

if __name__ == '__main__':
    run_automated_sweep()
