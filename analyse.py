import os
import glob
import numpy as np
import csv
import math

def analyse_data():
    results_dir = "test_results"
    output_csv = "final_ebn0_results.csv"
    
    # 1. Search for the new Eb/N0 filenames
    search_pattern = os.path.join(results_dir, "rx_bits_ebn0_*.bin")
    bit_files = glob.glob(search_pattern)
    
    if not bit_files:
        print("Error: No Eb/N0 .bin files found. Run the new sweep first.")
        return

    file_data = []
    max_bits_found = 0  
    
    # 2. Extract Eb/N0 and establish hardware baseline
    for bit_path in bit_files:
        filename = os.path.basename(bit_path)
        # Convert 'rx_bits_ebn0_5p5.bin' -> '5.5'
        ebn0_str = filename.replace("rx_bits_ebn0_", "").replace(".bin", "").replace("p", ".")
        
        try:
            ebn0_float = float(ebn0_str)
            rx_data = np.fromfile(bit_path, dtype=np.uint8)
            total_bits = len(rx_data)
            
            if total_bits > max_bits_found:
                max_bits_found = total_bits
                
            file_data.append((ebn0_float, bit_path, total_bits))
        except Exception:
            continue

    # Sort files mathematically by Eb/N0
    file_data.sort(key=lambda x: x[0])
    
    print(f"Hardware Baseline Established: {max_bits_found} bits maximum per 10s run.\n")
    
    with open(output_csv, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Eb/N0 (dB)", "Total Bits Checked", "Capture Loss", "Theoretical QPSK BER"])
        
        for ebn0, bit_path, total_bits in file_data:
            
            # --- FER CALCULATION ---
            if max_bits_found == 0:
                 fer = 1.0
            elif total_bits == 0:
                fer = 1.000000 
            else:
                capture_loss = 1.0 - (total_bits / max_bits_found)
                if capture_loss <0:
                    capture_loss = 0.0

            # --- THEORETICAL BER CALCULATION (Your perfect waterfall curve) ---
            # NOTE: Replace this block later with your NumPy cross-correlation math
            # to calculate the REAL hardware BER.
            ebn0_linear = 10.0 ** (ebn0 / 10.0)
            theoretical_ber = 0.5 * math.erfc(math.sqrt(ebn0_linear))

            # --- WRITE TO CSV ---
            # Setting a floor at 1e-8 so the logarithmic graph doesn't crash on absolute zero
            if theoretical_ber < 1e-8: theoretical_ber = 1e-8 
            
            writer.writerow([f"{ebn0:.1f}", total_bits, f"{capture_loss:.6f}", f"{theoretical_ber:.8e}"])
            print(f"Eb/N0: {ebn0:04.1f} dB | Bits: {total_bits:8d} | Capture loss: {capture_loss:.4f} | Ideal BER: {theoretical_ber:.2e}")

    print(f"\nSuccess! Waterfall data saved to {output_csv}.")

if __name__ == '__main__':
    analyse_data()
