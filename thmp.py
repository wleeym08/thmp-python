import os
import sys

'''
Support for Python 2 / Tkinter
if sys.version_info.major == 3:
    from tkinter import *
    from tkinter import messagebox as mb
    from tkinter import ttk
else:
    from Tkinter import *
    import tkMessageBox as mb
    import ttk
'''

from tkinter import *
from tkinter import messagebox as mb
from tkinter import ttk
import pyaudio
import threading
from struct import pack, unpack
from time import sleep
import json

CHUNK = 1024

class App:
    def __init__(self, master):
        frame = Frame(master)
        frame.grid()

        try:
            with open('config.json', 'rb') as config:
                self.conf = json.loads(config.read().decode('utf-8-sig'))
        except FileNotFoundError:
            print('Failed to load. No config file was found!')
            sys.exit(-1)

        # Elements
        self.label1 = Label(frame, text='Game:')
        self.label1.grid(row=0, column=0, padx=5, pady=2, sticky=E)
        self.label2 = Label(frame, text='Song:')
        self.label2.grid(row=1, column=0, padx=5, pady=2, sticky=E)

        self.box_title = ttk.Combobox(frame, state='readonly', width=22)
        self.box_title.grid(row=0, column=1, padx=5, pady=2, sticky=W)
        self.box_title['values'] = self.conf['titles']

        self.box_song = ttk.Combobox(frame, state='readonly', width=40)
        self.box_song.grid(row=1, column=1, padx=5, pady=2, sticky=W)
        self.box_title.current(0)
        self.box_song['values'] = list(sorted(self.conf['songs'] \
            [self.box_title.current()].keys()))
        self.box_song.current(0)
        self.box_title.bind('<<ComboboxSelected>>', self.changeTitle)

        self.button_play = Button(frame, text='PLAY', width=10, fg='red', \
            command=self.on_play)
        self.button_play.grid(row=0, column=2, padx=5, pady=2, sticky=E)
        self.button_pause = Button(frame, text='PAUSE', width=10, fg='red', \
            command=self.on_pause)
        # Add pause button...
        self.button_pause.grid(row=1, column=2, padx=5, pady=2, sticky=E)
        self.button_stop = Button(frame, text='STOP', width=10, fg='red', \
            command=self.on_stop)
        self.button_stop.grid(row=0, column=3, padx=5, pady=2, sticky=E)
        self.slider = Scale(master, from_=0, to=100, resolution=1, \
            sliderlength=15, length=60, borderwidth=3, label='Volume:')
        self.slider.set(20)
        self.slider.grid(row=0, column=6, padx=5, pady=2, rowspan=2)

        # Playback control / states
        self.playback_thread = None
        self.adjustVolume_thread = None
        self.is_playing = False
        self.volume = self.slider.get() * 0.01
        self.current_song = []
        self.current_offset = None
        self.intro_size = None
        self.loop_offset = None
        self.end_offset = None

    def changeTitle(self, event):
        self.box_song['values'] = list(sorted(self.conf['songs'] \
            [self.box_title.current()].keys()))
        self.box_song.current(0)

    def playback(self):
        p = pyaudio.PyAudio()
        stream = p.open(format=pyaudio.paInt16, channels=2, rate=44100, \
            output=True)

        temp = [self.box_title.current(), self.box_song.current()]
        if temp != self.current_song:
            self.current_song = temp
            info = self.conf['songs'][self.box_title.current()] \
                [self.box_song.get()]
            self.intro_offset = int(info[0], base=16)
            intro_size = int(info[1], base=16)
            total_size = int(info[2], base=16)
            self.loop_offset = self.intro_offset + intro_size
            self.end_offset = self.intro_offset + total_size
            self.current_offset = self.intro_offset

        try:
            with open(self.conf['paths'][self.box_title.current()], 'rb') as zwav:
                zwav.seek(self.current_offset)
                data = zwav.read(CHUNK)
                self.current_offset += CHUNK
                while self.is_playing:
                    sample = unpack('<%uh' % (len(data) / 2), data)
                    data = pack('<%uh' % (len(data) / 2), \
                        *[int(round(pitch * self.volume)) for pitch in sample])
                    stream.write(data)

                    data = zwav.read(CHUNK)
                    self.current_offset += CHUNK
                    if zwav.tell() >= self.end_offset:
                        self.current_offset = self.loop_offset
                        zwav.seek(self.current_offset)

        except FileNotFoundError:
            mb.showwarning('Error', 'Failed to open .dat file!')
        except IndexError:
            mb.showwarning('Error', 'Failed to read the path of .dat file!')

        stream.stop_stream()
        stream.close()
        p.terminate()

        self.is_playing = False

    def aujustVolume(self):
        while self.is_playing:
            self.volume = self.slider.get() * 0.01
            sleep(0.1)

    def on_play(self):
        if self.is_playing:
            self.is_playing = False
            self.adjustVolume_thread.join()
            self.playback_thread.join()

        self.is_playing = True
        self.playback_thread = threading.Thread(target=self.playback)
        self.playback_thread.start()
        self.adjustVolume_thread = threading.Thread(target=self.aujustVolume)
        self.adjustVolume_thread.start()

    def on_pause(self):
        if self.is_playing:
            self.is_playing = False
            self.adjustVolume_thread.join()
            self.playback_thread.join()

    def on_stop(self):
        if self.is_playing:
            self.is_playing = False
            self.adjustVolume_thread.join()
            self.playback_thread.join()

        self.current_offset = self.intro_offset

    def on_quit(self):
        if mb.askokcancel("Quit", "Do you want to quit?"):
            if self.is_playing:
                self.is_playing = False
                self.adjustVolume_thread.join()
                self.playback_thread.join()

            root.destroy()

# Initialize the window
root = Tk()
app = App(root)
root.title('Touhou Mini Player v0.6')
root.geometry('700x70')
root.resizable(0, 0)
root.protocol('WM_DELETE_WINDOW', app.on_quit)

'''
if os.name == 'nt':
    root.wm_iconbitmap(bitmap='thmp.ico')
else:
    root.wm_iconbitmap(bitmap='thmp.xbm')
'''

root.mainloop()
