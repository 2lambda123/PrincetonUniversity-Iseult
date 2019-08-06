import matplotlib as mpl
import  matplotlib.pyplot as plt
import numpy as np
from scipy.integrate import cumtrapz
import new_cmaps
import matplotlib.colors as mcolors
import matplotlib.gridspec as gridspec
import h5py
import os, sys
import re
import Tkinter, tkFileDialog

def pathOK(dirname):
    """ Test to see if the current path contains tristan files
    using regular expressions, then generate the lists of files
    to iterate over"""

    f_re = re.compile('flds.tot.*')
    is_okay = len(filter(f_re.match, os.listdir(dirname)))>0

    return is_okay

def findDir(parent, dlgstr = 'Choose the directory of the output files.'):
    """Look for /ouput folder, where the simulation results are
    stored. If output files are already in the path, they are
    automatically loaded"""
    # defining options for opening a directory


    dir_opt = {}
    dir_opt['initialdir'] = os.curdir
    dir_opt['mustexist'] = True



    tmpdir = tkFileDialog.askdirectory(parent = parent, title = dlgstr, **dir_opt)
    dirlist = os.listdir(tmpdir)
    if 'output' in dirlist:
        tmpdir = os.path.join(tmpdir, 'output')
    print tmpdir
    return tmpdir


# Be sure to call this with the output directory in the path
# create a bunch of regular expressions used to search for files
f_re = re.compile('flds.tot.*')
prtl_re = re.compile('prtl.tot.*')
s_re = re.compile('spect.*')
param_re = re.compile('param.*')
re_list = [f_re, prtl_re, s_re, param_re]
#root = Tkinter.Tk()
dirname = os.path.join(os.curdir,'output')
#root.destroy()

PathDict = {'Flds': [], 'Prtl': [], 'Param': [], 'Spect': []}

#fill all the paths
PathDict['Flds']= filter(f_re.match, os.listdir(dirname))
PathDict['Flds'].sort()

PathDict['Prtl']= filter(prtl_re.match, os.listdir(dirname))
PathDict['Prtl'].sort()

PathDict['Spect']= filter(s_re.match, os.listdir(dirname))
PathDict['Spect'].sort()

PathDict['Param']= filter(param_re.match, os.listdir(dirname))
PathDict['Param'].sort()


# A dictionary that allows use to see in what HDF5 file each key is stored.
# i.e. {'ui': 'Prtl', 'ue': 'Flds', etc...},

H5KeyDict = {}
for pkey in PathDict.keys():
    with h5py.File(os.path.join(dirname,PathDict[pkey][0]), 'r') as f:
    # Because dens is in both spect* files and flds* files,
        for h5key in f.keys():
            if h5key == 'dens' and pkey == 'Spect':
                H5KeyDict['spect_dens'] = pkey
            else:
                H5KeyDict[h5key] = pkey

# Get the shock location:
# First load the first field file to find the initial size of the
# box in the x direction

#        print os.path.join(self.dirname,self.PathDict['Flds'][0])

with h5py.File(os.path.join(dirname,PathDict['Flds'][0]), 'r') as f:
    nxf0 = f['by'][:].shape[1]
with h5py.File(os.path.join(dirname,PathDict['Param'][0]), 'r') as f:
    initial_time = f['time'][0]

# Load the final time step to find the shock's location at the end.
with h5py.File(os.path.join(dirname,PathDict['Flds'][-1]), 'r') as f:
    dens_arr =np.copy(f['dens'][0,:,:])

with h5py.File(os.path.join(dirname,PathDict['Param'][-1]), 'r') as f:
    # I use this file to get the final time, the istep, interval, and c_omp
    final_time = f['time'][0]
    istep = f['istep'][0]
    interval = f['interval'][0]
    c_omp = f['c_omp'][0]

# Find out where the shock is at the last time step.
jstart = min(10*c_omp/istep, nxf0)
# build the final x_axis of the plot

xaxis_final = np.arange(dens_arr.shape[1])/c_omp*istep
# Find the shock by seeing where the density is 1/2 of it's
# max value. First average the density in the y_direction


dens_half_max = max(dens_arr[dens_arr.shape[0]/2,jstart:])*.5
ishock_final = np.where(dens_arr[dens_arr.shape[0]/2,jstart:]>=dens_half_max)[0][-1]
xshock_final = xaxis_final[ishock_final]

print xshock_final
shock_speed = xshock_final/final_time


# Load the energy data of the Protons
ToLoad = {'Flds': [], 'Prtl': [], 'Param': [], 'Spect': []}
tmpList = ['c_omp', 'istep', 'gamma','xi','xe', 'bx','me', 'mi', 'ui', 'vi', 'wi','ue', 've', 'we']
for elm in tmpList:
    # find out what type of file the key is stored in
    ftype = H5KeyDict[elm]
    # add the key to the list of that file type
    ToLoad[ftype].append(elm)

    # Now iterate over each path key and create a datadictionary
    DataDict = {}
    for pkey in ToLoad.keys():
        tmplist = list(set(ToLoad[pkey])) # get rid of duplicate keys
        # Load the file
        with h5py.File(os.path.join(dirname,PathDict[pkey][-1]), 'r') as f:
            for elm in tmplist:
                # Load all the keys
                if elm == 'spect_dens':
                    DataDict[elm] = np.copy(f['dens'][:])
                else:
                    DataDict[elm] = np.copy(f[elm][:])

