
import sys
from netCDF4 import Dataset
from wrf2kmz import *
from slvp import compute_seaprs
from relhum import relative_humidity

from matplotlib import colors,cm

#clist=['white','#CCFF00','#66FF00',]
bounds=[0,1,5,10,25,50,100,250,500,1000]
mbound=[0,1,2, 3, 4, 5,  6,  7,  8,9,10]

basecmap=cm.jet
clist=[]
N=len(bounds)-1
for i in np.linspace(0,basecmap.N,N):
    clist.append(basecmap(float(i)/basecmap.N)[:-1])

cmap=colors.ListedColormap(clist)
norm=colors.BoundaryNorm(bounds,cmap.N)
cbarargs={'boundaries':bounds,'ticks':bounds,'spacing':'uniform'}

mlist=[]
N=len(mbound)-1
for i in np.linspace(0,basecmap.N,N):
    mlist.append(basecmap(float(i)/basecmap.N)[:-1])

mmap=colors.ListedColormap(mlist)
mnorm=colors.BoundaryNorm(mbound,mmap.N)
mbarargs={'boundaries':mbound,'ticks':mbound,'spacing':'uniform'}

class LightningRaster(ZeroMaskedRaster):
    pass

class GCLightningRaster(LightningRaster):
    def __init__(self,*args,**kwargs):
        kwargs['derivedVar']=True
        super(GCLightningRaster,self).__init__(*args,**kwargs)

    def _readVarRaw(self,varname,istep,*args,**kwargs):
        a=self._file.variables['LPOS'][istep,...]
        b=self._file.variables['LNEG'][istep,...]
        a=a+b
        return a.squeeze()

    def getDescription(self):
        return 'GC'

class TotLightningRaster(LightningRaster):
    def __init__(self,*args,**kwargs):
        kwargs['derivedVar']=True
        super(TotLightningRaster,self).__init__(*args,**kwargs)

    def _readVarRaw(self,varname,istep,*args,**kwargs):
        a=self._file.variables['LPOS'][istep,...]
        b=self._file.variables['LNEG'][istep,...]
        c=self._file.variables['LNEU'][istep,...]
        a=a+b+c
        return a.squeeze()

    def getDescription(self):
        return 'Total Ground Lightning Density'

class WindSpeedRaster(ZeroMaskedRaster):
    def __init__(self,*args,**kwargs):
        kwargs['derivedVar']=True
        super(WindSpeedRaster,self).__init__(*args,**kwargs)

    def _readVarRaw(self,varname,istep,*args,**kwargs):
        if istep == None:
            istep=0
        a=self._file.variables['U'][istep,0,...].squeeze()
        a=.5*(a[:,1:]+a[:,:-1])
        b=self._file.variables['V'][istep,0,...].squeeze()
        b=.5*(b[1:,:]+b[:-1,:])
        a=(a**2.+b**2.)**.5
        return a.squeeze()

    def getDescription(self):
        return 'Wind Speed'

class SeaPressureRaster(ZeroMaskedRaster):
    def __init__(self,*args,**kwargs):
        kwargs['derivedVar']=True
        super(SeaPressureRaster,self).__init__(*args,**kwargs)

    def _readVarRaw(self,varname,istep,*args,**kwargs):
        if istep == None:
            istep=0
        p=self._file.variables['P'][istep,...]
        pb=self._file.variables['PB'][istep,...]
        ph=self._file.variables['PH'][istep,...]
        phb=self._file.variables['PHB'][istep,...]
        t=self._file.variables['T'][istep,...]
        qv=self._file.variables['QVAPOR'][istep,...]

        return compute_seaprs(p,pb,ph,phb,t,qv)

    def getDescription(self):
        return 'Sea level pressure'

class RelHumRaster(ZeroMaskedRaster):
    def __init__(self,*args,**kwargs):
        kwargs['derivedVar']=True
        super(RelHumRaster,self).__init__(*args,**kwargs)

    def _readVarRaw(self,varname,istep,*args,**kwargs):
        if istep == None:
            istep=0
        t2=self._file.variables['T2'][istep,...]
        q2=self._file.variables['Q2'][istep,...]
        psfc=self._file.variables['PSFC'][istep,...]
        return relative_humidity(t2,q2,psfc)

