# batch.py
# ALS 2017/05/29

import numpy as np
import astropy.table as at
import os
import sys
import shutil
import copy

from .. import obsobj

class Batch(object):
	def __init__(self, survey, obj_naming_sys='sdss', args_to_list=[], **kwargs):
		"""
		Batch

		dir_batch is not automatically created, please call mkdir_batch()

		Params
		----------

		/either
			dir_batch (string): path of the directory
		/or 
			dir_parent (string): attr dir_batch is set to dir_parent+name+'/'
			name (string): name of the batch

		/either
			catalog (astropy table): 
				list of objects with columns ['ra', 'dec', ...] or ['RA', 'DEC', ...]
		/or 
			fn_cat (str):
				path to the catalog table file
		/or
			nothing: if dir_batch/list.csv exist, then read in list.csv as catalog 

		survey = (str): either 'sdss' or 'hsc'
		obj_naming_sys = 'sdss' (str): how to name objects in the batch
		args_to_list = [] (list): 
			list of names of additional arguments to pass to list from catalog, e.g., ['z']. 
				

		Attributes
		----------
		dir_batch (str)
		name (str)
		catalog (astropy table): the input catalog
		survey (str)
		obj_naming_sys = 'sdss' (str)

		list (astropy table):
			list of objects with columns ['ra', 'dec', 'obj_name']. 
		list_good (astropy table): 
			same as list but contains only good object
		list_except (astropy table):
			contain objects with exceptions
		args_to_list (list of str):
			list of argument names to include in lists

		dir_good (str)
		dir_except (str)
		fp_list_good (str)
		fp_list_except (str)
		fp_list (str)
		"""

		# set dir_batch, name
		if 'dir_batch' in kwargs:
			self.dir_batch = kwargs.pop('dir_batch', None)
			self.name = self.dir_batch.split('/')[-2]

			if 'name' in kwargs:
				if kwargs['name'] != self.name:
					raise Exception("[batch] input name inconsistent with dir_batch")

		elif ('dir_parent' in kwargs) and ('name' in kwargs):
			self.dir_parent = kwargs.pop('dir_parent', None)
			self.name = kwargs.pop('name', None)
			self.dir_batch = self.dir_parent+self.name+'/'

		else:
			raise Exception("[batch] dir_batch or dir_parent/name not specified")

		# set directories
		self.fp_list = self.dir_batch+'list.csv'
		self.dir_good = self.dir_batch+'good/'
		self.dir_except = self.dir_batch+'except/'
		self.fp_list_good = self.dir_good+'list_good.csv'
		self.fp_list_except = self.dir_except+'list_except.csv'

		# set catalog
		if 'catalog' in kwargs:
			self.catalog = kwargs.pop('catalog', None)

		elif 'fn_cat' in kwargs:
			fn_cat = kwargs.pop('fn_cat', None)
			if os.path.splitext(fn_cat)[1] == '.fits':
				self.catalog = at.Table.read(fn_cat)
			elif os.path.splitext(fn_cat)[1] == '.csv':
				self.catalog = at.Table.read(fn_cat, format='ascii.csv', comment='#')
			else:
				raise Exception("[batch] input catalog file extension not recognized")

		elif os.path.isfile(self.fp_list):
			self.catalog = at.Table.read(fp_list)

		else:
			raise Exception("[batch] input catalog not specified")

		# setting other attribute
		self.survey = survey
		self.obj_naming_sys = obj_naming_sys
		self.args_to_list = args_to_list
		self._make_attr_list()
		self._make_attr_list_good()
		self._make_attr_list_except()

		# sanity check
		if self.dir_batch[-1] != '/':
			raise Exception("[batch] dir_batch not a directory path")

		if self.survey not in ['sdss', 'hsc']:
			raise Exception("[batch] survey not recognized")

		self._check_list_good_except_updated()


	def mkdir_batch(self):
		if not os.path.isdir(self.dir_batch):
			os.makedirs(self.dir_batch)


	def _make_attr_list(self):
		"""
		extract list (table of cols ['ra', 'dec', 'obj_name']) from catalog
		"""
		if ('ra' in self.catalog.colnames) and ('dec' in self.catalog.colnames):
			self.list = self.catalog['ra', 'dec']
		elif ('RA' in self.catalog.colnames) and ('DEC' in self.catalog.colnames):
			self.list = self.catalog['RA', 'DEC']
			self.list.rename_column('RA', 'ra')
			self.list.rename_column('DEC', 'dec')
		else: 
			raise NameError("[batch] catalog table does not contain ra, dec or RA, DEC")

		if 'obj_name' in self.catalog.colnames:
			self.list['obj_name'] = self.catalog['obj_name']
		else: 
			objname = at.Column(name='obj_name', dtype='S64', length=len(self.list))
			for i, row in enumerate(self.list):
				ra = row['ra']
				dec = row['dec']
				objname[i] = obsobj.objnaming.get_obj_name(ra=ra, dec=dec, obj_naming_sys=self.obj_naming_sys)

			self.list.add_column(objname)

		if len(self.args_to_list) > 0:
			self.args_to_list_dtype = self.catalog[self.args_to_list].dtype
			for arg in self.args_to_list:
				self.list[arg] = self.catalog[arg]
		else: 
			self.args_to_list_dtype = None

		self.list.sort('ra')


	def _make_attr_list_good(self):
		if os.path.isfile(self.fp_list_good):
			self.list_good = at.Table.read(self.fp_list_good)
			if len(self.list_good) == 0:
				self.list_good = self._create_empty_list_table()
		else:
			self.list_good = self._create_empty_list_table()

		self.list_good.sort('ra')



	def _make_attr_list_except(self):
		if os.path.isfile(self.fp_list_except):
			self.list_except = at.Table.read(self.fp_list_except)
			if len(self.list_except) == 0:
				self.list_except = self._create_empty_list_table()
		else:
			self.list_except = self._create_empty_list_table()

		self.list_except.sort('ra')


	def _create_empty_list_table(self):

		d = np.dtype([('ra', 'float64'), ('dec', 'float64'), ('obj_name', 'S64')])
		tab0 = at.Table(dtype=d)

		if len(self.args_to_list) > 0:
			tab1 = at.Table(dtype=self.args_to_list_dtype)
			tab =  at.hstack([tab0, tab1])
		else:
			tab = tab0

		return tab


	def _write_list(self):
		self.mkdir_batch()
		self.list.write(self.fp_list, format='ascii.csv', overwrite=True)


	def _write_list_good(self):
		self.mkdir_batch()
		self.list_good.write(self.fp_list_good, format='ascii.csv', overwrite=True)


	def _write_list_except(self):
		self.mkdir_batch()
		self.list_except.write(self.fp_list_except, format='ascii.csv', overwrite=True)


	def iterlist(self, func, listargs=[], listname='good', overwrite=False, **kwargs): 
		"""
		Apply function to each of the objects in list (default: good). Nothing is done to the function return. 

		Params
		------
		func (function):
		    a function that takes in parameter (obj, overwrite, **kwargs), where kwargs includes listargs, and returns result (usually status [bool]). 

		listargs=[] (list of str): names of arguments to pass to func from self.list

		listname='good' (str): name of the list to run on, either 'good' or 'except'. 

		overwrite=False

		**kwargs:
	    	other arguments to be passed to func

	    Return
	    ------
	    results (list):
	    	a list of all the results returned by fun, usually "status" (bool array)
		"""
		if listname == 'good':
			lst = self.list_good
			dir_parent = self.dir_good
		elif listname == 'except':
			lst = self.list_except
			dir_parent = self.dir_except

		# statuss = np.ndarray(len(lst), dtype=bool)
		results = []
		for i, row in enumerate(lst):

			ra = row['ra']
			dec = row['dec']
			obj_name = row['obj_name']

			print("[batch] {obj_name} iterating".format(obj_name=obj_name))

			for arg in listargs:
				kwargs.update({arg: row[arg]})

			obj = obsobj.obsObj(ra=ra, dec=dec, dir_parent=dir_parent, obj_naming_sys=self.obj_naming_sys, overwrite=overwrite)
			obj.survey = self.survey		

			result = func(obj, overwrite=overwrite, **kwargs)
			results += [result]
			# statuss[i] = func(obj, overwrite=overwrite, **kwargs)

		return results
		# return statuss


	def compile_table(self, fn_tab, overwrite=False):
		"""
		compile table fn_tab for the entire batch and creates self.dir_batch+fn_tab.

		Params
		------
		self
		fn_tab (str):
			file name of the table to be compiled, e.g., 'sdss_photoobj.csv'.
		overwrite (bool)

		Return
		------
		status (bool)

		Write output
		------------
		self.dir_batch + fn_tab:
			e.g., 'batch_rz/sdss_photoobj.csv'
		"""		
		fp = self.dir_batch+fn_tab

		if not os.path.isfile(fp) or overwrite:
			print("[batch] compiling table {}".format(fn_tab))

			if len(self.list_good)>0:
				kwargs = dict(fn_tab=fn_tab)
				list_data = self.iterlist(func=self._iterfunc_read_table, listargs=[], listname='good', overwrite=False, **kwargs)
				tab_data = at.vstack(list_data)
				self._rename_list_args(tab_data)
				tab_good = at.hstack([self.list_good, tab_data])
			else:
				tab_good = at.Table()

			if len(self.list_good)>0 and len(self.list_except)>0:
				row_masked = at.Table(tab_data[0], masked=True)
				row_masked.mask = True
				tab_masked = at.vstack([row_masked for i in range(len(self.list_except))])
				self._rename_list_args(tab_masked)
				tab_except = at.hstack([self.list_except, tab_masked])
			else:
				tab_except = at.Table()

			tab = at.vstack([tab_good, tab_except])

			if len(tab) > 0:
				tab.sort('ra')
				tab.write(fp, overwrite=overwrite)
			else:
				# in case if there is no good object
				print("[batch] skipped compiling table {} as no data to compile")

		else:
			print("[batch] skipped compiling table {} as file exists".format(fn_tab))

		status = os.path.isfile(fp)	
		return status 


	def _iterfunc_read_table(self, obj, fn_tab, overwrite=False):
		""" 
		function to be iterated for each object to access the table being compiled

		Params
		------
		self
		obj
		fn_tab (str):
			file name of the table to be compiled, e.g., 'sdss_photoobj.csv'.
		overwrite (bool):
			can be ignored
		"""
		return at.Table.read(obj.dir_obj+fn_tab)


	def _rename_list_args(self, tab):
		""" rename the arguments that could conflict with the ones in list """

		args = ['ra', 'dec', 'obj_name'] + self.args_to_list

		for arg in args:
			if arg in tab.colnames:
				tab.rename_column(arg, arg+'_1')


	def _check_list_good_except_updated(self):
		""" raise exception if not """
		# sanity check -- directories consistent with list_good
		dirs_obj_good = [x[0].split('/')[-1] for x in os.walk(self.dir_good)][1::]
		obj_names_good = copy.copy(self.list_good['obj_name'])
		if dirs_obj_good.sort() != obj_names_good.sort():
			raise Exception("[batch] list_good inconsistent with directories under dirbatch/good/.")

		# sanity check -- directories consistent with list_except
		dirs_obj_except = [x[0].split('/')[-1] for x in os.walk(self.dir_except)][1::]
		obj_names_except = copy.copy(self.list_except['obj_name'])
		if dirs_obj_except.sort() != obj_names_except.sort():
			raise Exception("[batch] list_except inconsistent with directories under dirbatch/except/.")


	def _batch__build_core(self, func_build, overwrite=False, **kwargs):
		"""
		Build batch by making directories and running func_build. To be called by child class. 
		Good objects will be stored in dir_batch/good/.
		Except objects will be stored in dir_batch/except/.

		Params
		------
		func_build=self._func_build (funcion):
			A funciton that takes (obj, overwrite, **kwargs) as param, 
			and returns status (bool)
			The obj contains: ra, dec, dir_parent, dir_obj, name, overwrite, and "survey" of batch
		overwrite=False (bool)
		**kwargs:
			 to be entered into func_build() in the kwargs part

		Return
		----------
		status: True if successful. 
		"""
		self.mkdir_batch()
		self._write_list()

		for directory in [self.dir_good, self.dir_except]:
			if not os.path.isdir(directory):
				os.makedirs(directory)

		if overwrite:
			# reset list_good and list_except
			self.list_good = self._create_empty_list_table()
			self.list_except = self._create_empty_list_table()
		self._write_list_good()
		self._write_list_except()

		for i, row in enumerate(self.list):
			ra = row['ra']
			dec = row['dec']
			obj_name = row['obj_name']
			dir_obj_good = self.dir_good+row['obj_name']+'/'
			dir_obj_except = self.dir_except+row['obj_name']+'/'

			if (obj_name not in self.list_good['obj_name']) and (obj_name not in self.list_except['obj_name']):
				print("[batch] {obj_name} building".format(obj_name=obj_name))

				try:
					obj = obsobj.obsObj(ra=ra, dec=dec, dir_parent=self.dir_good, obj_naming_sys=self.obj_naming_sys, overwrite=overwrite)
					obj.survey = self.survey
					status = func_build(obj=obj, overwrite=overwrite, **kwargs)

				except KeyboardInterrupt, e:
					print("[batch] func_build() encounters exception {0}".format(str(e)))
					if os.path.isdir(dir_obj_good) and (obj_name not in self.list_good['obj_name']):
						shutil.rmtree(dir_obj_good)
					sys.exit(1)

				if status:
					print("[batch] Successful")
					self.list_good = at.vstack([self.list_good, row])
					self._write_list_good()
				else: 
					print("[batch] Failed, moving to except/. ")
					self.list_except = at.vstack([self.list_except, row])
					shutil.move(dir_obj_good, dir_obj_except)
					self._write_list_except()
			else: 
				print("[batch] {obj_name} skipped".format(obj_name=obj_name))

		self._check_list_good_except_updated()


		# status reflects that all is ran (list = list_good + list_except)
		list_ran = []
		for lst in [self.list_good, self.list_except]:
			if len(lst)>0:
				list_ran += list(lst['obj_name'])

		obj_names = self.list['obj_name']
		status = (obj_names.sort() == (list_ran).sort())

		if status: 
			print("[batch] building batch {0} done".format(self.name))
		else: 
			print("[batch] building batch {0} unfinished".format(self.name))

		return status