c_omp = DataDict['c_omp'][0]
me = DataDict['me'][0]
mi = DataDict['mi'][0]
print mi/me
istep = DataDict['istep'][0]
xmin = xshock_final-2000
#xmax = DataDict['bx'].shape[2]/c_omp*istep
xmax =5500
xi_values = DataDict['xi']/c_omp
ui = DataDict['ui']
vi = DataDict['vi']
wi = DataDict['wi']

E_i= np.log(np.sqrt(ui**2+vi**2+wi**2+1))


xe_values = DataDict['xe']/c_omp
ue = DataDict['ue']
ve = DataDict['ve']
we = DataDict['we']

E_e = np.log(np.sqrt(ue**2+ve**2+we**2+1)/(mi/me))

E_min = np.log(.5)
#E_max = min(max(E_e),max(E_i))
E_max = max(E_i)
print np.exp(E_max)
Hist_i, Eedges, xedges = np.histogram2d(E_i, xi_values,
        bins = [20, 50],
        range = [[E_min,E_max],[xmin,xmax]])

print len(Hist_i[:,0]),len(xedges),len(Hist_i[0])

Hist_e, Eedges, xedges = np.histogram2d(E_e, xe_values,
        bins = [20, 50],
        range = [[E_min,E_max],[xmin,xmax]])

print Hist_e
# Plot the integral from x to infinity of f(x,E)

# Choose 3 energy levels e=2.0 mi*c**2, 10 mi*c**2, 20 mi*c**2
# Find the histogram number that corresponds to these energies
E_list = [5.0, 10.0,16.0]


xval = np.empty(len(xedges)-1)
for i in range(len(xval)):
    xval[i] = (xedges[i]+xedges[i+1])/2
shock_ind = xval.searchsorted(xshock_final)
plt.style.use('ggplot')
for i in range(len(E_list)):
    E1_ind = Eedges.searchsorted(np.log(E_list[i]))

    E_val = np.exp((Eedges[E1_ind-1]+Eedges[E1_ind])/2)
    
    Fp = Hist_i[E1_ind - 1]
#    Fp *= max(Fp)**(-1)

    Fe = Hist_e[E1_ind - 1]
#    Fe *= max(Fe)**(-1)

#    Fp = cumtrapz(Hist_i[E1_ind - 1][::-1],-xval[::-1])[::-1]
#    Fp = cumtrapz(Hist_i[E1_ind - 1],xval)
#    Fp *= Fp[shock_ind]**(-1)

#    Fe = cumtrapz(Hist_e[E1_ind - 1][::-1],-xval[::-1])[::-1]
#    Fe = cumtrapz(Hist_e[E1_ind - 1],xval)
#    Fe *= Fe[shock_ind]**(-1)

    elabel = '%.2f' % E_val
    pline, = plt.semilogy(xval, Fp, label=r'$E = $'+elabel+' '+ r'$m_i c^2$')
#    plt.semilogy(xval, Fe, label=r'$E = $'+elabel+' '+ r'$m_i c^2$')
#    plt.semilogy(xval, Fe, color = pline.get_color(), linestyle ='--')
#    plt.semilogy(xval[0:-1], Fp, 'b'+ls_list[i], label=r'$E = $'+elabel+' '+ r'$m_i c^2$')
#    plt.semilogy(xval[0:-1], Fe, 'r'+ls_list[i])

plt.axvline(xshock_final, color = 'k', ls = ':', linewidth = 1)
plt.legend(loc='best')
plt.xlabel(r'$x\ [c/\omega_{pe}]$', size = 16)
#plt.ylabel(r'$\int_x^\infty{f(x^\prime,E)dx^\prime}$' +'[normalized to downstream max]')
#plt.ylabel(r'$f_p(x,E)\ \mathrm{[normalized]}$', size = 16)
plt.ylabel(r'$f_p(x,E)$', size = 16)
plt.show()

# Now calculate the diffusion coefficient in arbitrary units


'''

E_arr = np.empty(len(Eedges)-1)
De_arr = np.empty(len(Eedges)-1)
Dp_arr = np.empty(len(Eedges)-1)
for i in range(len(E_arr)):
    E_arr[i] = np.exp((Eedges[i]+Eedges[i+1])/2)
    # Calculate the diffusion coeffient
    De_arr[i] = np.trapz(Hist_e[i],xedges[0:-1])/Hist_e[i,0]
    Dp_arr[i] = np.trapz(Hist_i[i],xedges[0:-1])/Hist_i[i,0]
    print E_arr[i], De_arr[i], Dp_arr[i]

De_arr *= De_arr[0]**(-1)
#Dp_arr *= De_arr[0]**(-1)

#plt.loglog(E_arr, De_arr, label='Electrons')
plt.loglog(E_arr, Dp_arr, label='Protons')
plt.xlabel('Diffusion Coefficient [arb units]')
plt.xlabel('E '+r'$[m_i c^2]$')

plt.show()
'''
