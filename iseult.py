#! /usr/bin/env pythonw

import re # regular expressions
import os, sys # Used to make the code portable
import h5py # Allows us the read the data files
from threading import Thread
import time,string
import matplotlib
import new_cmaps
import numpy as np
import matplotlib.colors as mcolors
import matplotlib.gridspec as gridspec
from phase_plots import PhasePanel
from test_plots import TestPanel

matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

import Tkinter as Tk
import ttk as ttk
import tkFileDialog

def destroy(e):
    sys.exit()

colors=[None]*10
for i in range(len(colors)):
    colors[i]=np.random.rand(5,5)

class Spinbox(ttk.Entry):

    def __init__(self, master=None, **kw):
        ttk.Entry.__init__(self, master, "ttk::spinbox", **kw)

    def current(self, newindex=None):
        return self.tk.call(self._w, 'current', index)

    def set(self, value):
        return self.tk.call(self._w, 'set', value)

class SubPlotWrapper:
    """A simple class that will eventually hold all of the information
    about each sub_plot in the Figure"""

    def __init__(self, parent, figure=None, sub_plot_spec = None, ctype=None):
        self.parent = parent
        self.chartType = ctype
        # A dictionary that contains all of the plot types.
        self.PlotTypeDict = {'PhasePlot': PhasePanel, 'TestPlot': TestPanel}
        # A dictionary that will store where everything is in Hdf5 Files
        self.GenParamDict()
        self.figure = figure
#        self.graph = graph


    def LoadKey(self, h5key):
        pkey = self.parent.H5KeyDict[h5key]
        with h5py.File(os.path.join(self.parent.dirname,self.parent.PathDict[pkey][self.parent.timeStep.value-1]), 'r') as f:
            return f[h5key][:]

    def ChangeGraph(self, str_arg):
        self.chartType = str_arg
        self.parent.ChangeGraph()

    def GenParamDict(self):
        # Generate a dictionary that will store all of the params at dict['ctype']['param_name']
        self.PlotParamsDict = {elm: '' for elm in self.PlotTypeDict.keys() }
        for elm in self.PlotTypeDict.keys():
            self.PlotParamsDict[elm] = {x : '' for x in self.PlotTypeDict[elm].plot_param_list}

    def SetPlotParam(self, pname, val, ctype = None):
        if ctype is None:
            ctype = self.chartType
        self.PlotParamsDict[ctype][pname] = val

    def GetPlotParam(self, pname, ctype = None):
        if ctype is None:
            ctype = self.chartType

        return self.PlotParamsDict[ctype][pname]

    def SetGraph(self, parent, FigWrap, ctype = None, overwrite = True):
        if ctype:
            self.chartType = ctype
        self.graph = self.PlotTypeDict[self.chartType](parent, self, overwrite)

class Knob:
    """
    Knob - simple class with a "setKnob" method.
    A Knob instance is attached to a Param instance, e.g., param.attach(knob)
    Base class is for documentation purposes.
    """
    def setKnob(self, value):
        pass

class Param:

    """
    The idea of the "Param" class is that some parameter in the GUI may have
    several knobs that both control it and reflect the parameter's state, e.g.
    a slider, text, and dragging can all change the value of the frequency in
    the waveform of this example.
    The class allows a cleaner way to update/"feedback" to the other knobs when
    one is being changed.  Also, this class handles min/max constraints for all
    the knobs.
    Idea - knob list - in "set" method, knob object is passed as well
      - the other knobs in the knob list have a "set" method which gets
        called for the others.
    """
    def __init__(self, initialValue=None, minimum=0., maximum=1.):
        self.minimum = minimum
        self.maximum = maximum
        if initialValue != self.constrain(initialValue):
            raise ValueError('illegal initial value')
        self.value = initialValue
        self.knobs = []

    def attach(self, knob):
        self.knobs += [knob]

    def set(self, value, knob=None):
        self.value = self.constrain(value)
        for feedbackKnob in self.knobs:
            if feedbackKnob != knob:
                feedbackKnob.setKnob(self.value)
        return self.value

    def setMax(self, max_arg, knob=None):
        self.maximum = max_arg
        self.value = self.constrain(self.value)
        for feedbackKnob in self.knobs:
            if feedbackKnob != knob:
                feedbackKnob.setKnob(self.value)
        return self.value
    def constrain(self, value):
        if value <= self.minimum:
            value = self.minimum
        if value >= self.maximum:
            value = self.maximum
        return value


