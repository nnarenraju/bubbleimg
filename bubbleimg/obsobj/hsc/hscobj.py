# hscobj.py
# ALS 2017/05/11

"""
define class hscObj, which can check whether there is such an object and load xid 
"""
import numpy as np
import sys 
import os
from astropy.coordinates import SkyCoord
import astropy.table as at
from astropy.io import fits
import astropy.io.ascii
import astropy.units as u

from hscsspquery import hscSspQuery
from ..plainobj import plainObj

class hscObj(plainObj):
	def __init__(self, **kwargs):
		"""
		load sdss.xid write files 'hsc_xid.csv' automatically.
		if successful, sdss.status == True

		Instruction
		-----------
		One has to set HSC_SSP STARs account username and password as environmental variable to access hsc data
		  $ export HSC_SSP_CAS_USERNAME
		  $ read -s HSC_SSP_CAS_USERNAME
		  $ export HSC_SSP_CAS_PASSWORD
		  $ read -s HSC_SSP_CAS_PASSWORD


		Params
		------
		ra (float)
		dec (float)
		/either
			dir_obj (string)
		/or 
			dir_parent (string): attr dir_obj is set to dir_parent+'SDSSJXXXX+XXXX/'
		
		rerun = 's16a_wide' (string): which data base to search for
		release_version = 'dr1' (string): which data base to search for

		Attributes
		----------
		ra (float)
		dec (float)
		dir_obj (string)
		rerun (string): e.g., 's16a_wide'
		release_version (string): e.g., 'dr1'
		status (whether the xid and photoboj query were successful)

		optional attr (if querry successful):
			xid
		
		"""
		super(self.__class__, self).__init__(**kwargs)
		self.rerun = kwargs.pop('rerun', 's16a_wide')
		self.release_version = kwargs.pop('release_version', 'dr1')

		self.fp_xid = self.dir_obj+'hsc_xid.csv'
		self.fp_photoobj = self.dir_obj+'hsc_photoobj.csv'

		self.status = self.load_xid()


	def load_photoobj(self, columns=[], bands = [], tabname='main', hsctable='forced', all_columns=False):
		"""
		load hsc photometry table either locally or remotely and add it as attribute self.photoobj

		Params
		------

		[0] self 

		[1] Columns: Either contains the columns when called upon or has a default choice of columns if found NULL
		Enter the required columns:
			Refer Schema Browser -> "https://hscdata.mtk.nao.ac.jp/schema_browser2/"
			Note: STARs account required
	
		[2] Bands: Either contains the bands req. when called upon or has a default choice of bands if found NULL
		Available bands: g, r, i, z and y
	
		[3] hsctable='forced': which hsctable to load from remote hsc database

		[4] all_columns=True: Generates SQL code such that all the fields from the table are included

		Return
		------
		status (bool): if true then the loading was successful, false if not
		
		"""
		if self.status == True: 

			photoobj = self._get_photoobj(columns=columns, bands=bands, hsctable=hsctable, all_columns=all_columns, rerun=self.rerun, release_version=self.release_version)

			if photoobj is not None:
				self.photoobj = photoobj
				return True
			else:
				return False

		else: 
			print("[hscobj] skip loading photoobj as xid is not successfully created")
			return False



	def _get_photoobj(self, columns=[], bands=[], all_columns=False, hsctable='forced', rerun='s16a_wide', release_version='dr1'):
		"""
		return photoobj.
		Read photoobj locally if self.dir_obj+'hsc_xid.csv' exist. Otherwise query. 

		Params
		------
		columns=[]
		bands=[]
		all_columns=False
		hsctable='forced'
		rerun='s16a_wide'
		release_version='dr1'

		Returns:
		------
		photobj: table, or None if failed

		Write Output: (optional)
		------
		self.dir_obj+'xid.csv'
		"""

		fn = self.fp_photoobj

		if not hasattr(self, 'xid'):
			xidstatus = self.load_xid()
		else:
			xidstatus = True

		if xidstatus:
			if os.path.isfile(fn):
				print "[hscobj] reading hsc_photoobj locally"
				photoobj = at.Table.read(fn, format='ascii.csv',comment='#')
				return photoobj

			else:
				print "[hscobj] querying photoobj from HSC"
				object_id = self.xid['object_id'][0]
				sql = _get_photoobj_sql(object_id=object_id, columns=columns, bands=bands, all_columns=all_columns, rerun=rerun)
				hscSspQuery(sql, filename_out=fn, release_version=release_version)

				if os.path.isfile(fn) and (os.stat(fn).st_size > 0):
					photoobj = at.Table.read(fn, format='ascii.csv', comment='#')
					return photoobj
				else: 
					print("[hscobj] querying photoobj from HSC failed")
					return None
		else:
			return None


	def load_xid(self):
		"""
		load xid either locally or remotely and add it as attribute self.xid

		Params
		------
		self 

		Return
		------
		status (bool): if true then the loading was successful, false if not
		"""
		xid = self._get_xid(rerun=self.rerun, release_version=self.release_version)

		if xid is not None:
			self.xid = xid
			for col in xid.colnames: 
				# setting xid attributes 
				setattr(self, col, xid[col][0])
			return True
		else: 
			return False


	def _get_xid(self, rerun='s16a_wide', release_version='dr1'):
		"""
		return xid.
		Read xid locally if self.dir_obj+'hsc_xid.csv' exist. Otherwise query. 

		Parameters
		------
		self: obj
			contains: 
			self.dir_obj, self.ra, self.dec

		Returns:
		------
		xid: table, or None if failed

		Write Output: (optional)
		------
		self.dir_obj+'xid.csv'
		"""

		fn = self.fp_xid

		if os.path.isfile(fn): # retrieve xid locally
			print "[hscObj] reading xid locally"
		else: # download xid from sdss
			print "[hscObj] querying xid from server"
			self.make_dir_obj()	
			sql = _get_xid_sql(ra=self.ra, dec=self.dec, rerun=rerun)
			hscSspQuery(sql, filename_out=fn, release_version=release_version)

		if os.path.isfile(fn): # retrieve xid locally
			if os.stat(fn).st_size > 0:
				xid = at.Table.read(fn, format='ascii.csv', comment='#')

				if len(xid)>=1: 
					if len(xid)>1:
						xid = self._resolve_multiple_sources(xid)

					# sanity check 1
					diffra = (round(xid['ra'], 2) != round(self.ra, 2))
					diffdec = (round(xid['dec'], 2) != round(self.dec, 2))
					if diffra or diffdec:
						raise ValueError("local hsc_xid inconsistent with object")
					# sanity check 2
					if (len(xid) != 1) or (xid['detect_is_primary'][0] !='t'):
						raise Exception("[hscObj] something wrong with xid") 

					return xid

				elif len(xid)<1:
					print "[hscObj] no object found"				
					os.remove(fn)
					return None

			else: 
				print "[hscObj] no object found"
				os.remove(fn)
				return None
		else: 
			print "[hscObj] query failed"
			return None


	def _resolve_multiple_sources(self, xid):
		""" return the xid with only the row that is closest to self.ra, dec"""
		print "[hscObj] multiple primary objects found, choose the closest one"
		c = SkyCoord(self.ra, self.dec, 'icrs', unit='deg')
		crows = [SkyCoord(row['ra'], row['dec'], 'icrs', unit='deg') for row in xid]
		
		a = np.array([c.separation(crow).value for crow in crows])
		xid = at.Table(xid[np.argmin(a)])
		return xid


