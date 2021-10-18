# pylint:disable=missing-docstring
import sys

from matplotlib.backends.qt_compat import QtWidgets
from matplotlib.backends.backend_qt5agg import FigureCanvas
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import numpy as np
from PyQt5.QtCore import pyqtSignal as Signal
from PyQt5.QtGui import QColor

from gradient import Gradient


def to_gradient(red, green, blue):
    color = QColor(int(red * 255), int(green * 255), int(blue * 255))
    return f'#{color.rgb():08X}'


def from_gradient(color):
    color = QColor.fromRgb(int(color[1:], 16))
    return color.red() / 255, color.green() / 255, color.blue() / 255, 1


def circle(radius, angle):
    # x**2 + y**2 = radius**2
    # cos(angle) = a/h

    angle = angle % (2 * np.pi)

    if angle < np.pi:
        x = np.cos(angle) * radius
        y = np.sqrt(radius**2 - x**2)

    else:
        x = np.cos(angle) * radius
        y = -np.sqrt(radius**2 - x**2)

    return x, y


def squircle(radius, width, angle_offset, segments):
    x = []
    y = []
    for idx, angle in enumerate(np.linspace(angle_offset,
                                            2 * np.pi + angle_offset,
                                            segments + 1)):
        if idx >= segments:
            break

        if idx % 2 == 0:
            (tx, ty) = circle(radius - (width / 2), angle)
        else:
            (tx, ty) = circle(radius + (width / 2), angle)

        x.append(tx)
        y.append(ty)

    x.append(x[0])
    y.append(y[0])

    return x, y


class ControlPanel(QtWidgets.QGroupBox):

    numbersChanged = Signal()
    save = Signal()

    def __init__(self, vals):
        super().__init__('Controls')

        self._vals = vals

        layout = QtWidgets.QFormLayout(self)

        # Num Bumps
        self._num_bumps = QtWidgets.QSpinBox()
        self._num_bumps.setMinimum(2)
        self._num_bumps.setValue(self._vals['num_bumps'])
        self._num_bumps.valueChanged.connect(self.update)
        layout.addRow('Num. Bumps', self._num_bumps)

        # Num Rings
        self._num_rings = QtWidgets.QSpinBox()
        self._num_rings.setMinimum(1)
        self._num_rings.setValue(self._vals['num_rings'])
        self._num_rings.valueChanged.connect(self.update)
        layout.addRow('Num. Rings', self._num_rings)

        # Rot Rings
        self._rot_rings = QtWidgets.QSpinBox()
        self._rot_rings.setMinimum(2)
        self._rot_rings.setValue(self._vals['rot_rings'])
        self._rot_rings.valueChanged.connect(self.update)
        layout.addRow('Rot. Rings', self._rot_rings)

        # Rotation Offset
        self._rot_offset = QtWidgets.QDoubleSpinBox()
        self._rot_offset.setRange(0, 2 * np.pi)
        self._rot_offset.setDecimals(2)
        self._rot_offset.setSingleStep(0.01)
        self._rot_offset.setValue(self._vals['rot_offset'])
        self._rot_offset.valueChanged.connect(self.update)
        layout.addRow('Rot. Offset', self._rot_offset)

        # Radius Offset
        self._rad_offset = QtWidgets.QDoubleSpinBox()
        self._rad_offset.setMinimum(0.01)
        self._rad_offset.setDecimals(2)
        self._rad_offset.setSingleStep(0.01)
        self._rad_offset.setValue(self._vals['rad_offset'])
        self._rad_offset.valueChanged.connect(self.update)
        layout.addRow('Rad. Offset', self._rad_offset)

        # Bump Size
        self._bump_size = QtWidgets.QDoubleSpinBox()
        self._bump_size.setMinimum(0.01)
        self._bump_size.setDecimals(2)
        self._bump_size.setSingleStep(0.01)
        self._bump_size.setValue(self._vals['bump_size'])
        self._bump_size.valueChanged.connect(self.update)
        layout.addRow('Bump Size', self._bump_size)

        self._save = QtWidgets.QPushButton('Save')
        self._save.clicked.connect(self.save.emit)
        layout.addRow(self._save)

    def get_values(self):
        return self._vals

    def update(self):
        self._vals = {
            'num_bumps': self._num_bumps.value(),
            'num_rings': self._num_rings.value(),
            'rot_rings': self._rot_rings.value(),
            'rot_offset': self._rot_offset.value(),
            'rad_offset': self._rad_offset.value(),
            'bump_size': self._bump_size.value(),
        }
        self.numbersChanged.emit()


class AppWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        layout = QtWidgets.QGridLayout(self)

        self.fig = Figure(figsize=(5, 5))
        self.canvas = FigureCanvas(self.fig)
        layout.addWidget(self.canvas, 0, 0)

        self.ax = self.canvas.figure.subplots()
        cmap = plt.get_cmap('gist_rainbow')
        gradient_colors = []
        for r, g, b in zip(cmap._segmentdata['red'],
                           cmap._segmentdata['green'],
                           cmap._segmentdata['blue']):
            gradient_colors.append(
                (r[0], to_gradient(r[1], g[1], b[1])))

        vals = {
            'num_bumps': 20,
            'num_rings': 40,
            'rot_rings': 10,
            'rot_offset': 0.1,
            'rad_offset': 0.05,
            'bump_size': 0.1,
        }

        self._controls = ControlPanel(vals)
        layout.addWidget(self._controls, 0, 1)

        self._gradient = Gradient(gradient_colors)
        layout.addWidget(self._gradient, 1, 0, 1, 2)

        self._controls.numbersChanged.connect(self.redraw)
        self._gradient.gradientChanged.connect(self.redraw)
        self._controls.save.connect(self._save)

        self.redraw()

    def redraw(self):
        vals = self._controls.get_values()
        gradient = self._gradient.gradient()
        gradient = [(x, from_gradient(y))
                    for x, y in gradient]
        gradient = sorted(gradient, key=lambda x: x[0])
        cmap = LinearSegmentedColormap.from_list('custom', gradient)

        num_bumps = vals['num_bumps'] * 2
        num_rings = vals['num_rings']
        rot_rings = vals['rot_rings'] * 2
        rot_offset = vals['rot_offset']
        rad_offset = vals['rad_offset']
        bump_size = vals['bump_size']

        offsets = np.zeros((rot_rings - 2,))
        offsets[0:rot_rings // 2] = np.linspace(0, rot_offset, rot_rings // 2)
        offsets[rot_rings // 2:] = np.linspace(rot_offset, 0,
                                               rot_rings // 2)[1:-1]

        self.ax.clear()
        self.ax.tick_params(axis='both', which='both', bottom=False,
                            left=False, top=False, right=False)
        self.ax.tick_params(axis='both', which='both',
                            labelbottom=False, labelleft=False,
                            labeltop=False, labelright=False)
        for bidx in range(num_rings):
            self.ax.plot(*squircle(
                    radius=1 + (rad_offset * bidx),
                    width=bump_size,
                    angle_offset=offsets[bidx % (rot_rings - 2)],
                    segments=num_bumps),
                color=cmap(bidx / num_rings))
        self.canvas.draw()

    def _save(self):
        (fname, _) = QtWidgets.QFileDialog.getSaveFileName(
            self, 'Save to', '', 'Images (*.png *.jpg)')
        if not fname:
            return

        self.fig.savefig(fname, dpi=200)
        msg = QtWidgets.QMessageBox()
        msg.setText('Save Complete')
        msg.exec_()


def main():
    qapp = QtWidgets.QApplication(sys.argv)
    app = AppWindow()
    app.show()
    app.activateWindow()
    app.raise_()
    qapp.exec_()


if __name__ == '__main__':
    main()