class PlaybackBar(Tk.Frame):

    """A Class that will handle the time-stepping in Iseult, and has the
    following, a step left button, a play/pause button, a step right button, a
    playbar, and a settings button."""

    def __init__(self, parent, param):
        Tk.Frame.__init__(self)
        self.parent = parent

        self.skipSize = 1
        self.waitTime = .2
        self.playPressed = False

        # This param should be the time-step of the simulation
        self.param = param

        # make a button that skips left
        self.skipLB = ttk.Button(self, text = '<', command = self.SkipLeft)
        self.skipLB.pack(side=Tk.LEFT, fill=Tk.BOTH, expand=0)

        # make the play button
        self.playB = ttk.Button(self, text = 'Play', command = self.PlayHandler)
        self.playB.pack(side=Tk.LEFT, fill=Tk.BOTH, expand=0)

        # a button that skips right
        self.skipRB = ttk.Button(self, text = '>', command = self.SkipRight)
        self.skipRB.pack(side=Tk.LEFT, fill=Tk.BOTH, expand=0)

        # An entry box that will let us choose the time-step
        ttk.Label(self, text='n= ').pack(side=Tk.LEFT, fill=Tk.BOTH, expand=0)

        # A StringVar for a box to type in a frame num, linked to self.param
        self.tstep = Tk.StringVar()
        # set it to the param value
        self.tstep.set(str(self.param.value))

        # the entry box
        self.txtEnter = ttk.Entry(self, textvariable=self.tstep, width=6)
        self.txtEnter.pack(side=Tk.LEFT, fill = Tk.BOTH, expand = 0)

        # A slider that will show the progress in the simulation as well as
        # allow us to select a time
        self.slider = ttk.Scale(self, from_=self.param.minimum, to=self.param.maximum, command = self.ScaleHandler)
        self.slider.set(self.param.value)
        self.slider.pack(side=Tk.LEFT, fill=Tk.BOTH, expand=1)

        # a settings button that should lauch some global settings.
        self.SettingsB= ttk.Button(self, text='Settings', command=self.OpenSettings)
        self.SettingsB.pack(side=Tk.LEFT, fill=Tk.BOTH, expand=0)

        #attach the parameter to the Playbackbar
        self.param.attach(self)

    def SkipLeft(self, e = None):
        self.param.set(self.param.value - self.skipSize)

    def SkipRight(self, e = None):
        self.param.set(self.param.value + self.skipSize)

    def PlayHandler(self, e = None):
        if not self.playPressed:
            # Set the value of play pressed to true, change the button name to
            # pause and start the play loop.
            self.playPressed = True
            self.playB.config(text='Pause')
            self.after(int(self.waitTime*1E3), self.blink)
        else:
            # pause the play loop and set the button nameback to plau
            self.playPressed = False
            self.playB.config(text='Play')

    def OpenSettings(self):
        SettingsFrame(self.parent)


    def blink(self):
        if self.playPressed:
            # First check to see if the timestep can get larger
            if self.param.value == self.param.maximum:
                # push pause button
                self.PlayHandler()

            # otherwise skip right by size skip size
            else:
                self.param.set(self.param.value + self.skipSize)

            # start loopin'
            self.after(int(self.waitTime*1E3), self.blink)


    def TextCallback(self):
        try:
            #make sure the user types in a int
            if int(self.tstep.get()) != self.param.value:
                self.param.set(int(self.tstep.get()))
        except ValueError:
            #if they type in random stuff, just set it ot the param value
            self.tstep.set(str(self.param.value))

    def ScaleHandler(self, e):
        # if changing the scale will change the value of the parameter, do so
        if self.param.value != int(self.slider.get()):
            self.param.set(int(self.slider.get()))

    def setKnob(self, value):
        #set the text entry value
        self.tstep.set(str(value))
        #set the slider
        self.slider.set(value)

