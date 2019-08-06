import matplotlib as mpl
mpl.use('Tkagg')
#mpl.use('agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import numpy.ma as ma
from new_cnorms import PowerNormWithNeg, PowerNormFunc
import matplotlib.colors as mcolors
from scipy.integrate import simps, cumtrapz
import matplotlib.colors as mcolors
import matplotlib.gridspec as gridspec
from mpl_toolkits.axes_grid1 import make_axes_locatable, axes_size
import h5py
import os, sys
import re
import new_cmaps
import Tkinter, tkFileDialog
import matplotlib.animation as manimation
from scipy.stats import linregress
import matplotlib.patheffects as PathEffects
from matplotlib import transforms
from matplotlib.offsetbox import TextArea, VPacker, AnnotationBbox

#plt.style.use('ggplot')
mpl.rcParams['mathtext.fontset'] = 'stix'
mpl.rcParams['font.family'] = 'STIXGeneral'
mpl.rcParams['xtick.direction'] = 'out'
mpl.rcParams['ytick.direction'] = 'out'


#My own color maps
colors =  ['#D90000','#04756F','#FF8C00', '#988ED5', '#2E0927', '#0971B2']
e_color = '#0971B2'
i_color = '#D90000'
gradient =  np.linspace(0, 1, 256)# A way to make the colorbar display better
gradient = np.vstack((gradient, gradient))


ax_label_size = 30
ticklabel_size = 30

mpl.rcParams['xtick.labelsize'] = ticklabel_size
mpl.rcParams['ytick.labelsize'] = ticklabel_size


# Be sure to call only this with the output directory in the path
# create a bunch of regular expressions used to search for files
f_re = re.compile('flds.tot.*')
prtl_re = re.compile('prtl.tot.*')
s_re = re.compile('spect.*')
param_re = re.compile('param.*')
re_list = [f_re, prtl_re, s_re, param_re]
#root = Tkinter.Tk()



class simulation:
    # a placeholder to hold all the simulation data
    np.nan

#dir_names = ['../mi16/output', '../dely500/output','../mi160/output']#,'../SuperLarge10deg/output']
dir_names = ['../Gam1.5XXXL/output', '../Gam3XXL/output','../Gam5DS/output']#,'../SuperLarge10deg/output']
sim_names = [r'$\Gamma_0 = 1.5$',r'$\Gamma_0 = 3$', r'$\Gamma_0 =5 $', '']
sim_i_regions = [(-320,-40),(-640,-80), (-1010,-125),(-640,-80)]
sim_e_regions = [(-320, -40),(-640,-80),(-1010,-125),(-640,-80)]
#sim_time = [28, 27, 44]
#ylims=  [(0,79), (210,289),(0,79)]
ylims=  [(0,100), (0,100),(0,100)]
#ylims=  [(0,79), (490,569),(0,79)]
sim_time = [-1, -1, -1, -1]
ls = ['-', '-','-','--']
lcolor  = ['#FF8C00',  '#2E0927','#988ED5','#2E0927']


SimList = []
for i in range(len(dir_names)):
    sim = simulation()
    SimList.append(sim)
    sim.name = sim_names[i]
    sim.label = sim_names[i]
    sim.dr = os.path.join(os.curdir,dir_names[i])
    sim.i_region = sim_i_regions[i]
    sim.e_region = sim_e_regions[i]
    sim.ylims = ylims[i]
    sim.time_slice = sim_time[i]
    sim.ls = ls[i]
    sim.color = lcolor[i]
    sim.dens_norm = 1.0
    sim.dens_midpoint = 0
for sim in SimList:
    sim.PathDict = {}
    #fill all the paths
    sim.PathDict['Flds']= filter(f_re.match, os.listdir(sim.dr))
    sim.PathDict['Flds'].sort()

    sim.PathDict['Prtl']= filter(prtl_re.match, os.listdir(sim.dr))
    sim.PathDict['Prtl'].sort()

    sim.PathDict['Spect']= filter(s_re.match, os.listdir(sim.dr))
    sim.PathDict['Spect'].sort()

    sim.PathDict['Param']= filter(param_re.match, os.listdir(sim.dr))
    sim.PathDict['Param'].sort()


