#pip install keyboard
#pip install win32gui

import sys
import win32gui
import random
import keyboard
import time

class Control_Pawn():
    """
    Class to control pawn in standalone UE session.
    """
    def __init__(self):
        """
        Init class.
        """
        # a - strafe left
        # d - strafe right
        # w - forward
        # s - backward
        # u - up
        # o - down
        # l - left
        # r - right
        self.keys = ['a','d','w','u','o','l','r']
        self.stand_alone_window = '64-bit Development' # appears in standalone window title
        self.window_ID = None
        self.find_window()
        if self.window_ID:
            self.generate_random_keys()

    def generate_random_keys(self):
        """
        test function to generate random key presses
        """
        for i in range (100):
            # force focus to stand alone
            win32gui.SetForegroundWindow(self.window_ID)
            key = random.choice(self.keys)
            keyboard.press(key)
            time.sleep(.1)
            keyboard.release(key)

    def callback(self, hwnd, strings):
        if win32gui.IsWindowVisible(hwnd):
            window_title = win32gui.GetWindowText(hwnd)
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            if window_title and right-left and bottom-top:
                strings.append('0x{:08x}: "{}"'.format(hwnd, window_title))
                if self.stand_alone_window in window_title:
                    self.window_ID = hwnd
        return True
    
    def find_window(self):
        """
        Find standalone window.
        """
        win_list = []  # list of strings containing win handles and window titles
        win32gui.EnumWindows(self.callback, win_list)  # populate list

Control_Pawn()