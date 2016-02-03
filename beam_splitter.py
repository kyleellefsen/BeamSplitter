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
from time import time

class Beam_Splitter(BaseProcess_noPriorWindow):
    def __init__(self):
        BaseProcess_noPriorWindow.__init__(self)

    def __call__(self, red_window, green_window, x_shift, y_shift, split_type='Two Windows'):
        '''
        plots red_window over green_window, shifted by (x_shift, y_shift) pixels
        '''
        self.window.close()
        del self.window
        g.m.statusBar().showMessage("Applying beam splitter shift ...")
        t = time()
        imR = red_window.image
        t, w, h = imR.shape
        if split_type == 'Vertical Split':
            imR, imG = imR[:, :w // 2, :], imR[:, w // 2:, :]
            rName = "%s Left Half" % (red_window.name)
            gName = "%s Right Half shifted (%d, %d)" % (red_window.name, x_shift, y_shift)
        elif split_type == 'Horizontal Split':
            imR, imG = imR[:, :, :h // 2], imR[:, :, h // 2:]
            rName = "%s Top Half" % (red_window.name)
            gName = "%s Bottom Half shifted (%d, %d)" % (red_window.name, x_shift, y_shift)
        elif split_type == 'Two Windows' and green_window != None:
            gName = "%s shifted (%d, %d)" % (green_window.name, x_shift, y_shift)
            rName = ''
            imG = green_window.image
        imG = self.pad_shift(imG, np.shape(imR), x_shift, y_shift)
        command = 'beam_splitter(%s, %s, %s, %s, %s)' % (red_window, green_window, x_shift, y_shift, split_type)
        g.m.statusBar().showMessage("Successfully shifted (%s s)" % (time() - t))
        if rName:
            winR = Window(imR, name=rName, commands=[command])
            winR.imageview.setLevels(self.minlevel, self.maxlevel)
        winG = Window(imG, name=gName, commands=[command])
        winG.imageview.setLevels(self.minlevel, self.maxlevel)

    def pad_shift(self, imGreen, size, x_shift, y_shift):
        '''
        shift imGreen by (x_shift, y_shift) onto an empty array of size similar to imRed
        '''
        g_size = imGreen.shape
        imGreen_shifted = np.zeros(size)
        if imGreen.ndim == 2:
            imGreen_shifted[:g_size[0], :g_size[1]] = imGreen
            imGreen_shifted = shift(imGreen_shifted, (x_shift, y_shift))
        elif imGreen.ndim == 3:
            rt, rw, rh = size
            gt, gw, gh = g_size
            r_left = max(0, x_shift)
            r_top = max(0, y_shift)
            r_right = min(rw, gw + x_shift)
            r_bottom = min(rh, gh + y_shift)

            g_left = max(0, -x_shift)
            g_top = max(0, -y_shift)
            g_right = min(gw, rw - x_shift)
            g_bottom = min(gh, rh - y_shift)
            
            imGreen_shifted[:, r_left:r_right, r_top:r_bottom] = imGreen[:, g_left:g_right, g_top:g_bottom]        
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
        if event.key() == 16777220: # Enter
            self.call_from_gui()
        event.accept()

    def preview(self, extra=0):
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
                if hasattr(self, 'window'):
                    self.window.hide()
                return
            imG = self.pad_shift(imG, np.shape(imR), x_shift, y_shift)
            self.minlevel = np.min([np.min(imG), np.min(imR)])
            self.maxlevel = np.max([np.max(imG), np.max(imR)])
            
            imZ = np.zeros_like(imR)
            stacked = np.dstack((imR, imG, imZ))
            if not hasattr(self, 'window') or not self.window.isVisible():
                self.window = Window(stacked)
                self.window.imageview.setLevels(self.minlevel, self.maxlevel)
                self.window.imageview.keyPressEvent = self.keyPressed
                self.window.closeEvent = self.closeEvent
            else:
                self.window.imageview.setImage(stacked, autoLevels=False, autoRange=False)
        
    def closeEvent(self, event):
        self.ui.close()
        event.accept()

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