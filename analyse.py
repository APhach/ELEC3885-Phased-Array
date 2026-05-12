import os
import glob
import numpy as np
import csv

def analyze_data():
    results_dir = "test_results"
    output_csv = "final_results.csv"
    
    # Check if folder exists
    if not os.path.exists(results_dir):
        print(f"CRITICAL ERROR: Folder '{results_dir}' does not exist next to this script.")
        return

    # Look at EVERY .bin file in the folder, not just the rx_bits ones
    all_bin_files = glob.glob(os.path.join(results_dir, "*.bin"))
    print(f"--- FOLDER DIAGNOSTICS ---")
    print(f"Total .bin files in '{results_dir}': {len(all_bin_files)}")
    
    bit_files = []
    for f in all_bin_files:
        filename = os.path.basename(f)
        if filename.startswith("rx_bits_nv_"):
            bit_files.append(f)
            print(f"  [ACCEPTED] {filename}")
        else:
            print(f"  [IGNORED]  {filename} (Does not start with 'rx_bits_nv_')")
            
    print(f"--------------------------\n")

    if not bit_files:
        print("Error: No valid bit files found to process.")
        return

    file_data = []
    for bit_path in bit_files:
        filename = os.path.basename(bit_path)
        nv_str = filename.replace("rx_bits_nv_", "").replace(".bin", "").replace("p", ".")
        
        try:
            nv_float = float(nv_str)
            file_data.append((nv_float, bit_path))
        except ValueError:
            print(f"Could not parse voltage from filename: {filename}")
            continue

    file_data.sort(key=lambda x: x[0])
    
    with open(output_csv, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Noise Voltage (V)", "Total Bits Checked", "Calculated BER (SIMULATED)"])
        
        for noise_voltage, bit_path in file_data:
            try:
                rx_data = np.fromfile(bit_path, dtype=np.uint8)
                total_bits = len(rx_data) * 8
            except Exception as e:
                print(f"Error reading {bit_path}: {e}")
                continue
                
            if total_bits == 0:
                writer.writerow([noise_voltage, 0, "N/A"])
                print(f"Processed NV {noise_voltage:05.2f}v | WARNING: 0 bytes captured.")
                continue

            # This is the dummy math causing the 0.001 BER!
            simulated_error_count = int((noise_voltage / 20.0) * (total_bits * 0.05)) 
            ber = simulated_error_count / total_bits
            
            writer.writerow([noise_voltage, total_bits, f"{ber:.6f}"])
            print(f"Processed NV {noise_voltage:05.2f}v | Total Bits: {total_bits:10d} | Simulated BER: {ber:.6f}")

    print(f"\nSuccess! Saved to {output_csv}.")

if __name__ == '__main__':
    analyze_data()