def _get_xid_sql(ra, dec, radius=2, rerun='s16a_wide'):
	"""
	construct sql query 

	Params
	------
	ra (float): ra in deg decimal
	dec (float): dec in deg decimal
	radius (float): search radius in arcsec
	rerun (string): which rerun to use

	"""

	path=os.path.dirname(sys.modules[__name__].__file__)
	if path == '': 
		path ='.'
	localpath = path+'/'

	fn = localpath+'template.sql'

	with open(fn, 'r') as f:
		sql_template=f.read()
	sql = sql_template.format(rerun=rerun, ra=str(ra), dec=str(dec), radius=str(radius))

	return sql


def _get_photoobj_sql(object_id, columns=[], bands=[], tabname='main', all_columns=False, rerun='s16a_wide', save_sql=False, fn_sql='hsc_sql.txt'):
	"""
	construct sql query 

	Params
	------
	object_id
	columns=[]
	bands=[]
	tabname='main'
	all_columns=False
	rerun='s16a_wide'
	save_sql=False
		if True, save the output sql script to fn_sql
	fn_sql='hsc_sql.txt'

	Return
	------
	sql (str)
	"""

	path = os.path.dirname(sys.modules[__name__].__file__)
	if path == '': 
		path ='.'
	localpath = path+'/'

	fn = localpath+'photoobj_template.sql'
	sqlcolumns = _get_photoobj_sql_columns(columns=columns, bands=bands, tabname=tabname, all_columns=all_columns)

	with open(fn, 'r') as f:
		sql_template=f.read()
	sql = sql_template.format(rerun=rerun, object_id=object_id, sqlcolumns=sqlcolumns)

	if save_sql:
		with open(fn_sql, "w") as text_file:
			text_file.write(sql)

	return sql


def _get_photoobj_sql_columns(columns=[], bands=[], tabname='main', all_columns=False):
	
	"""
	Creates SQL commands for required columns in the form of a single string array
	
	Params
	------
	columns=[]
	bands=[]
	tabname='main'
	all_columns=False


	Return
	------
	Returns a string containing the SQL commands for data acquisition
	
	"""

	default = 'main.object_id,main.ra, main.dec,main.patch_id,main.tract,main.patch,main.patch_s,\
				main.parent_id,main.deblend_nchild,main.detect_is_patch_inner,main.detect_is_tract_inner,\
				main.detect_is_primary,'

	if all_columns:
		return '*'

	else:
		sqlcolumns = ""
		if len(columns) == 0:
			columns = ['mag_kron', 'mag_kron_err', 'flux_kron_flags', 'flux_kron_radius', 'mag_aperture10', 'mag_aperture15']

		if len(bands) == 0:
			bands = ['g', 'r', 'i', 'z', 'y'] 

		count = 0
		for x in bands:
			for y in columns:
				count+=1
				if count!=len(bands)*len(columns):
					sqlcolumns+=tabname+"."+x+y+","
				else:
					sqlcolumns+=tabname+"."+x+y
		default+=sqlcolumns

		return sqlcolumns

