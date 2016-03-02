#!/usr/bin/env pythonw
import Tkinter as Tk
import ttk as ttk
import matplotlib
import numpy as np
import numpy.ma as ma
import new_cmaps
import matplotlib.colors as mcolors
import matplotlib.gridspec as gridspec
import matplotlib.patheffects as PathEffects

class SpectralPanel:
    # A diction of all of the parameters for this plot with the default parameters

    plot_param_dict = {'spectral_type': 0, #0 dn/dp, 1 = dn/dE
                       'show_ions': 1,
                       'show_electrons': 1,
                       'rest_frame': False
    }

    def __init__(self, parent, figwrapper):
        self.settings_window = None
        self.FigWrap = figwrapper
        self.parent = parent
        self.ChartTypes = self.FigWrap.PlotTypeDict.keys()
        self.chartType = self.FigWrap.chartType
        self.figure = self.FigWrap.figure
        self.InterpolationMethods = ['nearest', 'bilinear', 'bicubic', 'spline16',
            'spline36', 'hanning', 'hamming', 'hermite', 'kaiser', 'quadric',
            'catrom', 'gaussian', 'bessel', 'mitchell', 'sinc', 'lanczos']


    def ChangePlotType(self, str_arg):
        self.FigWrap.ChangeGraph(str_arg)

    def set_plot_keys(self):
        '''A helper function that will insure that each hdf5 file will only be
        opened once per time step'''
        # First make sure that omega_plasma & istep is loaded so we can fix the
        # integrate over the specified regions

        self.arrs_needed = ['c_omp', 'istep', 'gamma', 'xsl']
        if self.GetPlotParam('rest_frame'):
            # Set the loading of the rest frame spectra
            self.arrs_needed.append('specerest')
            self.arrs_needed.append('specprest')
        else:
            # Load the normal spectra
            self.arrs_needed.append('spece')
            self.arrs_needed.append('specp')


        return self.arrs_needed

    def draw(self):
        # get c_omp and istep to convert cells to physical units
        self.c_omp = self.FigWrap.LoadKey('c_omp')[0]
        self.istep = self.FigWrap.LoadKey('istep')[0]
        self.xsl = self.FigWrap.LoadKey('xsl')/self.c_omp
        self.gamma = self.FigWrap.LoadKey('gamma')

        if self.GetPlotParam('rest_frame'):
            self.spece = self.FigWrap.LoadKey('specerest')
            self.specp = self.FigWrap.LoadKey('specprest')
        else:
            self.spece = self.FigWrap.LoadKey('spece')
            self.specp = self.FigWrap.LoadKey('specp')


        # In output.F90, spece (specp) is defined by the number of electons (ions)
        # divided by gamma in each logrithmic energy bin. So we multiply by gamma.

        for i in range(len(self.xsl)):
            self.spece[:,i] *= self.gamma
            self.specp[:,i] *= self.gamma
        ###############################
        ###### energy spectra, f=(dN/dE)/N
        ###############################
        self.dgamma = np.empty(len(self.gamma))
        delta=np.log10(self.gamma[-1]/self.gamma[0])/len(self.gamma)
        for i in range(len(self.dgamma)):
            self.dgamma[i]=self.gamma[i]*(10**delta-1.)

         # Select the x-range from which to take the spectra
        e_left_loc = self.parent.shock_loc/self.c_omp*self.istep+self.parent.e_e_region[0]
        e_right_loc = self.parent.shock_loc/self.c_omp*self.istep+self.parent.e_e_region[1]

        eL = self.xsl.searchsorted(e_left_loc)
        eR = self.xsl.searchsorted(e_right_loc, side='right')

        i_left_loc = self.parent.shock_loc/self.c_omp*self.istep+self.parent.ion_e_region[0]
        i_right_loc = self.parent.shock_loc/self.c_omp*self.istep+self.parent.ion_e_region[1]

        iL = self.xsl.searchsorted(i_left_loc)
        iR = self.xsl.searchsorted(i_right_loc, side='right')
        # total particles in each linear x bin
        norme = np.copy(self.xsl)
        normp = np.copy(self.xsl)
        for i in range(len(norme)):
            norme[i]=sum(self.spece[:,i])
            normp[i]=sum(self.specp[:,i])

        # energy distribution, f(E)=(dn/dE)/N
        self.fe=np.empty(len(self.gamma))
        self.fp=np.empty(len(self.gamma))


        for k in range(len(self.fe)):
            self.fe[k]=sum(self.spece[k][eL:eR])/(sum(norme[eL:eR])*self.dgamma[k])
            self.fp[k]=sum(self.specp[k][iL:iR])/(sum(normp[iL:iR])*self.dgamma[k])


        #  NOTE: gamma ---> gamma-1 ***
        self.edist=self.gamma*self.fe
        self.pdist=self.gamma*self.fp

        self.momentum=np.sqrt((self.gamma+1)**2-1.)
        self.femom=self.fe/(4*np.pi*self.momentum)/(self.gamma+1)
        self.momedist=self.femom*self.momentum**4
        self.fpmom=self.fp/(4*np.pi*self.momentum)/(self.gamma+1)
        self.mompdist=self.fpmom*self.momentum**4

        # Set the tick color
        tick_color = 'black'

        # Create a gridspec to handle spacing better
        self.gs = gridspec.GridSpecFromSubplotSpec(100,100, subplot_spec = self.parent.gs0[self.FigWrap.pos])#, bottom=0.2,left=0.1,right=0.95, top = 0.95)

        # load the density values
        self.axes = self.figure.add_subplot(self.gs[18:92,:])

        if self.GetPlotParam('spectral_type') == 0: #Show the momentum dist
            self.axes.plot(self.momentum, self.momedist, color = self.parent.electron_color)
            self.axes.plot(self.momentum, self.mompdist, color = self.parent.ion_color)
            self.axes.set_xscale("log")
            self.axes.set_yscale("log")
            self.axes.set_axis_bgcolor('lightgrey')
            self.axes.set_xlim(-0.05,500)
            self.axes.set_ylim(1E-6,1)
            self.axes.tick_params(labelsize = 10, color=tick_color)

            self.axes.set_xlabel(r'$p(mc)$', labelpad = self.parent.xlabel_pad, color = 'black')
            self.axes.set_ylabel(r'$p^4f(p)$', labelpad = self.parent.ylabel_pad, color = 'black')

        if self.GetPlotParam('spectral_type') == 1: #Show the energy dist
            self.axes.plot(self.gamma, self.edist, color = self.parent.electron_color)
            self.axes.plot(self.gamma, self.pdist, color = self.parent.ion_color)
            self.axes.set_xscale("log")
            self.axes.set_yscale("log")
            self.axes.set_axis_bgcolor('lightgrey')
            self.axes.set_xlim(1e-5,1E3)
            self.axes.set_ylim(1E-6,1)
            self.axes.tick_params(labelsize = 10, color=tick_color)

            self.axes.set_xlabel(r'$E(mc^2)$', labelpad = -2, color = 'black')
            self.axes.set_ylabel(r'$E(dn/dE)/n$', labelpad = 0, color = 'black')

    def GetPlotParam(self, keyname):
        return self.FigWrap.GetPlotParam(keyname)

    def SetPlotParam(self, keyname, value, update_plot = True):
        self.FigWrap.SetPlotParam(keyname, value, update_plot = update_plot)

    def OpenSettings(self):
        if self.settings_window is None:
            self.settings_window = SpectraSettings(self)
        else:
            self.settings_window.destroy()
            self.settings_window = SpectraSettings(self)


