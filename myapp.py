#!/usr/bin/env python3
"""
myapp.py -- kiosk wrapper around final.py for the 7-inch Pi touchscreen.

What it does:
  - Imports the GNU Radio flowgraph (final.py) without running its own GUI
  - Embeds the constellation + a freq sink into a fixed 800x480 layout
  - Adds a control panel: freq, tx_atten, rcv gain, az/el (manual/auto stub),
    record toggle, lock indicator
  - Fullscreen kiosk; Ctrl+Q to exit

Designed to stay simple. Add features by adding rows in build_controls().
"""

from __future__ import annotations

import os
import sys
import time
import shutil
from datetime import datetime
from pathlib import Path

import sip
from PyQt5 import QtCore, QtGui, QtWidgets

from gnuradio import qtgui
from gnuradio.fft import window  # noqa: F401  -- referenced by final.py's imports

# Pull in the existing flowgraph. final.py defines class `final(gr.top_block)`.
import final as fg


# --------------------------------------------------------------------------
# Config
# --------------------------------------------------------------------------

REC_DIR     = Path.home() / "recordings"
SOURCE_TXT  = "qpsk_receive.txt"        # written by the flowgraph
POLL_MS     = 500                        # how often to poll FER / record / lock


# --------------------------------------------------------------------------
# A tiny coloured circle that turns green/red
# --------------------------------------------------------------------------

class LockIndicator(QtWidgets.QLabel):
    def __init__(self, diameter=24, parent=None):
        super().__init__(parent)
        self.setFixedSize(diameter, diameter)
        self._locked = False
        self._update()

    def set_locked(self, locked: bool):
        if locked != self._locked:
            self._locked = locked
            self._update()

    def _update(self):
        pm = QtGui.QPixmap(self.size())
        pm.fill(QtCore.Qt.transparent)
        p = QtGui.QPainter(pm)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        colour = QtGui.QColor("#27c93f") if self._locked else QtGui.QColor("#c0392b")
        p.setBrush(colour)
        p.setPen(QtCore.Qt.NoPen)
        p.drawEllipse(2, 2, self.width() - 4, self.height() - 4)
        p.end()
        self.setPixmap(pm)


# --------------------------------------------------------------------------
# The main window
# --------------------------------------------------------------------------