def test():
    subdomain={'centerlon':-80.874129,
               'centerlat':42.181647,
               'dx':500000,
               'dy':500000}
    f=Dataset(sys.argv[1],'r')
    lpos=LightningRaster(f,f.variables['LPOS'],name='LPOS',accum=True,accumsumhours=3,subdomain=subdomain)
    lneg=LightningRaster(f,f.variables['LNEG'],name='LNEG',accum=True,accumsumhours=3,subdomain=subdomain)
    
    n=ncKML()
    n.setViewFromRaster(lpos)
    n.groundOverlayFromRaster(lpos)
    n.groundOverlayFromRaster(lneg)
    n.savekmz('lightning.kmz')

def main():
    from optparse import OptionParser
    usage='''usage: %prog [-s centerlon centerlat width height] wrfout
centerlon,centerlat: center of subdomain in degrees lat/lon
width,height:        width/height of the subdomain in meters

Creates lightning.kmz from the contents of wrfout.
'''
    #parser=OptionParser(usage=usage)
    #parser.add_option('-s',action='store_true',dest='subdomain',help='Output only a subdomain',
    #                  default=False)
    
    #(opts,args) = parser.parse_args()
    
    class tmp(object):
        pass

    opts=tmp()
    opts.subdomain=False
    args=sys.argv[1:]
    if '-s' in args:
        args.remove('-s')
        opts.subdomain=True

    subdomain=None
    if opts.subdomain:
        if len(args) != 5:
            print >> sys.stderr, 'Invalid number of arguments for subdomain (-s)'
            sys.exit(1)
        subdomain = {'centerlon':float(args[0]),
                     'centerlat':float(args[1]),
                     'dx':float(args[2]),
                     'dy':float(args[3])}
        file=args[4]
    else:
        file=args[0]

    commonargs={'subdomain':subdomain,
                'cmap':cmap,
                'norm':norm,
                'colorbarargs':cbarargs,
                'interp':'sinc'}
                #'dpi':1200}
    mcommonargs={'subdomain':subdomain,
                'cmap':mmap,
                'norm':mnorm,
                'colorbarargs':mbarargs,
                'interp':'sinc'}

    f=Dataset(file,'r')
    lpos=LightningRaster(f,f.variables['LPOS'],name='+GC',accum=True,accumsumhours=3,**mcommonargs)
    lneg=LightningRaster(f,f.variables['LNEG'],name='-GC',accum=True,accumsumhours=3,**commonargs)
    lneu=LightningRaster(f,f.variables['LNEU'],name='IC',accum=True,accumsumhours=None,**commonargs)
    lgc=GCLightningRaster(f,f.variables['LPOS'],name='GC',accum=True,accumsumhours=3,**commonargs)
    ltot=TotLightningRaster(f,f.variables['LPOS'],name='Total',accum=True,accumsumhours=3,**commonargs)
    
    rain=ZeroMaskedRaster(f,f.variables['RAINNC'],name='RAINNC',accum=True,accumsumhours=3,subdomain=subdomain,
                          interp='sinc')
    snow=ZeroMaskedRaster(f,f.variables['SNOWH'],name='SNOWH',accum=True,accumsumhours=3,subdomain=subdomain,
                          interp='sinc')

    wind=Vector2Raster(f,f.variables['U'],f.variables['V'],name='Wind',usebarbs=True,barbslength=3,
                       barbswidth=.5,displayDescription='Wind',subdomain=subdomain)
    winds=WindSpeedRaster(f,f.variables['U'],name='Wind Speed',subdomain=subdomain,interp='sinc')
    slvp=SeaPressureRaster(f,f.variables['P'],name='Sea Level Pressure',subdomain=subdomain,interp='sinc')
    relhum=RelHumRaster(f,f.variables['Q2'],name='Relative Humidity',subdomain=subdomain,interp='sinc')


    n=ncKML()
    n.setViewFromRaster(lpos)
    n.groundOverlayFromRaster(lpos)
    n.groundOverlayFromRaster(lneg)
    n.groundOverlayFromRaster(lneu)
    n.groundOverlayFromRaster(lgc)
    n.groundOverlayFromRaster(ltot)
    n.groundOverlayFromRaster(rain)
    n.groundOverlayFromRaster(snow)
    n.groundOverlayFromRaster(wind)
    n.groundOverlayFromRaster(winds)
    n.groundOverlayFromRaster(slvp)
    n.groundOverlayFromRaster(relhum)
    n.savekmz('lightning.kmz')

if __name__ == '__main__':
    main()