class SettingsFrame(Tk.Toplevel):
    def __init__(self, parent):

        Tk.Toplevel.__init__(self)
        self.wm_title('General Settings')
        self.parent = parent
        frm = ttk.Frame(self)
        frm.pack(fill=Tk.BOTH, expand=True)

        #Create some sizers


        # Make an entry to change the skip size
        self.skipSize = Tk.StringVar(self)
        self.skipSize.set(self.parent.playbackbar.skipSize) # default value
        self.skipSize.trace('w', self.SkipSizeChanged)
        ttk.Label(frm, text="Skip Size:").grid(row=0)
        self.skipEnter = ttk.Entry(frm, textvariable=self.skipSize, width = 6)
        self.skipEnter.grid(row =0, column = 1, sticky = Tk.W + Tk.E)

        # Make an button to change the wait time
        self.waitTime = Tk.StringVar(self)
        self.waitTime.set(self.parent.playbackbar.waitTime) # default value
        self.waitTime.trace('w', self.WaitTimeChanged)
        ttk.Label(frm, text="Playback Wait Time:").grid(row=1)
        self.waitEnter = ttk.Entry(frm, textvariable=self.waitTime, width = 6)
        self.waitEnter.grid(row =1, column = 1, sticky = Tk.W + Tk.E)

        # Have a list of the color maps
        self.cmapList = ['magma', 'inferno', 'plasma', 'viridis']
        self.cmapvar = Tk.StringVar(self)
        self.cmapvar.set(self.parent.cmap) # default value
        self.cmapvar.trace('w', self.CmapChanged)

        ttk.Label(frm, text="Color map:").grid(row=2)
        cmapChooser = apply(ttk.OptionMenu, (frm, self.cmapvar) + tuple(self.cmapList))
        cmapChooser.grid(row =2, column = 1, sticky = Tk.W + Tk.E)

        # Make an entry to change the number of columns
        self.columnNum = Tk.StringVar(self)
        self.columnNum.set(self.parent.numOfColumns.get()) # default value
        self.columnNum.trace('w', self.ColumnNumChanged)
        ttk.Label(frm, text="# of columns:").grid(row=3)
        self.ColumnSpin = Spinbox(frm,  from_=1, to=self.parent.maxCols, textvariable=self.columnNum, width = 6)
        self.ColumnSpin.grid(row =3, column = 1, sticky = Tk.W + Tk.E)

        # Make an entry to change the number of columns
        self.rowNum = Tk.StringVar(self)
        self.rowNum.set(self.parent.numOfRows.get()) # default value
        self.rowNum.trace('w', self.RowNumChanged)
        ttk.Label(frm, text="# of rows:").grid(row=4)
        self.RowSpin = Spinbox(frm, from_=1, to=self.parent.maxRows, textvariable=self.rowNum, width = 6)
        self.RowSpin.grid(row =4, column = 1, sticky = Tk.W + Tk.E)

        # A button to refresh the directory
        self.ReloadButton = ttk.Button(frm, text='Reload Directory', command = self.OnReload)
        self.ReloadButton.grid(row = 5)


    def CmapChanged(self, *args):
    # Note here that Tkinter passes an event object to onselect()
        self.parent.cmap = self.cmapvar.get()


    def SkipSizeChanged(self, *args):
    # Note here that Tkinter passes an event object to onselect()
        try:
            if self.skipSize.get() == '':
                pass
            else:
                self.parent.playbackbar.skipSize = int(self.skipSize.get())
        except ValueError:
            self.skipSize.set(self.parent.playbackbar.skipSize)

    def RowNumChanged(self, *args):
    # Note here that Tkinter passes an event object to onselect()
        try:
            if self.rowNum.get() == '':
                pass
            elif int(self.rowNum.get())<1:
                self.rowNum.set(1)
            elif int(self.rowNum.get())>self.parent.maxRows:
                self.rowNum.set(self.parent.maxRows)
            else:
                self.parent.numOfRows.set(int(self.rowNum.get()))
        except ValueError:
            self.rowNum.set(self.parent.numOfRows.get())

    def ColumnNumChanged(self, *args):
    # Note here that Tkinter passes an event object to onselect()
        try:
            if self.columnNum.get() == '':
                pass
            elif int(self.columnNum.get())<1:
                self.columnNum.set(1)
            elif int(self.columnNum.get())>self.parent.maxCols:
                self.columnNum.set(self.parent.maxCols)

            else:
                self.parent.numOfColumns.set(int(self.columnNum.get()))
        except ValueError:
            self.columnNum.set(self.parent.numOfColumns.get())

    def WaitTimeChanged(self, *args):
    # Note here that Tkinter passes an event object to onselect()
        try:
            if self.waitTime.get() == '':
                pass
            else:
                self.parent.playbackbar.waitTime = float(self.waitTime.get())
        except ValueError:
            self.waitTime.set(self.parent.playbackbar.waitTime)


    def OnReload(self, event=None):
        self.parent.findDir()