class SpectraSettings(Tk.Toplevel):
    def __init__(self, parent):
        self.parent = parent
        Tk.Toplevel.__init__(self)

        self.wm_title('Spectrum (%d,%d) Settings' % self.parent.FigWrap.pos)
        self.parent = parent
        frm = ttk.Frame(self)
        frm.pack(fill=Tk.BOTH, expand=True)
        self.protocol('WM_DELETE_WINDOW', self.OnClosing)
        #Create some sizers

        self.InterpolVar = Tk.StringVar(self)
        self.InterpolVar.set(self.parent.GetPlotParam('interpolation')) # default value
        self.InterpolVar.trace('w', self.InterpolChanged)

        ttk.Label(frm, text="Interpolation Method:").grid(row=0, column = 2)
        InterplChooser = apply(ttk.OptionMenu, (frm, self.InterpolVar, self.parent.GetPlotParam('interpolation')) + tuple(self.parent.InterpolationMethods))
        InterplChooser.grid(row =0, column = 3, sticky = Tk.W + Tk.E)

        # Create the OptionMenu to chooses the Chart Type:
        self.ctypevar = Tk.StringVar(self)
        self.ctypevar.set(self.parent.chartType) # default value
        self.ctypevar.trace('w', self.ctypeChanged)

        ttk.Label(frm, text="Choose Chart Type:").grid(row=0, column = 0)
        cmapChooser = apply(ttk.OptionMenu, (frm, self.ctypevar, self.parent.chartType) + tuple(self.parent.ChartTypes))
        cmapChooser.grid(row =0, column = 1, sticky = Tk.W + Tk.E)


        self.TwoDVar = Tk.IntVar(self) # Create a var to track whether or not to plot in 2-D
        self.TwoDVar.set(self.parent.GetPlotParam('twoD'))
        cb = ttk.Checkbutton(frm, text = "Show in 2-D",
                variable = self.TwoDVar,
                command = self.Change2d)
        cb.grid(row = 1, sticky = Tk.W)

        # the Radiobox Control to choose the Field Type
        self.DensList = ['dens_e', 'rho']
        self.DensTypeVar  = Tk.IntVar()
        self.DensTypeVar.set(self.parent.GetPlotParam('dens_type'))

        ttk.Label(frm, text='Choose Density:').grid(row = 2, sticky = Tk.W)

        for i in range(len(self.DensList)):
            ttk.Radiobutton(frm,
                text=self.DensList[i],
                variable=self.DensTypeVar,
                command = self.RadioField,
                value=i).grid(row = 3+i, sticky =Tk.W)


        # Control whether or not Cbar is shown
        self.CbarVar = Tk.IntVar()
        self.CbarVar.set(self.parent.GetPlotParam('show_cbar'))
        cb = ttk.Checkbutton(frm, text = "Show Color bar",
                        variable = self.CbarVar,
                        command = lambda:
                        self.parent.SetPlotParam('show_cbar', self.CbarVar.get()))
        cb.grid(row = 6, sticky = Tk.W)

        # show shock
        self.ShockVar = Tk.IntVar()
        self.ShockVar.set(self.parent.GetPlotParam('show_shock'))
        cb = ttk.Checkbutton(frm, text = "Show Shock",
                        variable = self.ShockVar,
                        command = lambda:
                        self.parent.SetPlotParam('show_shock', self.ShockVar.get()))
        cb.grid(row = 6, column = 1, sticky = Tk.W)




    def Change2d(self):
        if self.TwoDVar.get() == self.parent.GetPlotParam('twoD'):
            pass
        else:
            self.parent.SetPlotParam('twoD', self.TwoDVar.get())



    def ctypeChanged(self, *args):
        if self.ctypevar.get() == self.parent.chartType:
            pass
        else:
            self.parent.ChangePlotType(self.ctypevar.get())
            self.destroy()

    def InterpolChanged(self, *args):
        if self.InterpolVar.get() == self.parent.GetPlotParam('interpolation'):
            pass
        else:
            self.parent.SetPlotParam('interpolation', self.InterpolVar.get())

    def RadioField(self):
        if self.DensTypeVar.get() == self.parent.GetPlotParam('dens_type'):
            pass
        else:
            self.parent.SetPlotParam('dens_type', self.DensTypeVar.get())


    def OnClosing(self):
        self.parent.settings_window = None
        self.destroy()
