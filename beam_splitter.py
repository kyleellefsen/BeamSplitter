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
        self.current_red = None
        self.current_green = None

    def __call__(self, red_window, green_window, x_shift, y_shift):
        '''
        plots red_window over green_window, shifted by (x_shift, y_shift) pixels
        '''
        self.window.close()
        del self.window
        g.m.statusBar().showMessage("Applying beam splitter shift ...")
        t = time()
        imR = red_window.image
        t, w, h = imR.shape
        if red_window != None and green_window != None:
            gName = "%s shifted (%d, %d)" % (green_window.name, x_shift, y_shift)
            imG = green_window.image
        imG = self.pad_shift(imG, np.shape(imR), x_shift, y_shift)
        command = 'beam_splitter(%s, %s, %s, %s)' % (red_window, green_window, x_shift, y_shift)
        g.m.statusBar().showMessage("Successfully shifted (%s s)" % (time() - t))
        green_window.imageview.setImage(imG)
        green_window.setName(gName)
        green_window.commands = [command]
        green_window.imageview.setLevels(self.minlevel, self.maxlevel)

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
            self.gui.close()
        event.accept()

    def closeEvent(self, event):
        if self.current_red != None:
            self.current_red.sigTimeChanged.disconnect(self.changed)
        if self.current_green != None:
            self.current_green.sigTimeChanged.disconnect(self.changed)
        BaseProcess_noPriorWindow.closeEvent(self, event)

    def indexChanged(self, i):
        self.preview()

    def preview(self):
        winRed = self.getValue('red_window')
        winGreen = self.getValue('green_window')

        if self.current_red != winRed:
            if self.current_red != None:
                self.current_red.sigTimeChanged.disconnect(self.indexChanged)
            winRed.sigTimeChanged.connect(self.indexChanged)
        if self.current_red != winGreen:
            if self.current_green != None:
                self.current_green.sigTimeChanged.disconnect(self.indexChanged)
            winGreen.sigTimeChanged.connect(self.indexChanged)
        self.current_green = winGreen
        self.current_red = winRed

        x_shift = self.getValue('x_shift')
        y_shift = self.getValue('y_shift')
        if winRed != None and winGreen != None:
            imR = winRed.image[winRed.currentIndex]
            w, h = imR.shape
            imG = winGreen.image[winGreen.currentIndex]
            imG = self.pad_shift(imG, np.shape(imR), x_shift, y_shift)
            self.minlevel = np.min([np.min(imG), np.min(imR)])
            self.maxlevel = np.max([np.max(imG), np.max(imR)])
            
            imZ = np.zeros_like(imR)
            stacked = np.dstack((imR, imG, imZ))
            if not hasattr(self, 'window'):
                self.window = Window(stacked)
                self.window.imageview.setLevels(self.minlevel, self.maxlevel)
                self.window.imageview.keyPressEvent = self.keyPressed
            else:
                self.window.imageview.setImage(stacked, autoLevels=False, autoRange=False)
            self.window.show()
        elif hasattr(self, "window"):
            self.window.hide()

    def gui(self):
        self.gui_reset()
        red_window=WindowSelector()
        self.green_window=WindowSelector()
        self.x_shift_spin = pg.SpinBox(int=True, step=1)
        self.y_shift_spin = pg.SpinBox(int=True, step=1)

        self.items.append({'name': 'red_window', 'string': 'Overlay Red Window', 'object': red_window})
        self.items.append({'name': 'green_window', 'string': 'With Green Window', 'object': self.green_window})
        self.items.append({'name': 'x_shift', 'string': 'X Pixel Shift', 'object': self.x_shift_spin})
        self.items.append({'name': 'y_shift', 'string': 'Y Pixel Shift', 'object': self.y_shift_spin})
        super().gui()
beam_splitter = Beam_Splitter()