# A dictionary that allows use to see in what HDF5 file each key is stored.
# i.e. {'ui': 'Prtl', 'ue': 'Flds', etc...},

H5KeyDict = {}
for pkey in SimList[0].PathDict.keys():
    with h5py.File(os.path.join(SimList[0].dr,SimList[0].PathDict[pkey][0]), 'r') as f:
    # Because dens is in both spect* files and flds* files,
        for h5key in f.keys():
            if h5key == 'dens' and pkey == 'Spect':
                H5KeyDict['spect_dens'] = pkey
            else:
                H5KeyDict[h5key] = pkey
                H5KeyDict['time'] = 'Param'
# Get the shock speeds:
# First load the first field file to find the initial size of the
# box in the x direction

for sim in SimList:
    with h5py.File(os.path.join(sim.dr,sim.PathDict['Flds'][0]), 'r') as f:
        sim.nxf0 = f['by'][:].shape[1]
    with h5py.File(os.path.join(sim.dr,sim.PathDict['Param'][0]), 'r') as f:
        sim.initial_time = f['time'][0]

    # Load the final time step to find the shock's location at the end.
    with h5py.File(os.path.join(sim.dr,sim.PathDict['Flds'][-1]), 'r') as f:
        dens_arr =np.copy(f['dens'][0,:,:])[::-1,:]

    with h5py.File(os.path.join(sim.dr,sim.PathDict['Param'][-1]), 'r') as f:
        # I use this file to get the final time, the istep, interval, and c_omp
        final_time = f['time'][0]
        istep = f['istep'][0]
        c_omp = f['c_omp'][0]

    # Since we're in the piston frame, we have to account for the wall on the left
    istart = 0
    while dens_arr[dens_arr.shape[0]//2,istart]<1E-8:
        istart += 1

    # build the final x_axis of the plot


    jstart = int(min(10*c_omp/istep, sim.nxf0))
    xaxis_final = np.arange(dens_arr.shape[1]-istart)/c_omp*istep
    # Find the shock by seeing where the density is 1/2 of it's
    # max value. First average the density in the y_direction


    dens_half_max = max(dens_arr[dens_arr.shape[0]//2,jstart:])*.5
    ishock_final = np.where(dens_arr[dens_arr.shape[0]//2,jstart:]>=dens_half_max)[0][-1]-istart
    xshock_final = xaxis_final[ishock_final]
    sim.shock_speed = xshock_final/final_time


####
# Get the spectrum and data for t1 and t2
####
for sim in SimList:



    ToLoad = {'Flds': [], 'Prtl': [], 'Param': [], 'Spect': []}
    tmpList = ['c_omp', 'istep', 'dens','ppc0','gamma', 'ppc0','xsl','spece','specp', 'time', 'mi', 'me', 'gamma0', 'bz', 'by','bx','ey', 'ez','c', 'sigma', 'btheta']

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
        print(sim.dr)
        with h5py.File(os.path.join(sim.dr,sim.PathDict[pkey][sim.time_slice]), 'r') as f:
            for elm in tmplist:
                # Load all the keys
                if elm == 'spect_dens':
                    DataDict[elm] = f['dens'][:]
                elif elm =='gamma0':
                    DataDict[elm] = 1.5
                elif elm == 'spece':
                    DataDict[elm] = f['specerest'][:]
                elif elm == 'specp':
                    DataDict[elm] = f['specprest'][:]
                else:
                    DataDict[elm] = f[elm][:]
    dens_arr = DataDict['dens'][0,:,:]
    # Find out where the left wall is:
    sim.mass_ratio = DataDict['mi']/DataDict['me']
    istart = 0
    while dens_arr[dens_arr.shape[0]//2,istart]<1E-8:
        istart += 1
    sim.dens = dens_arr[:,istart:]/DataDict['ppc0']
    sim.p_shock_loc = DataDict['time'][0]*sim.shock_speed
    # All the data for this time step is now stored in the datadict
    # Calculate the current shock location:
    sim.c_omp = DataDict['c_omp'][0]
    sim.istep = DataDict['istep'][0]

    shock_loc = DataDict['time'][0]*sim.shock_speed+istart/sim.c_omp*sim.istep
    ### CALCULATE EPS B IN LEFT WALL FRAME
    bx_prime = DataDict['bx'][0,:,istart:]
    by_prime = 1.5*(DataDict['by'][0,:,istart:]+np.sqrt(1-1.5**-2)*DataDict['ez'][0,:,istart:])
    bz_prime = 1.5*(DataDict['bz'][0,:,istart:]-np.sqrt(1-1.5**-2)*DataDict['ey'][0,:,istart:])
    eps_B = (bx_prime**2+by_prime**2+bz_prime**2)/((1.5-1)*DataDict['ppc0']*.5*DataDict['c']**2*(DataDict['mi']+DataDict['me']))
    sim.eps_B = np.mean(eps_B, axis = 0)
    sim.x_array = np.arange(len(sim.eps_B))*sim.istep/sim.c_omp/np.sqrt(sim.mass_ratio)
    sim.eps_B_arr = np.log10(eps_B)
    #### Get all the data:

    c_omp = DataDict['c_omp'][0]
    istep = DataDict['istep'][0]
    xsl = DataDict['xsl']/c_omp
    gamma = DataDict['gamma']
    sim.LF = DataDict['gamma0']
    spece = DataDict['spece']
    specp = DataDict['specp']
    # In output.F90, spece (specp) is defined by the number of electons (ions)
    # divided by gamma in each logrithmic energy bin. So we multiply by gamma.

    for j in range(len(xsl)):
        spece[:,j] *= gamma
        specp[:,j] *= gamma
    dgamma = np.empty(len(gamma))
    delta=np.log10(gamma[-1]/gamma[0])/len(gamma)
    for j in range(len(dgamma)):
        dgamma[j]=gamma[j]*(10**delta-1.)

    # Select the x-range from which to take the spectra
    e_left_loc = shock_loc + sim.e_region[0]
    e_right_loc = shock_loc + sim.e_region[1]

    eL = xsl.searchsorted(e_left_loc)
    eR = xsl.searchsorted(e_right_loc, side='right')
    if eL == eR:
        eR += 1
    i_left_loc = shock_loc + sim.i_region[0]
    i_right_loc = shock_loc + sim.i_region[1]

    iL = xsl.searchsorted(i_left_loc)
    iR = xsl.searchsorted(i_right_loc, side='right')
    #    print iL, eL, iR, eR
    if iL == iR:
        iR += 1

    # total particles in each linear x bin
    norme = np.copy(xsl)
    normp = np.copy(xsl)

    for k in range(len(norme)):
        norme[k]=sum(spece[:,k])
        normp[k]=sum(specp[:,k])

    # energy distribution, f(E)=(dn/dE)/N
    fe=np.empty(len(gamma))
    fp=np.empty(len(gamma))


    for k in range(len(fe)):
        fe[k]=sum(spece[k][eL:eR])/(sum(norme[eL:eR])*dgamma[k])
        fp[k]=sum(specp[k][iL:iR])/(sum(normp[iL:iR])*dgamma[k])


    fe[fe<=0]=1E-100
    fp[fp<=0]=1E-100

    # MASK OUT THE ZEROS

    #  NOTE: gamma ---> gamma-1 ***
    edist = gamma*fe
    pdist = gamma*fp

    masked_edist = np.ma.masked_where(edist < 1E-20, edist)
    masked_pdist = np.ma.masked_where(pdist < 1E-20, pdist)

    momentum=np.sqrt((gamma+1)**2-1.)
    femom=fe/(4*np.pi*momentum)/(gamma+1)
    momedist=femom*momentum**4
    fpmom=fp/(4*np.pi*momentum)/(gamma+1)
    mompdist=fpmom*momentum**4

    masked_momedist = np.ma.masked_where(edist < 1E-40, momedist)
    masked_mompdist = np.ma.masked_where(pdist < 1E-40, mompdist)

    sim.exdata = momentum*DataDict['me'][0]/DataDict['mi'][0]/np.sqrt(DataDict['gamma0']**2-1)
    sim.eydata = masked_momedist/sim.mass_ratio/np.sqrt(sim.LF**2-1)
    sim.ixdata = momentum/np.sqrt(DataDict['gamma0']**2-1)
    sim.iydata = masked_mompdist/np.sqrt(sim.LF**2-1)





#####
#
# We've now loaded all of the data. Let's make the 2 spectra:
#
#####

"""
# Make the figure
fig = plt.figure(figsize = (9,11))
gsArgs = {'left':0.18, 'right':0.95, 'top':.95, 'bottom':0.1, 'wspace':0.2, 'hspace':0.0}
MainGs = gridspec.GridSpec(100,100)
MainGs.update(**gsArgs)

i_ax = fig.add_subplot(MainGs[2:49,:])
e_ax = fig.add_subplot(MainGs[51:98,:])


for sim in SimList:
    #Plot the eps_e and eps_p lines
    sim.iplot, = i_ax.loglog(sim.ixdata, sim.iydata, ls = sim.ls, linewidth = 1.5, color = sim.color, label = sim.label)
    sim.eplot, = e_ax.loglog(sim.exdata, sim.eydata, ls = sim.ls, linewidth = 1.5, color = sim.color, label = sim.label)


i_ax.text(.015,.02,r'Ions',size = ax_label_size)
e_ax.text(.015,.02,r'Electrons',size = ax_label_size)


ax_list = [i_ax, e_ax]

#print [SimList[1].eplot, SimList[-1].eplot]
#l1 = i_ax.legend([SimList[1].eplot, SimList[-1].eplot],[r'$t \approx1330\ (\gamma_0\omega_{pi})^{-1}$', r'$t =3140\ (\gamma_0\omega_{pi})^{-1}$'], loc =8, fontsize = 18)
'''l1 = i_ax.legend([SimList[1].eplot],[r'$t \approx1330\ (\gamma_0\omega_{pi})^{-1}$'],handlelength=0, handletextpad=0, loc =8, fontsize = ax_label_size)
l1.get_frame().set_linewidth(0)
for item in l1.legendHandles:
        item.set_visible(False)'''
leg = ax_list[0].legend(handlelength=0, handletextpad=0, fontsize = ax_label_size)
leg.get_frame().set_linewidth(0)

for item in leg.legendHandles:
    item.set_visible(False)
for color,text in zip(lcolor,leg.get_texts()):
    text.set_color(color)

for ax in ax_list:
    # MAKE THE LEGEND OMITING THE 4RD SIM

    ax.tick_params(axis='x',
                     which = 'both', # bothe major and minor ticks
                      top = 'off') # turn off top ticks

    ax.tick_params(axis='y',          # changes apply to the y-axis
                   which='major',      # both major and minor ticks are affected
                   left='on',      # ticks along the bottom edge are off
                   right='off')         # ticks along the top edge are off)

    ax.tick_params(axis='y',          # changes apply to the y-axis
                   which='minor',      # both major and minor ticks are affected
                   left='off',      # ticks along the bottom edge are off
                   right='off')         # ticks along the top edge are off


    ax.set_ylabel(r'$p^4 f(p)/(\gamma_0\beta_0m_i c)$', size = ax_label_size)

    ax.set_yticks([1E-6, 1E-4, 1E-2])

    ax.set_ylim(8E-7,2E-1)
    ax.set_xlim(1E-2,6E1)

#i_ax.add_artist(l1)

#i_ax.set_title(r'$\omega_{pi}t/\gamma_0 \approx1330$', size = ax_label_size, loc = 'right')
e_ax.set_xlabel(r'$p/(\gamma_0\beta_0m_i c)$', size = ax_label_size)
i_ax.set_xticklabels([])
i_ax.tick_params(axis='x',
                 which = 'both', # bothe major and minor ticks
                 bottom = 'off') # turn off top ticks


plt.show()
"""
### NOW DO THE DENSITY:

gsArgs = {'left':0.1, 'right':0.9, 'top':.95, 'bottom':0.03, 'wspace':0.2, 'hspace':0.1}
MainGS_starting = 40
MainGS_spacing = 40
MainGS_ending = 940

fig = plt.figure(figsize = (11,11))

MainGs = gridspec.GridSpec(1000,1)
graph_extent = int((MainGS_ending - MainGS_starting - 2*MainGS_spacing)/3.)
curpos = MainGS_starting
MainGs.update(**gsArgs)


for i in range(len(SimList)):
    sim = SimList[i]
    print(sim.name)
    # Create a gridspec to handle spacing better

    ax = fig.add_subplot(MainGs[curpos:curpos+graph_extent,:])
    ax.grid(False)
#    if i == 0:
#        ax.set_title(r'$\omega_{pi}t/\gamma_0 \approx1330$', size = ax_label_size, loc = 'right')
    curpos += graph_extent + MainGS_spacing

    im = ax.imshow(sim.dens, norm = PowerNormWithNeg(sim.dens_norm,div_cmap = False, midpoint = sim.dens_midpoint), origin = 'lower')

    #if i == 0:
    #    ax.set_title(r'$t \approx 1330\ (\gamma_0\omega_{pi})^{-1}$', size = ax_label_size)

    ax.set_ylabel(r'$y \ [c/\omega_{pi}]$', size = ax_label_size)
    im.set_cmap(new_cmaps.cmaps['temperature'])
    im.set_extent([-sim.p_shock_loc/np.sqrt(sim.mass_ratio), (sim.dens.shape[1]*sim.istep/sim.c_omp-sim.p_shock_loc)/np.sqrt(sim.mass_ratio), 0, sim.dens.shape[0]*sim.istep/sim.c_omp/np.sqrt(sim.mass_ratio)])
    ax.set_xlim(-250,350)
    annotate_kwargs = {'horizontalalignment': 'center',
                   'verticalalignment': 'top',
                   'size' : 30,
                       #'path_effects' : [PathEffects.withStroke(linewidth=1.5,foreground="k")],
                    'xycoords': 'axes fraction',
                    'color' : 'k'}
    bbox_props = dict(fc="k", alpha=0.0)
    ax.annotate(sim.name,
                  xy = (0.1,.92),
                bbox = bbox_props,
                  **annotate_kwargs)


    im.norm.vmin = 0
    im.norm.vmax = 5
    #ax.locator_params(axis='y',nbins=4)
    ax.set_ylim(sim.ylims)
    #ax.set_yticks([sim.ylims[0],sim.ylims[0]+20,sim.ylims[0]+40,sim.ylims[0]+60])

    ax.tick_params(labelsize = ticklabel_size)#, color=tick_color)
    ax.tick_params(axis ='y', which='both', right='off')
    ax.tick_params(axis ='x', which='both', top='off')
    if i != 2:
        ax.tick_params(axis ='x', which='both', bottom='off')
        ax.set_xticklabels([])
    divider = make_axes_locatable(ax)
    cax = divider.append_axes("right", size="3%", pad=0.1)


    # Cbar is vertical
    cbar = cax.imshow(np.transpose(gradient)[::-1], aspect='auto',
                                            cmap=new_cmaps.cmaps['temperature'])

    cax.tick_params(axis='x',
                        which = 'both', # bothe major and minor ticks
                        top = 'off', # turn off top ticks
                        bottom = 'off', # turn off bottom ticks
                        labelbottom = 'off') # turn off bottom ticks
    cax.grid(False)

    cax.tick_params(axis='y',          # changes apply to the y-axis
                        which='both',      # both major and minor ticks are affected
                        left='off',      # ticks along the bottom edge are off
                        right='on',         # ticks along the top edge are off
                        labelleft='off',
                        labelright = 'on',
                        labelsize = ticklabel_size)


    clim = np.copy(im.get_clim())
    cbar.set_extent([0,1,clim[0],clim[1]])

    # re-create the gradient with the data values
    # First make a colorbar in the negative region that is linear in the pow_space
    data_range = np.linspace(clim[0],clim[1],512)

    cbardata = PowerNormFunc(data_range, vmin = data_range[0], vmax = data_range[-1], gamma = sim.dens_norm, div_cmap =False,midpoint = sim.dens_midpoint)
    cbardata = np.vstack((cbardata,cbardata))
    cbar.set_data(np.transpose(cbardata)[::-1])

    cax.set_ylim(clim[0],clim[1])
    #cax.set_yticks([0,1,5])


    cax.set_ylabel(r'$n/n_0$', size = ax_label_size, rotation = -90, labelpad = 25)
    cax.yaxis.set_label_position("right")
#fig.suptitle(r'$\theta_B = 0,\quad \omega_{pi}t \approx 1750$', size = ax_label_size)
fig.suptitle(r'$\theta_B = 0,\quad \sigma = 0.01, \quad m_i/m_e = 64$', size = ax_label_size)
ax.set_xlabel(r'$x-x_s\ [c/\omega_{pi}]$', size = ax_label_size)
plt.savefig('densVLF.pdf', dpi = 200)
plt.show()
"""
### NOW DO THE DENSITY:

gsArgs = {'left':0.1, 'right':0.9, 'top':.95, 'bottom':0.03, 'wspace':0.2, 'hspace':0.1}
MainGS_starting = 40
MainGS_spacing = 40
MainGS_ending = 940

fig = plt.figure(figsize = (12,12))

MainGs = gridspec.GridSpec(1000,1)
graph_extent = int((MainGS_ending - MainGS_starting - 2*MainGS_spacing)/3.)
curpos = MainGS_starting
MainGs.update(**gsArgs)


for i in range(len(SimList)):
    sim = SimList[i]
    print(sim.name)
    # Create a gridspec to handle spacing better

    ax = fig.add_subplot(MainGs[curpos:curpos+graph_extent,:])
    ax.grid(False)
#    if i == 0:
#        ax.set_title(r'$\omega_{pi}t/\gamma_0 \approx1330$', size = ax_label_size, loc = 'right')
    curpos += graph_extent + MainGS_spacing

    im = ax.imshow(sim.eps_B_arr,  origin = 'lower')

    #if i == 0:
    #    ax.set_title(r'$t \approx 1330\ (\gamma_0\omega_{pi})^{-1}$', size = ax_label_size)

    ax.set_ylabel(r'$y \ [c/\omega_{pi}]$', size = ax_label_size)
    im.set_cmap(new_cmaps.cmaps['inferno'])
    im.set_extent([0, sim.eps_B_arr.shape[1]*sim.istep/sim.c_omp/np.sqrt(sim.mass_ratio), 0, sim.eps_B_arr.shape[0]*sim.istep/sim.c_omp/np.sqrt(sim.mass_ratio)])
    ax.set_xlim(50,300)
    annotate_kwargs = {'horizontalalignment': 'center',
                   'verticalalignment': 'top',
                   'size' : 30,
                       #'path_effects' : [PathEffects.withStroke(linewidth=1.5,foreground="k")],
                    'xycoords': 'axes fraction',
                    'color' : 'k'}
    bbox_props = dict(fc="k", alpha=0.0)
    ax.annotate(sim.name,
                  xy = (0.14,.92),
                bbox = bbox_props,
                  **annotate_kwargs)


    im.norm.vmin = -2.2
    im.norm.vmax = 0.2
    #ax.locator_params(axis='y',nbins=4)
    ax.set_ylim(sim.ylims)
    ax.set_yticks([sim.ylims[0],sim.ylims[0]+20,sim.ylims[0]+40,sim.ylims[0]+60])
    ax.set_yticklabels([0,20,40,60])

    ax.tick_params(labelsize = ticklabel_size)#, color=tick_color)
    ax.tick_params(axis ='y', which='both', right='off')
    ax.tick_params(axis ='x', which='both', top='off')
    if i != 2:
        ax.tick_params(axis ='x', which='both', bottom='off')
        ax.set_xticklabels([])
    divider = make_axes_locatable(ax)
    cax = divider.append_axes("right", size="3%", pad=0.1)


    # Cbar is vertical
    cbar = cax.imshow(np.transpose(gradient)[::-1], aspect='auto',
                                            cmap=new_cmaps.cmaps['temperature'])

    cax.tick_params(axis='x',
                        which = 'both', # bothe major and minor ticks
                        top = 'off', # turn off top ticks
                        bottom = 'off', # turn off bottom ticks
                        labelbottom = 'off') # turn off bottom ticks
    cax.grid(False)

    cax.tick_params(axis='y',          # changes apply to the y-axis
                        which='both',      # both major and minor ticks are affected
                        left='off',      # ticks along the bottom edge are off
                        right='on',         # ticks along the top edge are off
                        labelleft='off',
                        labelright = 'on',
                        labelsize = ticklabel_size)


    clim = np.copy(im.get_clim())
    cbar.set_extent([0,1,clim[0],clim[1]])

    # re-create the gradient with the data values
    # First make a colorbar in the negative region that is linear in the pow_space
    data_range = np.linspace(clim[0],clim[1],512)

    cbardata = PowerNormFunc(data_range, vmin = data_range[0], vmax = data_range[-1], gamma = sim.dens_norm, div_cmap =False,midpoint = sim.dens_midpoint)
    cbardata = np.vstack((cbardata,cbardata))
    cbar.set_data(np.transpose(cbardata)[::-1])

    cax.set_ylim(clim[0],clim[1])
    cax.set_yticks([0,6,12])


    cax.set_ylabel(r'$n/n_0$', size = ax_label_size, rotation = -90, labelpad = 25)
    cax.yaxis.set_label_position("right")
ax.set_xlabel(r'$x\ [c/\omega_{pi}]$', size = ax_label_size)
#plt.savefig('AppendixBdens.pdf', dpi = 200)
plt.show()

ax_label_size = 24
ticklabel_size = 20


fig = plt.figure(figsize = (7,4))
gsArgs = {'left':0.12, 'right':0.95, 'top':.95, 'bottom':0.1, 'wspace':0.2, 'hspace':0.0}
MainGs = gridspec.GridSpec(1000,1000)
MainGs.update(**gsArgs)
eps_ax = fig.add_subplot(MainGs[35:900,50:990]) # axes to plot the downstream spectra


#plt.show()


for sim in SimList:
    eps_ax.semilogy(sim.x_array, sim.eps_B,ls = sim.ls, linewidth = 1.5, color = sim.color, label = sim.label)

eps_ax.set_xlabel(r'$x\ [c/\omega_{pi}]$', size = ax_label_size)
eps_ax.set_ylabel(r'$\langle \epsilon_{B} \rangle$', size = ax_label_size)
eps_ax.set_xlim(50, 300)
eps_ax.set_ylim(None,1.5)
eps_ax.tick_params(labelsize = ticklabel_size)#, color=tick_color)
eps_ax.tick_params(axis ='y', which='both', right='off')
eps_ax.tick_params(axis ='x', which='both', top='off')

leg = eps_ax.legend(handlelength=0, handletextpad=0,fontsize = ax_label_size-1)
leg.get_frame().set_linewidth(0)
for item in leg.legendHandles:
    item.set_visible(False)
for color,text in zip(lcolor,leg.get_texts()):
    text.set_color(color)
#eps_ax.set_title(r'$\omega_{pi}t/\gamma_0 \approx1330$', size = ax_label_size, loc = 'right')
plt.savefig('AppendixB_epsB.pdf')
plt.show()
"""