class MainApp(Tk.Tk):
    """ We simply derive a new class of Frame as the man frame of our app"""
    def __init__(self, name):

        Tk.Tk.__init__(self)
        self.update_idletasks()
        menubar = Tk.Menu(self)
        self.wm_title(name)

        # Set the number of rows and columns in the figure
        # (As well as the max rows)
        self.maxRows = 4
        self.maxCols = 3

        self.numOfRows = Tk.IntVar(self)
        self.numOfRows.set(3)
        self.numOfRows.trace('w', self.UpdateGridSpec)
        self.numOfColumns = Tk.IntVar(self)
        self.numOfColumns.set(2)
        self.numOfColumns.trace('w', self.UpdateGridSpec)


        fileMenu = Tk.Menu(menubar, tearoff=False)
        menubar.add_cascade(label="File", underline=0, menu=fileMenu)
        fileMenu.add_command(label= 'Open Directory', command = self.OnOpen, accelerator='Command+o')
        fileMenu.add_command(label="Exit", underline=1,
                             command=quit, accelerator="Ctrl+Q")
        self.config(menu=menubar)

        self.bind_all("<Control-q>", self.quit)
        self.bind_all("<Command-o>", self.OnOpen)


        # create a bunch of regular expressions used to search for files
        f_re = re.compile('flds.tot.*')
        prtl_re = re.compile('prtl.tot.*')
        s_re = re.compile('spect.*')
        param_re = re.compile('param.*')
        self.re_list = [f_re, prtl_re, s_re, param_re]

        self.PathDict = {'Flds': [], 'Prtl': [], 'Param': [], 'Spect': []}
        self.H5KeyDict ={}
        # Set the default color map

        self.cmap = 'inferno'

        # Make the object hold the timestep info
        self.TimeStep = Param(1, minimum=1, maximum=1000)

        # Look for the tristan output files and load the file paths into
        # previous objects
        self.dirname = os.curdir
        self.findDir()


        self.TimeStep.attach(self)
        self.DrawCanvas()

        self.playbackbar = PlaybackBar(self, self.TimeStep)
        self.playbackbar.pack(side=Tk.TOP, fill=Tk.BOTH, expand=0)
        self.update()
        # now root.geometry() returns valid size/placement
        self.minsize(self.winfo_width(), self.winfo_height())
        self.geometry("1200x700")
        self.bind('<Return>', self.TxtEnter)
        self.bind('<Left>', self.playbackbar.SkipLeft)
        self.bind('<Right>', self.playbackbar.SkipRight)
        self.bind('<space>', self.playbackbar.PlayHandler)

    def quit(self, event):
        print("quitting...")
        sys.exit(0)

    def GenH5Dict(self):
        for pkey in self.PathDict.keys():
            with h5py.File(os.path.join(self.dirname,self.PathDict[pkey][0]), 'r') as f:
                for h5key in f.keys():
                    self.H5KeyDict[h5key] = pkey

    def pathOK(self):
        """ Test to see if the current path contains tristan files
        using regular expressions, then generate the lists of files
        to iterate over"""
        dirlist = os.listdir(self.dirname)
        if 'output' in dirlist:
            self.dirname = os.path.join(self.dirname, 'output')
        is_okay = True
        i = 0
        for key in self.PathDict.keys():
            self.PathDict[key]= (filter(self.re_list[i].match, os.listdir(self.dirname)))
            self.PathDict[key].sort()
            is_okay &= len(self.PathDict[key]) > 0
            i += 1
        self.TimeStep.setMax(len(self.PathDict['Flds']))
        if len(self.H5KeyDict) == 0:
            self.GenH5Dict()
        return is_okay


    def OnOpen(self, e = None):
        """open a file"""
        tmpdir = tkFileDialog.askdirectory(title = 'Choose the directory of the output files', **self.dir_opt)
        if tmpdir != '':
            self.dirname = tmpdir
        if not self.pathOK():
