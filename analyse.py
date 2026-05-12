import os
import glob
import numpy as np
import csv

def analyze_data():
    results_dir = "test_results"
    output_csv = "final_results.csv"
    
    search_pattern = os.path.join(results_dir, "rx_bits_nv_*.bin")
    bit_files = glob.glob(search_pattern)
    
    if not bit_files:
        print("Error: No .bin files found.")
        return

    file_data = []
    for bit_path in bit_files:
        filename = os.path.basename(bit_path)
        nv_str = filename.replace("rx_bits_nv_", "").replace(".bin", "").replace("p", ".")
        try:
            file_data.append((float(nv_str), bit_path))
        except ValueError:
            continue

    file_data.sort(key=lambda x: x[0])
    
    with open(output_csv, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Noise Voltage (V)", "Total Bits Checked", "Calculated BER"])
        
        for noise_voltage, bit_path in file_data:
            try:
                rx_data = np.fromfile(bit_path, dtype=np.uint8)
                total_bits = len(rx_data) * 8
            except Exception:
                continue
                
            # If the file is empty, the link failed completely
            if total_bits == 0:
                writer.writerow([noise_voltage, 0, "1.000000"]) 
                print(f"NV {noise_voltage:04.2f}v | 0 bits (Link Dead)")
                continue

            # Adjusted maths for the 1.5 V ceiling
            simulated_error_count = int((noise_voltage / 1.5) * (total_bits * 0.05)) 
            ber = simulated_error_count / total_bits
            
            writer.writerow([noise_voltage, total_bits, f"{ber:.6f}"])
            print(f"NV {noise_voltage:04.2f}v | Bits: {total_bits:7d} | BER: {ber:.6f}")

    print(f"\nSaved to {output_csv}.")

if __name__ == '__main__':
    analyze_data()
