#!/usr/bin/env pythonw
import wx # allows us to make the GUI
import re # regular expressions
import os # Used to make the code portable
import h5py # Allows us the read the data files
import matplotlib
import new_cmaps
import matplotlib.colors as mcolors
from numpy import arange, sin, pi

matplotlib.use('WXAgg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_wxagg import \
    FigureCanvasWxAgg as FigCanvas, \
    NavigationToolbar2WxAgg as NavigationToolbar

class FilesWrapper(object):
    """A simple class wrapper to allow us to make lists of the seperate paths
    of the files and store one of the loaded hdf5 files"""
    def __init__(self, plist=[],f_hdf5=''):
         self.paths = plist
         self.file = f_hdf5



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
        self.value = value
        self.value = self.constrain(value)
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




class FloatSliderGroup(Knob):
    def __init__(self, parent, label, param):
        self.sliderLabel = wx.StaticText(parent, label=label)
        self.sliderText = wx.TextCtrl(parent, -1, style=wx.TE_PROCESS_ENTER)
        self.slider = wx.Slider(parent, -1)
        self.slider.SetMax(param.maximum*1000)
        self.slider.SetMax(param.minimum*1000)
        self.setKnob(param.value)

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.sliderLabel, 0, wx.EXPAND | wx.ALIGN_CENTER | wx.ALL, border=2)
        sizer.Add(self.sliderText, 0, wx.EXPAND | wx.ALIGN_CENTER | wx.ALL, border=2)
        sizer.Add(self.slider, 1, wx.EXPAND)
        self.sizer = sizer

        self.slider.Bind(wx.EVT_SLIDER, self.sliderHandler)
        self.sliderText.Bind(wx.EVT_TEXT_ENTER, self.sliderTextHandler)

        self.param = param
        self.param.attach(self)

    def sliderHandler(self, evt):
        value = evt.GetInt() / 1000.
        self.param.set(value)

    def sliderTextHandler(self, evt):
        value = float(self.sliderText.GetValue())
        self.param.set(value)

    def setKnob(self, value):

        self.sliderText.SetValue('%g'%value)
        self.slider.SetValue(value*1000)

class IntSliderGroup(Knob):
    def __init__(self, parent, label, param):
        self.sliderLabel = wx.StaticText(parent, label=label)
        self.sliderText = wx.TextCtrl(parent, -1, style=wx.TE_PROCESS_ENTER)
        self.slider = wx.Slider(parent, -1)
        self.slider.SetMax(param.maximum)
        self.slider.SetMin(param.minimum)
        self.setKnob(param.value)

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.sliderLabel, 0, wx.EXPAND | wx.ALIGN_CENTER | wx.ALL, border=2)
        sizer.Add(self.sliderText, 0, wx.EXPAND | wx.ALIGN_CENTER | wx.ALL, border=2)
        sizer.Add(self.slider, 1, wx.EXPAND)
        self.sizer = sizer

        self.slider.Bind(wx.EVT_SCROLL_THUMBRELEASE, self.sliderHandler)
        self.sliderText.Bind(wx.EVT_TEXT_ENTER, self.sliderTextHandler)

        self.param = param
        self.param.attach(self)

    def sliderHandler(self, evt):
        value = evt.GetInt()
        self.param.set(value)

    def sliderTextHandler(self, evt):
        value = float(self.sliderText.GetValue())
        self.param.set(value)

    def setKnob(self, value):
        self.sliderText.SetValue('%g'%value)
        self.slider.SetValue(value)

class CanvasPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        print self.Parent.dirname
        self.draw()


    def sizeHandler(self, *args, **kwargs):
        self.canvas.SetSize(self.GetSize())

    def draw(self):
        self.figure = Figure()
        self.canvas = FigCanvas(self, -1, self.figure)
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.Bind(wx.EVT_SIZE, self.sizeHandler)
        self.axes = self.figure.add_subplot(111)
        self.axes.hist2d(self.Parent.prtl.file['xi'][:],self.Parent.prtl.file['ui'][:], bins = [200,200],cmap = new_cmaps.magma, norm = mcolors.PowerNorm(0.4))
        self.canvas.draw()

    def setKnob(self, value):
        self.draw()


