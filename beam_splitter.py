from __future__ import (absolute_import, division,print_function, unicode_literals)
from future.builtins import (bytes, dict, int, list, object, range, str, ascii, chr, hex, input, next, oct, open, pow, round, super, filter, map, zip)

from process.BaseProcess import BaseProcess_noPriorWindow, WindowSelector
from PyQt4.QtCore import *
from PyQt4.QtGui import *
import numpy as np
from scipy.ndimage.interpolation import shift
from window import Window
import global_vars as g
import pyqtgraph as pg

class Beam_Splitter(BaseProcess_noPriorWindow):
    def __init__(self):
        BaseProcess_noPriorWindow.__init__(self)

    def __call__(self, red_window, green_window, x_shift, y_shift, split_type='Two Windows'):
        '''
        plots red_window over green_window, shifted by (x_shift, y_shift) pixels
        '''
        imR = red_window.image
        t, w, h = imR.shape
        if split_type == 'Vertical Split':
            imR, imG = imR[:, :w // 2, :], imR[:, w // 2:, :]
            self.newname = "%s Vertical Split" % (red_window.name)
        elif split_type == 'Horizontal Split':
            imR, imG = imR[:, :, :h // 2], imR[:, :, h // 2:]
            self.newname = "%s Horizontal Split" % (red_window.name)
        elif split_type == 'Two Windows' and winGreen != None:
            self.newname = "Overlay %s on %s" % (green_window.name, red_window.name)
            imG = green_window.image
        imG = self.pad_shift(imG, np.shape(imR), x_shift, y_shift)
        self.newtif = np.hstack((imR, imG))
        self.newname += " (%s, %s)" % (x_shift, y_shift)
        self.command = 'beam_splitter(%s, %s, %s, %s, %s)' % (red_window, green_window, x_shift, y_shift, split_type)
        return self.end()
    
    def make_colored(self, im, color):
        imR = im if color == 0 else np.zeros_like(im)
        imG = im if color == 1 else np.zeros_like(im)
        imB = im if color == 2 else np.zeros_like(im)
        return np.dstack((imR, imG, imB))
        #return np.stack((im if color == 0 else np.zeros_like(im), im if color == 1 else np.zeros_like(im), im if color == 2 else np.zeros_like(im)), np.ndim(im))


    def pad_shift(self, imGreen, size, x_shift, y_shift):
        '''
        shift imGreen by (x_shift, y_shift) onto an empty array of size similar to imRed
        '''
        g_size = imGreen.shape
        imGreen_shifted = np.zeros(size)
        if imGreen.ndim == 2:
            imGreen_shifted[:g_size[0], :g_size[1]] = imGreen
        elif imGreen.ndim == 3:
            imGreen_shifted[:, :g_size[1], :g_size[2]] = imGreen
        imGreen_shifted = shift(imGreen_shifted, (0, x_shift, y_shift) if len(size) == 3 else (x_shift, y_shift))
        return imGreen_shifted

    def keyPressed(self, event):
        if event.key() == Qt.Key_Up:
            self.y_shift_spin.setValue(self.y_shift_spin.value() - 1)
        if event.key() == Qt.Key_Down:
            self.y_shift_spin.setValue(self.y_shift_spin.value() + 1)
        if event.key() == Qt.Key_Left:
            self.x_shift_spin.setValue(self.x_shift_spin.value() - 1)
        if event.key() == Qt.Key_Right:
            self.x_shift_spin.setValue(self.x_shift_spin.value() + 1)
        event.accept()

    def preview(self):
        winRed = self.getValue('red_window')
        winGreen = self.getValue('green_window')
        mode = self.getValue('split_type')
        x_shift = self.getValue('x_shift')
        y_shift = self.getValue('y_shift')
        if winRed != None:
            imR = winRed.image[winRed.currentIndex]
            w, h = imR.shape
            if mode == 'Vertical Split':
                imR, imG = imR[:w // 2, :], imR[w // 2:, :]
            elif mode == 'Horizontal Split':
                imR, imG = imR[:, :h // 2], imR[:, h // 2:]
            elif mode == 'Two Windows' and winGreen != None:
                imG = winGreen.image[winGreen.currentIndex]
            else:
                return
            imG = self.pad_shift(imG, np.shape(imR), x_shift, y_shift)
            imG = self.make_colored(imG, 1)
            imR = self.make_colored(imR, 0)
            stacked = imR + imG
            if not hasattr(self, 'window') or not self.window.isVisible():
                self.window = Window(stacked)
                self.window.imageview.keyPressEvent = self.keyPressed
                self.window.closeEvent = lambda ev: self.ui.close()
            else:
                self.window.imageview.setImage(stacked, autoLevels=False, autoRange=False)
        

    def gui(self):
        self.gui_reset()
        red_window=WindowSelector()
        self.green_window=WindowSelector()
        self.green_window.setEnabled(False)
        self.x_shift_spin = pg.SpinBox(int=True, step=1)
        self.y_shift_spin = pg.SpinBox(int=True, step=1)
        self.windowDropDown = QComboBox()
        self.windowDropDown.addItems(['Vertical Split', 'Horizontal Split', 'Two Windows'])

        self.items.append({'name': 'red_window', 'string': 'Red Background Image', 'object': red_window})
        self.items.append({'name': 'split_type', 'string': 'Overlay Type', 'object': self.windowDropDown})
        self.windowDropDown.currentIndexChanged.connect(lambda v: self.green_window.setEnabled(self.windowDropDown.itemText(v) == 'Two Windows'))
        self.items.append({'name': 'green_window', 'string': 'Green Foreground Image', 'object': self.green_window})
        self.items.append({'name': 'x_shift', 'string': 'X Pixel Shift', 'object': self.x_shift_spin})
        self.items.append({'name': 'y_shift', 'string': 'Y Pixel Shift', 'object': self.y_shift_spin})
        super().gui()
beam_splitter = Beam_Splitter()