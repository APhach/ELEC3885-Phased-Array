import os
import glob
import numpy as np
import csv

def analyze_data():
    results_dir = "test_results"
    output_csv = "final_results.csv"
    
    # 1. Locate all generated bit files
    search_pattern = os.path.join(results_dir, "rx_bits_nv_*.bin")
    bit_files = glob.glob(search_pattern)
    
    if not bit_files:
        print(f"Error: No .bin files found in '{results_dir}/'. Run the sweep first.")
        return

    # 2. Extract voltages and SORT the list mathematically
    file_data = []
    for bit_path in bit_files:
        filename = os.path.basename(bit_path)
        # Convert 'rx_bits_nv_1p50.bin' -> '1.50'
        nv_str = filename.replace("rx_bits_nv_", "").replace(".bin", "").replace("p", ".")
        
        try:
            nv_float = float(nv_str)
            file_data.append((nv_float, bit_path))
        except ValueError:
            print(f"Could not parse voltage from filename: {filename}")
            continue

    # CRITICAL FIX: Force ascending order so your graph doesn't scribble back on itself
    file_data.sort(key=lambda x: x[0])

    # 3. Process the files and write to CSV
    print(f"Found {len(file_data)} files. Processing in ascending order...")
    
    with open(output_csv, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Noise Voltage (V)", "Total Bits Checked", "Calculated BER"])
        
        for noise_voltage, bit_path in file_data:
            try:
                # Read the raw bytes dumped by GNU Radio
                rx_data = np.fromfile(bit_path, dtype=np.uint8)
                total_bits = len(rx_data) * 8 # 8 bits per byte
            except Exception as e:
                print(f"Error reading {bit_path}: {e}")
                continue
                
            # Failsafe for empty captures
            if total_bits == 0:
                writer.writerow([noise_voltage, 0, "N/A"])
                print(f"Processed NV {noise_voltage:05.2f}v | WARNING: 0 bytes captured.")
                continue

            # --- BER MATH LOGIC ---
            # NOTE: Placeholder logic so you can verify the CSV populates correctly.
            # Once confirmed, you will replace this with your cross-correlation math.
            simulated_error_count = int((noise_voltage / 15.0) * (total_bits * 0.05)) 
            ber = simulated_error_count / total_bits
            
            # Write the row to the CSV
            writer.writerow([noise_voltage, total_bits, f"{ber:.6f}"])
            print(f"Processed NV {noise_voltage:05.2f}v | Total Bits: {total_bits:7d} | BER: {ber:.6f}")

    print(f"\nSuccess! Sorted dataset saved to {output_csv}.")

if __name__ == '__main__':
    analyze_data()