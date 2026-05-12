import time
import os
import shutil
import numpy as np
from validation_flow import validation_flow 

def run_automated_sweep():
    # Define 20 test steps from 0.0V to 15.0V
    noise_voltages = np.linspace(0.0, 15.0, 20)
    
    # MUST MATCH the absolute paths typed into your GRC File Sinks!
    temp_bits_file = r"C:\path\to\your\temp_bits.bin"
    temp_symbols_file = r"C:\path\to\your\temp_symbols.bin"
    
    # Create the output directory
    os.makedirs("test_results", exist_ok=True)

    for nv in noise_voltages:
        print(f"--- Running Test: Noise Voltage = {nv:.2f} ---")
        
        # 1. Initialise and start the flowgraph
        tb = validation_flow()
        tb.set_noise_voltage(nv)
        tb.start()
        
        # 2. Record data for 5 seconds
        time.sleep(5) 
        
        # 3. Safely kill the flowgraph and hardware threads
        tb.stop()
        del tb        # CRITICAL FIX: Kills the hanging SDR hardware thread
        time.sleep(1) # CRITICAL FIX: Gives Windows time to release the file lock
        
        # 4. Safely rename and move the files to prevent overwriting
        safe_nv = f"{nv:.2f}".replace('.', 'p') 
        
        if os.path.exists(temp_bits_file):
            shutil.move(temp_bits_file, f"test_results/rx_bits_nv_{safe_nv}.bin")
            
        if os.path.exists(temp_symbols_file):
            shutil.move(temp_symbols_file, f"test_results/rx_symbols_nv_{safe_nv}.bin")
            
        print(f"Data saved for NV {nv:.2f}. \n")

if __name__ == '__main__':
    run_automated_sweep()
    print("Automated sweep complete. Files are in the /test_results/ directory.")