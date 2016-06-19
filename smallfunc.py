# smallfunc.py
# ALS 2016/05/04

"""
a temporary repository of small functions 
"""
import os
from astropy.io import fits
from astropy.table import Table, join

def dir_RenormalizeImg_fits(dir_obj,filename='stamp-lOIII5008_I.fits',norm=1.e-15,update=False):
    """
    make 'stamp-lOIII5008_I_norm.fits' which is scaled up by 1.e15
    """

    filein=dir_obj+filename
    fileout=dir_obj+os.path.splitext(filename)[0]+'_norm.fits'

    if not os.path.isfile(fileout) or update:
        # read in 
        img=fits.getdata(filein)
        header=fits.getheader(filein)

        img_new=img/norm
        header['HISTORY']="Renormalized by a factor of 1 over "+str(norm)
        header['BUNIT']='%.1e'%norm+" "+(header['BUNIT'])

        prihdu = fits.PrimaryHDU(img_new, header=header)
        prihdu.writeto(fileout, clobber=True)
    else: 
        print "skipping dir_RenormalizeImg_fits as file exists"


def dir_delete_file(dir_obj, filename):
    """ delete file "filename" in dir_obj """
    if os.path.isfile(dir_obj+filename):
        print "deleting file "+filename
        os.remove(dir_obj+filename)
    else:
        print "skip deleting file "+filename


def dir_delete_files(dir_obj, filenames):
    """ delete file "filename" in dir_obj """
    for filename in filenames: 
        dir_delete_file(dir_obj, filename)


def joinmullaney(dir_batch,filename='measureimg.ecsv',filemullaney='/Users/aisun/Documents/Astro/Thesis/bbselection/SDSS/sample/Mullaney/catalogue/ALPAKA_extended.fits'):
    """
    join the table with mullaney table
    """

    # files to join
    tabin=Table.read(dir_batch+filename,format='ascii.ecsv')
    tabmullaney=Table.read(filemullaney,format='fits')
    tabmullaney.rename_column('SDSSNAME','OBJNAME')

    tabout=join(tabin,tabmullaney,keys=['OBJNAME'], join_type='left')

    # write out
    # tabout.write(dir_batch+filenameout+'.fits',format='fits',overwrite=True)

    tabout.write(dir_batch+os.path.splitext(filename)[0]+'_joinmullaney.ecsv',format='ascii.ecsv')
    tabout.write(dir_batch+os.path.splitext(filename)[0]+'_joinmullaney.csv',format='ascii.csv')
