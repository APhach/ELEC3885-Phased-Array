import time
import os
import shutil
import numpy as np
from validation_flow import validation_flow # Imports the class from your GRC generated file

def run_automated_sweep():
    # Define the noise voltage steps you want to test
    noise_voltages = np.linspace(0.0, 15.0, 20)
    
    # Static file names matching what you typed into the File Sink blocks in GRC
    temp_bits_file = "temp_bits.bin"
    temp_symbols_file = "temp_symbols.bin"
    
    # Create a directory to store the outputs
    os.makedirs("test_results", exist_ok=True)

    for nv in noise_voltages:
        print(f"--- Running Test: Noise Voltage = {nv} ---")
        
        # 1. Initialise the flowgraph (simulates a cold start)
        tb = validation_flow()
        
        # 2. Set the variable (ensure your variable block in GRC is exactly 'noise_voltage')
        tb.set_noise_voltage(nv)
        
        # 3. Start the flowgraph
        tb.start()
        
        # 4. Let it run and collect data for 30 seconds
        time.sleep(5)
        
        # 5. Stop the flowgraph and wait for threads to close gracefully
        tb.stop()
        tb.wait()
        
        # 6. Move and rename the generated files so they aren't overwritten next loop
        safe_nv = str(nv).replace('.', 'p') # e.g., converts 0.5 to '0p5' for safe file naming
        
        if os.path.exists(temp_bits_file):
            shutil.move(temp_bits_file, f"test_results/rx_bits_nv_{safe_nv}.bin")
            
        if os.path.exists(temp_symbols_file):
            shutil.move(temp_symbols_file, f"test_results/rx_symbols_nv_{safe_nv}.bin")
            
        print(f"Data saved for NV {nv}. \n")

if __name__ == '__main__':
    run_automated_sweep()
    print("Automated sweep complete. Files are in the /test_results/ directory.")
