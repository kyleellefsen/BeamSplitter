from flika.process.BaseProcess import BaseProcess_noPriorWindow, WindowSelector
from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *
import numpy as np
from scipy.ndimage.interpolation import shift
from flika.window import Window
import flika.global_vars as g
import pyqtgraph as pg
from time import time

class Beam_Splitter(BaseProcess_noPriorWindow):
    """
    Overlay two image stacks to correct for xy pixel shift.  
    The current frame of the green window (or the smaller image if red is smaller)
    will be displayed over the current frame of the red window. 
    Use the arrow keys to align the movies.
    """
    def __init__(self):
        BaseProcess_noPriorWindow.__init__(self)
        self.current_red = None
        self.current_green = None

    def __call__(self, red_window, green_window, x_shift, y_shift):
        '''
        plots red_window over green_window, shifted by (x_shift, y_shift) pixels
        '''
        self.unlink_frames(self.current_red, self.current_green)
        self.window.close()
        del self.window
        g.m.statusBar().showMessage("Applying beam splitter shift ...")
        t = time()
        imR = red_window.imageview.image
        t, w, h = imR.shape
        if red_window != None and green_window != None:
            self.newname = "%s shifted (%d, %d)" % (green_window.name, x_shift, y_shift)
            imG = green_window.imageview.image
        else:
            return
        imG = self.pad_shift(imG, imR, x_shift, y_shift)
        self.command = 'beam_splitter(%s, %s, %s, %s)' % (red_window, green_window, x_shift, y_shift)
        g.m.statusBar().showMessage("Successfully shifted (%s s)" % (time() - t))
        self.newtif = imG
        win = self.end()
        win.imageview.setLevels(self.minlevel, self.maxlevel)
        return win

    def pad_shift(self, imGreen, imR, x_shift, y_shift):
        '''
        shift imGreen by (x_shift, y_shift) onto an empty array of size similar to imRed
        '''
        if imGreen.ndim == 2:
            g_mx, g_my = imGreen.shape
        elif imGreen.ndim == 3:
            g_mt, g_mx, g_my = imGreen.shape
        if imR.ndim == 2:
            r_mx, r_my = imR.shape
        elif imR.ndim == 3:
            r_mt, r_mx, r_my = imR.shape


        if imGreen.ndim == 2:
            imGreen_shifted = np.zeros((r_mx, r_my))
            imGreen_shifted[:g_mx, :g_my] = imGreen
            imGreen_shifted = shift(imGreen_shifted, (x_shift, y_shift))
        elif imGreen.ndim == 3:
            imGreen_shifted = np.zeros((g_mt, r_mx, r_my))
            r_left = max(0, x_shift)
            r_top = max(0, y_shift)
            r_right = min(r_mx, g_mx + x_shift)
            r_bottom = min(r_my, g_my + y_shift)

            g_left = max(0, -x_shift)
            g_top = max(0, -y_shift)
            g_right = min(g_mx, r_mx - x_shift)
            g_bottom = min(g_my, r_my - y_shift)
            
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
        if event.key() == 16777220:  # Enter
            self.ui.close()
            self.call_from_gui()
            
        event.accept()

    def closeEvent(self, event):
        self.unlink_frames(self.current_red, self.current_green)
        BaseProcess_noPriorWindow.closeEvent(self, event)

    def indexChanged(self, i):
        if self.ui.isVisible():
            self.preview()

    def unlink_frames(self, *windows):
        for window in windows:
            if window != None:
                try:
                    window.sigTimeChanged.disconnect(self.indexChanged)
                except:
                    pass

    def preview(self):
        winRed = self.getValue('red_window')
        winGreen = self.getValue('green_window')
        x_shift = self.getValue('x_shift')
        y_shift = self.getValue('y_shift')
        
        if not winRed or not winGreen:
            if hasattr(self, "window"):
                self.window.hide()
            return

        if self.current_red != winRed:
            self.unlink_frames(self.current_red)
            winRed.sigTimeChanged.connect(self.indexChanged)
            self.current_red = winRed
        
        if self.current_green != winGreen:
            self.unlink_frames(self.current_green)
            winGreen.sigTimeChanged.connect(self.indexChanged)
            self.current_green = winGreen

        imG = winGreen.image
        imR = winRed.image
        if imR.ndim == 3:
            imR = imR[winRed.currentIndex]
        if imG.ndim == 3:
            imG = imG[winGreen.currentIndex]
        if np.size(imR) < np.size(imG):
            imG, imR = imR, imG

        imG = self.pad_shift(imG, imR, x_shift, y_shift)
        self.minlevel = np.min([np.min(imG), np.min(imR)])
        self.maxlevel = np.max([np.max(imG), np.max(imR)])
        
        imZ = np.zeros_like(imR)
        stacked = np.dstack((imR, imG, imZ))
        if not hasattr(self, 'window') or self.window.closed:
            self.window = Window(stacked, name="Beam Splitter Overlay Frame")
            self.window.imageview.setLevels(self.minlevel, self.maxlevel)
            self.window.imageview.keyPressEvent = self.keyPressed
        else:
            self.window.imageview.setImage(stacked, autoLevels=False, autoRange=False)
        self.window.show()

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