class App(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CCSDS Cyberdeck")

        # --- Build the flowgraph but do not show its window --------------
        self.tb = fg.final()
        self._add_freq_sink_to_flowgraph()

        # --- Layout ------------------------------------------------------
        central = QtWidgets.QWidget(self)
        self.setCentralWidget(central)
        outer = QtWidgets.QVBoxLayout(central)
        outer.setContentsMargins(4, 4, 4, 4)
        outer.setSpacing(4)

        # Top: two GR sink widgets side by side
        top = QtWidgets.QHBoxLayout()
        top.addWidget(self._steal_sink(self.tb.qtgui_const_sink_x_0), 1)
        top.addWidget(self._steal_sink(self._freq_sink), 1)
        outer.addLayout(top, stretch=3)

        # Bottom: controls
        outer.addWidget(self._build_controls(), stretch=2)

        # --- Periodic poller for FER / record / lock ---------------------
        self._last_rx_size = 0
        self._record_fp    = None
        self._record_path  = None

        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(POLL_MS)

        # --- Kiosk + shortcut --------------------------------------------
        QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+Q"), self,
                            activated=self._quit)
        self.showFullScreen()

        # Start the radio
        self.tb.start()

    # ------------------------------------------------------------------
    # Flowgraph plumbing
    # ------------------------------------------------------------------

    def _add_freq_sink_to_flowgraph(self):
        """Tack a freq sink onto the existing flowgraph, post-Pluto-source."""
        samp_rate = self.tb.get_samp_rate()
        self._freq_sink = qtgui.freq_sink_c(
            1024, window.WIN_BLACKMAN_HARRIS, 0, samp_rate,
            "RX Spectrum", 1, None)
        self._freq_sink.set_update_time(0.10)
        self._freq_sink.set_y_axis(-140, 10)
        self._freq_sink.enable_grid(True)
        # Tap right at the Pluto source
        self.tb.connect((self.tb.iio_pluto_source_0, 0),
                        (self._freq_sink, 0))

    def _steal_sink(self, sink):
        """Grab the QWidget owned by a GR Qt sink and return it."""
        return sip.wrapinstance(sink.qwidget(), QtWidgets.QWidget)

    # ------------------------------------------------------------------
    # Controls
    # ------------------------------------------------------------------

    def _build_controls(self) -> QtWidgets.QWidget:
        box = QtWidgets.QFrame()
        box.setFrameShape(QtWidgets.QFrame.StyledPanel)
        grid = QtWidgets.QGridLayout(box)
        grid.setContentsMargins(8, 8, 8, 8)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(4)

        row = 0

        # --- Frequency (MHz) ---
        grid.addWidget(QtWidgets.QLabel("Freq (MHz)"), row, 0)
        self.freq_spin = QtWidgets.QDoubleSpinBox()
        self.freq_spin.setRange(70.0, 6000.0)
        self.freq_spin.setDecimals(3)
        self.freq_spin.setSingleStep(1.0)
        self.freq_spin.setValue(self.tb.get_frequency() / 1e6)
        self.freq_spin.valueChanged.connect(
            lambda v: self.tb.set_frequency(int(v * 1e6)))
        grid.addWidget(self.freq_spin, row, 1)

        # --- TX atten ---
        grid.addWidget(QtWidgets.QLabel("TX atten (dB)"), row, 2)
        self.atten_spin = QtWidgets.QDoubleSpinBox()
        self.atten_spin.setRange(0.0, 60.0)
        self.atten_spin.setSingleStep(1.0)
        self.atten_spin.setValue(self.tb.get_tx_atten())
        self.atten_spin.valueChanged.connect(self.tb.set_tx_atten)
        grid.addWidget(self.atten_spin, row, 3)

        # --- RX gain ---
        grid.addWidget(QtWidgets.QLabel("RX gain (dB)"), row, 4)
        self.gain_spin = QtWidgets.QDoubleSpinBox()
        self.gain_spin.setRange(0.0, 73.0)
        self.gain_spin.setSingleStep(1.0)
        self.gain_spin.setValue(self.tb.get_gain())
        self.gain_spin.valueChanged.connect(self.tb.set_gain)
        grid.addWidget(self.gain_spin, row, 5)

        row += 1

        # --- Az / El (stub for now) ---
        grid.addWidget(QtWidgets.QLabel("Az (deg)"), row, 0)
        self.az_spin = QtWidgets.QDoubleSpinBox()
        self.az_spin.setRange(-360.0, 360.0)
        self.az_spin.setSingleStep(1.0)
        self.az_spin.setValue(0.0)
        grid.addWidget(self.az_spin, row, 1)

        grid.addWidget(QtWidgets.QLabel("El (deg)"), row, 2)
        self.el_spin = QtWidgets.QDoubleSpinBox()
        self.el_spin.setRange(0.0, 90.0)
        self.el_spin.setSingleStep(1.0)
        self.el_spin.setValue(90.0)
        grid.addWidget(self.el_spin, row, 3)

        self.mode_box = QtWidgets.QComboBox()
        self.mode_box.addItems(["Manual", "Auto"])
        grid.addWidget(QtWidgets.QLabel("Mode"), row, 4)
        grid.addWidget(self.mode_box, row, 5)

        row += 1

        # --- Record / Lock / Status / Quit ---
        self.rec_btn = QtWidgets.QPushButton("● Record")
        self.rec_btn.setCheckable(True)
        self.rec_btn.toggled.connect(self._toggle_record)
        grid.addWidget(self.rec_btn, row, 0, 1, 2)

        self.lock_lbl = QtWidgets.QLabel("Lock:")
        self.lock_ind = LockIndicator(24)
        lockwrap = QtWidgets.QHBoxLayout()
        lockwrap.addWidget(self.lock_lbl)
        lockwrap.addWidget(self.lock_ind)
        lockwrap.addStretch(1)
        lw = QtWidgets.QWidget()
        lw.setLayout(lockwrap)
        grid.addWidget(lw, row, 2, 1, 2)

        self.status_lbl = QtWidgets.QLabel("RX bytes: 0")
        grid.addWidget(self.status_lbl, row, 4)

        self.quit_btn = QtWidgets.QPushButton("Quit")
        self.quit_btn.clicked.connect(self._quit)
        grid.addWidget(self.quit_btn, row, 5)

        return box

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def _toggle_record(self, on: bool):
        if on:
            REC_DIR.mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
            self._record_path = REC_DIR / f"rx_{ts}.txt"
            self._record_fp   = open(self._record_path, "wb")
            self._last_rx_size = self._current_rx_size()
            self.rec_btn.setText(f"■ Recording → {self._record_path.name}")
        else:
            if self._record_fp:
                self._record_fp.close()
                self._record_fp = None
            self.rec_btn.setText("● Record")

    def _current_rx_size(self) -> int:
        try:
            return os.path.getsize(SOURCE_TXT)
        except OSError:
            return 0

    def _drain_into_recording(self):
        """Append any new bytes from qpsk_receive.txt into the record file."""
        if self._record_fp is None:
            return
        size = self._current_rx_size()
        if size > self._last_rx_size:
            try:
                with open(SOURCE_TXT, "rb") as f:
                    f.seek(self._last_rx_size)
                    chunk = f.read(size - self._last_rx_size)
                self._record_fp.write(chunk)
                self._record_fp.flush()
            except OSError:
                pass
            self._last_rx_size = size

    # ------------------------------------------------------------------
    # Periodic poll
    # ------------------------------------------------------------------

    def _tick(self):
        # Status: bytes in qpsk_receive.txt
        size = self._current_rx_size()
        self.status_lbl.setText(f"RX bytes: {size}")

        # Lock: very crude -- locked if file is growing
        if not hasattr(self, "_prev_size_for_lock"):
            self._prev_size_for_lock = size
            self.lock_ind.set_locked(False)
        else:
            self.lock_ind.set_locked(size > self._prev_size_for_lock)
            self._prev_size_for_lock = size

        self._drain_into_recording()

    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------

    def _quit(self):
        try:
            if self._record_fp:
                self._record_fp.close()
        except Exception:
            pass
        try:
            self.tb.stop()
            self.tb.wait()
        except Exception:
            pass
        QtWidgets.QApplication.quit()

    def closeEvent(self, ev):
        self._quit()
        ev.accept()


# --------------------------------------------------------------------------

def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")

    palette = QtGui.QPalette()
    palette.setColor(QtGui.QPalette.Window,          QtGui.QColor(35, 35, 38))
    palette.setColor(QtGui.QPalette.WindowText,      QtCore.Qt.white)
    palette.setColor(QtGui.QPalette.Base,            QtGui.QColor(25, 25, 28))
    palette.setColor(QtGui.QPalette.AlternateBase,   QtGui.QColor(45, 45, 48))
    palette.setColor(QtGui.QPalette.Text,            QtCore.Qt.white)
    palette.setColor(QtGui.QPalette.Button,          QtGui.QColor(50, 50, 55))
    palette.setColor(QtGui.QPalette.ButtonText,      QtCore.Qt.white)
    palette.setColor(QtGui.QPalette.Highlight,       QtGui.QColor(60, 130, 200))
    palette.setColor(QtGui.QPalette.HighlightedText, QtCore.Qt.white)
    app.setPalette(palette)

    app.setStyleSheet("""
        QPushButton { padding: 6px; font-size: 14px; }
        QPushButton:checked { background: #c0392b; }
        QFrame { background: #2a2a2e; border: 1px solid #444; border-radius: 4px; }
    """)


if __name__ == "__main__":
    main()
