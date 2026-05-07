from gpiozero import OutputDevice
import time
 
# Wiring (BCM numbering)
D1 = OutputDevice(17)   # Pi pin 11 → J3 pin 2 — bit 0 (LSB, 22.5°)
D2 = OutputDevice(27)   # Pi pin 13 → J3 pin 3 — bit 1 (45°)
D3 = OutputDevice(22)   # Pi pin 15 → J3 pin 4 — bit 2 (90°)
D4 = OutputDevice(23)   # Pi pin 16 → J3 pin 5 — bit 3 (MSB, 180°)
LATCH = OutputDevice(24)  # Pi pin 18 → J3 pin 6 — D5 latch enable
 
bits = [D1, D2, D3, D4]   # ordered LSB to MSB
 
def set_phase(code):
    """Set MAPS phase. code: 0..15. Each step = 22.5 degrees."""
    if not 0 <= code <= 15:
        raise ValueError("code must be 0-15")
    LATCH.off()
    for i, pin in enumerate(bits):
        pin.value = (code >> i) & 1
    time.sleep(0.001)
    LATCH.on()
    time.sleep(0.001)
    LATCH.off()
 
# Demo: cycle through all 16 states, 2 seconds each
try:
    for code in range(16):
        set_phase(code)
        print(f"Code {code:2d}  bits {code:04b}  expected phase = {code*22.5:5.1f}°")
        time.sleep(2)
finally:
    for pin in bits + [LATCH]:
        pin.off()