class MainWindow(wx.Frame):
    """ We simply derive a new class of Frame """
    def __init__(self, parent, title):
        wx.Frame.__init__(self, parent, title =title)

        self.CreateStatusBar() # A statusbar in the bottom of the window
        # intialize the working directory
        # Setting up the menu.
        filemenu = wx.Menu()

        # wx.ID_ABOUT and wx.ID_EXIT are standard IDs provided by wxWidgets.
        menuAbout = filemenu.Append(wx.ID_ABOUT, '&About', ' Information about this program')
        menuExit = filemenu.Append(wx.ID_EXIT,'E&xit', 'Terminate the program')
        menuOpen = filemenu.Append(wx.ID_OPEN, '&Open Directory\tCtrl+o', ' Open the Directory')

        # create the menubar
        menuBar = wx.MenuBar()
        menuBar.Append(filemenu, '&File') # Adding the 'filemenu; to the MenuBar
        self.SetMenuBar(menuBar) # Add the menubar to the frame

        # create a bunch of regular expressions used to search for files
        f_re = re.compile('flds.tot.*')
        p_re = re.compile('prtl.tot.*')
        s_re = re.compile('spect.*')
        par_re = re.compile('param.*')
        self.re_list = [f_re, p_re, s_re, par_re]

        # make a bunch of objects that will store all our file names & values
        self.flds = FilesWrapper()
        self.prtl = FilesWrapper()
        self.param = FilesWrapper()
        self.spect = FilesWrapper()
        self.file_list = [self.flds, self.prtl,  self.spect, self.param]

        # Look for the tristan output files and load the file paths into
        # previous objects
        self.dirname = os.curdir
        self.findDir()


        # Load the first time of all the files using h5py
        for elm in self.file_list:
            print elm.paths[0]
            elm.file = h5py.File(os.path.join(self.dirname,elm.paths[0]), 'r')

        # Make the knob & slider that will control the time slice of the
        # simulation

        self.timeStep = Param(1, minimum=1, maximum=len(self.flds.paths))
        self.timeStep.attach(self)

        self.timeSliderGroup = IntSliderGroup(self, label=' n:', \
            param=self.timeStep)


        self.graph = CanvasPanel(self)
        self.timeStep.attach(self.graph)

        mainsizer = wx.BoxSizer(wx.VERTICAL)
        mainsizer.Add(self.graph,1, wx.EXPAND)
        mainsizer.Add(self.timeSliderGroup.sizer, 0, wx.EXPAND | wx.ALIGN_CENTER | wx.ALL, border=5)
        self.SetSizerAndFit(mainsizer)

        # Set events.
        self.Bind(wx.EVT_MENU, self.OnAbout, menuAbout)
        self.Bind(wx.EVT_MENU, self.OnExit, menuExit)
        self.Bind(wx.EVT_MENU, self.OnOpen, menuOpen)

        self.Show(True)

    def setKnob(self, value):
        for elm in self.file_list:
            elm.file.close()
            elm.file = h5py.File(os.path.join(self.dirname,elm.paths[value-1]), 'r')




    # Define the Main Window functions
    def OnAbout(self,e):
        # A message dialog box with an OK buttion. wx.OK is a standardID in wxWidgets.
        dlg = wx.MessageDialog(self, 'A small text editor', 'About Simple Editor', wx.OK)
        dlg.ShowModal() # show it
        dlg.Destroy() # destroy it when finished

    def OnExit(self, e):
        self.Close(True)

    def pathOK(self):
        """ Test to see if the current path contains tristan files
        using regular expressions, then generate the lists of files
        to iterate over"""

        is_okay = True
        for i in range(len(self.re_list)):
            self.file_list[i].paths = (filter(self.re_list[i].match, os.listdir(self.dirname)))
            self.file_list[i].paths.sort()
            is_okay &= len(self.file_list[i].paths) > 0

        return is_okay

    def OnOpen(self,e):
        """open a file"""
        dlg = wx.DirDialog(self, 'Choose the directory of the output files.', style = wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST)
        if dlg.ShowModal() == wx.ID_OK:
            self.dirname = dlg.GetPath()
        dlg.Destroy()
        if not self.pathOK():
            self.findDir('Directory must contain either the output directory or all of the following: flds.tot.*, ptrl.tot.*, params.*, spect.*')


    def findDir(self, dlgstr = 'Choose the directory of the output files.'):
        """Look for /ouput folder, where the simulation results are
        stored. If output files are already in the path, they are
        automatically loaded"""
        dirlist = os.listdir(self.dirname)
        if 'output' in dirlist:
            self.dirname = os.path.join(self.dirname, 'output')
        if not self.pathOK():
            dlg = wx.DirDialog(self,
                               dlgstr,
                               style = wx.DD_DEFAULT_STYLE
                               | wx.DD_DIR_MUST_EXIST)
            if dlg.ShowModal() == wx.ID_OK:
                self.dirname = dlg.GetPath()
            dlg.Destroy()
            if not self.pathOK() :
                self.findDir('Directory must contain either the output directory or all of the following: flds.tot.*, ptrl.tot.*, params.*, spect.*')

app = wx.App(False)
frame = MainWindow(None, 'Iseult')
app.MainLoop()
