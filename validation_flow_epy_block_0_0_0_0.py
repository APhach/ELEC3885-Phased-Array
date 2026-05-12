import numpy as np
from gnuradio import gr

class blk(gr.basic_block):
    def __init__(self, frame_len=255, preamble_len=384):
        gr.basic_block.__init__(self,
            name="Custom CCSDS TX",
            in_sig=[np.uint8],
            out_sig=[np.float32])
        self.frame_len = frame_len
        self.preamble_len = preamble_len
        self.asm_val = 0x1ACFFC1D
        self.asm_bits = [(self.asm_val >> (31 - i)) & 1 for i in range(32)]
        
        # Pre-generate a fixed random sequence for the preamble
        # This prevents loop-shock when transitioning to the scrambled payload
        np.random.seed(42) 
        self.preamble_bits = np.random.randint(0, 2, self.preamble_len)
        
        self.out_frame_size = self.preamble_len + 32 + (self.frame_len * 8)

    def general_work(self, input_items, output_items):
        in_sig = input_items[0]
        out_sig = output_items[0]
        in_idx = 0
        out_idx = 0

        while (in_idx + self.frame_len <= len(in_sig)) and \
              (out_idx + self.out_frame_size <= len(out_sig)):

            data = in_sig[in_idx : in_idx + self.frame_len]
            in_idx += self.frame_len

            # 1. Preamble
            for b in self.preamble_bits:
                out_sig[out_idx] = 1.0 if b else -1.0
                out_idx += 1

            # Reset LFSR at start of every frame payload so RX stays in sync
            lfsr = 0xFF

            # 2. ASM (unscrambled)
            for b in self.asm_bits:
                out_sig[out_idx] = 1.0 if b else -1.0
                out_idx += 1

            # 3. Payload (scrambled)
            for byte in data:
                for i in range(7, -1, -1):
                    bit = (byte >> i) & 1
                    msb = (lfsr >> 7) & 1
                    enc_bit = bit ^ msb
                    out_sig[out_idx] = 1.0 if enc_bit else -1.0
                    out_idx += 1

                    new_bit = (
                        ((lfsr >> 7) & 1) ^
                        ((lfsr >> 6) & 1) ^
                        ((lfsr >> 4) & 1) ^
                        ((lfsr >> 2) & 1)
                    )
                    lfsr = ((lfsr << 1) | new_bit) & 0xFF

        self.consume(0, in_idx)
        return out_idx