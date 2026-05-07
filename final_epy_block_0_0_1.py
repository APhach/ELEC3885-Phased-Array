import numpy as np
from gnuradio import gr

class blk(gr.basic_block):
    def __init__(self, frame_len=255, tolerance=0):
        gr.basic_block.__init__(self,
            name="Custom CCSDS RX",
            in_sig=[np.float32],
            out_sig=[np.uint8])
        self.frame_len = frame_len
        self.tolerance = tolerance
        self.asm_val = 0x1ACFFC1D
        self.state = 0          # 0 = hunting, 1 = receiving payload
        self.sync_reg = 0
        self.lfsr = 0xFF
        self.bit_count = 0
        self.current_byte = 0
        self.frames_seen = 0

    def general_work(self, input_items, output_items):
        in_sig = input_items[0]
        out_sig = output_items[0]
        in_idx = 0
        out_idx = 0

        while in_idx < len(in_sig) and out_idx < len(out_sig):
            bit = 1 if in_sig[in_idx] > 0 else 0

            if self.state == 0:
                # Shift incoming bits into 32-bit sync register
                self.sync_reg = ((self.sync_reg << 1) | bit) & 0xFFFFFFFF
                diff = self.sync_reg ^ self.asm_val
                errors = bin(diff).count('1')

                if errors <= self.tolerance:
                    self.state = 1
                    self.bit_count = 0
                    self.current_byte = 0
                    self.lfsr = 0xFF
                    self.frames_seen += 1
                    print(f"[RX] ASM detected, frame #{self.frames_seen}, errors={errors}")

            else:  # state == 1: descramble payload
                msb = (self.lfsr >> 7) & 1
                orig_bit = bit ^ msb
                self.current_byte = ((self.current_byte << 1) | orig_bit) & 0xFF

                new_bit = (
                    ((self.lfsr >> 7) & 1) ^
                    ((self.lfsr >> 6) & 1) ^
                    ((self.lfsr >> 4) & 1) ^
                    ((self.lfsr >> 2) & 1)
                )
                self.lfsr = ((self.lfsr << 1) | new_bit) & 0xFF
                self.bit_count += 1

                if self.bit_count % 8 == 0:
                    out_sig[out_idx] = self.current_byte
                    out_idx += 1
                    self.current_byte = 0

                if self.bit_count == self.frame_len * 8:
                    self.state = 0
                    self.sync_reg = 0

            in_idx += 1

        self.consume(0, in_idx)
        return out_idx