#            p = MyDialog(self, 'Directory must contain either the output directory or all of the following: \n flds.tot.*, ptrl.tot.*, params.*, spect.*', title = 'Cannot find output files')
#            self.wait_window(p.top)
            self.findDir()

    def findDir(self, dlgstr = 'Choose the directory of the output files.'):
        """Look for /ouput folder, where the simulation results are
        stored. If output files are already in the path, they are
        automatically loaded"""
        # defining options for opening a directory
        self.dir_opt = {}
        self.dir_opt['initialdir'] = os.curdir
        self.dir_opt['mustexist'] = True
        self.dir_opt['parent'] = self

        if not self.pathOK():
            tmpdir = tkFileDialog.askdirectory(title = dlgstr, **self.dir_opt)
            if tmpdir != '':
                self.dirname = tmpdir
            if not self.pathOK():
#                p = MyDialog(self, 'Directory must contain either the output directory or all of the following: \n flds.tot.*, ptrl.tot.*, params.*, spect.*', title = 'Cannot find output files')
#                self.wait_window(p.top)
                self.FindDir()


    def DrawCanvas(self):
        '''Initializes the figure, and then packs it into the main window.
        Should only be called once.'''

        # figsize (w,h tuple in inches) dpi (dots per inch)
        #f = Figure(figsize=(5,4), dpi=100)
        self.f = Figure(figsize = (2,2), dpi = 100)

        # Generate all of the subplot wrappers. They are stored in a 2D list
        # where the index [i][j] corresponds to the ith row, jth column
        self.SubPlotList = []
        for i in range(self.maxRows):
            tmpList = [SubPlotWrapper(self, figure = self.f) for j in range(self.maxCols)]
            self.SubPlotList.append(tmpList)

        # divy up the figure into a bunch of subplots using GridSpec.
        self.gs0 = gridspec.GridSpec(self.numOfRows.get(),self.numOfColumns.get())

        self.a = self.f.add_subplot(self.gs0[0,0])
        self.a.pcolor(np.random.rand(5,5))
        # a tk.DrawingArea
        self.canvas = FigureCanvasTkAgg(self.f, master=self)
#        self.canvas._tkcanvas.pack(side=Tk.TOP, fill=Tk.BOTH, expand=1)

        self.canvas.show()
        self.canvas.get_tk_widget().pack(side=Tk.TOP, fill=Tk.BOTH, expand=1)

        #self.label = Label(self.top, text = 'Text',bg='orange')
        #self.label.grid()
        # initialize (time index t)

    def UpdateGridSpec(self, *args):
        '''A function that handles updates the gridspec that divides up of the
        plot into X x Y subplots'''
        self.gs0 = gridspec.GridSpec(self.numOfRows.get(),self.numOfColumns.get())
        self.RefreshCanvas()

    def RefreshCanvas(self):
        self.f.clf()
        self.a = self.f.add_subplot(self.gs0[0,0])
        self.a.pcolor(colors[self.TimeStep.value-1])

        self.canvas.show()
        self.canvas.get_tk_widget().update_idletasks()

        self.canvas.show()
    def setKnob(self, value):
        self.a.pcolor(colors[self.TimeStep.value-1])
        self.canvas.show()
        self.canvas.get_tk_widget().update_idletasks()

    # We need to do it this way so that pressing enter with focus anywhere on the app will cause the
    def TxtEnter(self, e):
        self.playbackbar.TextCallback()


        #   refresh the graph

if __name__ == "__main__":
    app = MainApp('Iseult')
    app.mainloop()
