from __future__ import print_function
from collections import OrderedDict
from json import dumps
from pprint import pprint
from sys import version_info
from inspect import ismethod

try:
    from collections.abc import MutableMapping
except ImportError:
    from collections import MutableMapping

# for debugging
def here(item=None):
	out = 'here'
	if item != None:
		out += '({})'.format(item)
	print(out)


class DotMap(MutableMapping, OrderedDict):
	def __init__(self, *args, **kwargs):
		self._map = OrderedDict()
		self._dynamic = True
		if kwargs:
			if '_dynamic' in kwargs:
				self._dynamic = kwargs['_dynamic']
		if args:
			d = args[0]
			if isinstance(d, dict):
				for k,v in self.__call_items(d):
					if isinstance(v, dict):
						v = DotMap(v, _dynamic=self._dynamic)
					if type(v) is list:
						l = []
						for i in v:
							n = i
							if type(i) is dict:
								n = DotMap(i, _dynamic=self._dynamic)
							l.append(n)
						v = l
					self._map[k] = v
		if kwargs:
			for k,v in self.__call_items(kwargs):
				if k != '_dynamic':
					self._map[k] = v

	def __call_items(self, obj):
		if hasattr(obj, 'iteritems') and ismethod(getattr(obj, 'iteritems')):
			return obj.iteritems()
		else:
			return obj.items()

	def items(self):
		return self.iteritems()

	def iteritems(self):
		return self.__call_items(self._map)

	def __iter__(self):
		return self._map.__iter__()

	def next(self):
		return self._map.next()

	def __setitem__(self, k, v):
		self._map[k] = v
	def __getitem__(self, k):
		if k not in self._map and self._dynamic and k != '_ipython_canary_method_should_not_exist_':
			# automatically extend to new DotMap
			self[k] = DotMap()
		return self._map[k]

	def __setattr__(self, k, v):
		if k in {'_map','_dynamic', '_ipython_canary_method_should_not_exist_'}:
			super(DotMap, self).__setattr__(k,v)
		else:
			self[k] = v

	def __getattr__(self, k):
		if k in {'_map','_dynamic','_ipython_canary_method_should_not_exist_'}:
			super(DotMap, self).__getattr__(k)
		else:
			return self[k]

	def __delattr__(self, key):
		return self._map.__delitem__(key)

	def __contains__(self, k):
		return self._map.__contains__(k)

	def __str__(self):
		items = []
		for k,v in self.__call_items(self._map):
			# bizarre recursive assignment situation (why someone would do this is beyond me)
			if id(v) == id(self):
				items.append('{0}=DotMap(...)'.format(k))
			else:
				items.append('{0}={1}'.format(k, repr(v)))
		joined = ', '.join(items)
		out = '{0}({1})'.format(self.__class__.__name__, joined)
		return out

	def __repr__(self):
		return str(self)

	def toDict(self):
		d = {}
		for k,v in self.items():
			if type(v) is DotMap:
				# bizarre recursive assignment support
				if id(v) == id(self):
					v = d
				else:
					v = v.toDict()
			elif type(v) in (list, tuple):
				l = []
				for i in v:
					n = i
					if type(i) is DotMap:
						n = i.toDict()
					l.append(n)
				if type(v) is tuple:
					v = tuple(l)
				else:
					v = l
			d[k] = v
		return d

	def pprint(self, pformat='dict'):
		if pformat == 'json':
			print(dumps(self.toDict(), indent=4, sort_keys=True))
		else:
			pprint(self.toDict())

	def empty(self):
		return (not any(self))

	# proper dict subclassing
	def values(self):
		return self._map.values()

	# ipython support
	def __dir__(self):
		return self.keys()

	@classmethod
	def parseOther(self, other):
		if type(other) is DotMap:
			return other._map
		else:
			return other
	def __cmp__(self, other):
		other = DotMap.parseOther(other)
		return self._map.__cmp__(other)
	def __eq__(self, other):
		other = DotMap.parseOther(other)
		if not isinstance(other, dict):
			return False
		return self._map.__eq__(other)
	def __ge__(self, other):
		other = DotMap.parseOther(other)
		return self._map.__ge__(other)
	def __gt__(self, other):
		other = DotMap.parseOther(other)
		return self._map.__gt__(other)
	def __le__(self, other):
		other = DotMap.parseOther(other)
		return self._map.__le__(other)
	def __lt__(self, other):
		other = DotMap.parseOther(other)
		return self._map.__lt__(other)
	def __ne__(self, other):
		other = DotMap.parseOther(other)
		return self._map.__ne__(other)

	def __delitem__(self, key):
		return self._map.__delitem__(key)
	def __len__(self):
		return self._map.__len__()
	def clear(self):
		self._map.clear()
	def copy(self):
		return DotMap(self)
	def __copy__(self):
		return self.copy()
	def __deepcopy__(self, memo=None):
		return self.copy()
	def get(self, key, default=None):
		return self._map.get(key, default)
	def has_key(self, key):
		return key in self._map
	def iterkeys(self):
		return self._map.iterkeys()
	def itervalues(self):
		return self._map.itervalues()
	def keys(self):
		return self._map.keys()
	def pop(self, key, default=None):
		return self._map.pop(key, default)
	def popitem(self):
		return self._map.popitem()
	def setdefault(self, key, default=None):
		self._map.setdefault(key, default)
	def update(self, *args, **kwargs):
		if len(args) != 0:
			self._map.update(*args)
		self._map.update(kwargs)
	def viewitems(self):
		return self._map.viewitems()
	def viewkeys(self):
		return self._map.viewkeys()
	def viewvalues(self):
		return self._map.viewvalues()
	@classmethod
	def fromkeys(cls, seq, value=None):
		d = DotMap()
		d._map = OrderedDict.fromkeys(seq, value)
		return d
	def __getstate__(self): return self.__dict__
	def __setstate__(self, d): self.__dict__.update(d)
	# bannerStr
	def _getListStr(self,items):
		out = '['
		mid = ''
		for i in items:
			mid += '  {}\n'.format(i)
		if mid != '':
			mid = '\n' + mid
		out += mid
		out += ']'
		return out
	def _getValueStr(self,k,v):
		outV = v
		multiLine = len(str(v).split('\n')) > 1
		if multiLine:
			# push to next line
			outV = '\n' + v
		if type(v) is list:
			outV = self._getListStr(v)
		out = '{} {}'.format(k,outV)
		return out
	def _getSubMapDotList(self, pre, name, subMap):
		outList = []
		if pre == '':
			pre = name
		else:
			pre = '{}.{}'.format(pre,name)
		def stamp(pre,k,v):
			valStr = self._getValueStr(k,v)
			return '{}.{}'.format(pre, valStr)
		for k,v in subMap.items():
			if isinstance(v,DotMap) and v != DotMap():
				subList = self._getSubMapDotList(pre,k,v)
				outList.extend(subList)
			else:
				outList.append(stamp(pre,k,v))
		return outList
	def _getSubMapStr(self, name, subMap):
		outList = ['== {} =='.format(name)]
		for k,v in subMap.items():
			if isinstance(v,DotMap) and v != DotMap():
				# break down to dots
				subList = self._getSubMapDotList('',k,v)
				# add the divit
				# subList = ['> {}'.format(i) for i in subList]
				outList.extend(subList)
			else:
				out = self._getValueStr(k,v)
				# out = '> {}'.format(out)
				out = '{}'.format(out)
				outList.append(out)
		finalOut = '\n'.join(outList)
		return finalOut
	def bannerStr(self):
		lines = []
		previous = None
		for k,v in self.items():
			if previous == 'DotMap':
				lines.append('-')
			out = ''
			if isinstance(v,DotMap):
				name = k
				subMap = v
				out = self._getSubMapStr(name,subMap)
				lines.append(out)
				previous = 'DotMap'
			else:
				out = self._getValueStr(k,v)
				lines.append(out)
				previous = 'other'
		lines.append('--')
		s = '\n'.join(lines)
		return s


if __name__ == '__main__':
	# basics
	print('\n== basics ==')
	d = {
		'a':1,
		'b':2,
		'subD': {'c':3, 'd':4}
	}
	dd = DotMap(d)
	print(dd)
	print(len(dd))
	print(dd.copy())
	print(dd)
	print(OrderedDict.fromkeys([1,2,3]))
	print(DotMap.fromkeys([1,2,3], 'a'))
	print(dd.get('a'))
	print(dd.get('f',33))
	print(dd.get('f'))
	print(dd.has_key('a'))
	dd.update([('rat',5),('bum',4)], dog=7,cat=9)
	dd.update({'lol':1,'ba':2})
	print(dd)
	print
	for k in dd:
		print(k)
	print('a' in dd)
	print('c' in dd)
	dd.c.a = 1
	print(dd.toDict())
	dd.pprint()
	print
	print(dd.values())
	dm = DotMap(name='Steve', job='programmer')
	print(dm)
	print(issubclass(dm.__class__, dict))
	am = DotMap()
	am.some.deep.path.cuz.we = 'can'
	print(am)
	del am.some.deep
	print(am)
	parentDict = {
		'name': 'Father1',
		'children': [
			{'name': 'Child1'},
			{'name': 'Child2'},
			{'name': 'Child3'},
		]
	}
	parent = DotMap(parentDict)
	print([x.name for x in parent.children])

	# pickle
	print('\n== pickle ==')
	import pickle
	s = pickle.dumps(parent)
	d = pickle.loads(s)
	print(d)

	# init from DotMap
	print('\n== init from DotMap ==')
	e = DotMap(d)
	print(e)

	# empty
	print('\n== empty() ==')
	d = DotMap()
	print(d.empty())
	d.a = 1
	print(d.empty())
	print()
	x = DotMap({'a': 'b'})
	print(x.b.empty()) # True (and creates empty DotMap)
	print(x.b) # DotMap()
	print(x.b.empty()) # also True

	# _dynamic
	print('\n== _dynamic ==')
	d = DotMap()
	d.still.works
	print(d)
	d = DotMap(_dynamic=False)
	try:
		d.no.creation
		print(d)
	except KeyError:
		print('KeyError caught')
	d = {'sub':{'a':1}}
	dm = DotMap(d)
	print(dm)
	dm.still.works
	dm.sub.still.works
	print(dm)
	dm2 = DotMap(d,_dynamic=False)
	try:
		dm.sub.yes.creation
		print(dm)
		dm2.sub.no.creation
		print(dm)
	except KeyError:
		print('KeyError caught')

	# _dynamic
	print('\n== toDict() ==')
	conf = DotMap()
	conf.dep = DotMap(facts=DotMap(operating_systems=DotMap(os_CentOS_7=True), virtual_data_centers=[DotMap(name='vdc1', members=['sp1'], options=DotMap(secret_key='badsecret', description='My First VDC')), DotMap(name='vdc2', members=['sp2'], options=DotMap(secret_key='badsecret', description='My Second VDC'))], install_node='192.168.2.200', replication_group_defaults=DotMap(full_replication=False, enable_rebalancing=False, description='Default replication group description', allow_all_namespaces=False), node_defaults=DotMap(ntp_servers=['192.168.2.2'], ecs_root_user='root', dns_servers=['192.168.2.2'], dns_domain='local', ecs_root_pass='badpassword'), storage_pools=[DotMap(name='sp1', members=['192.168.2.220'], options=DotMap(ecs_block_devices=['/dev/vdb'], description='My First SP')), DotMap(name='sp2', members=['192.168.2.221'], options=DotMap(protected=False, ecs_block_devices=['/dev/vdb'], description='My Second SP'))], storage_pool_defaults=DotMap(cold_storage_enabled=False, protected=False, ecs_block_devices=['/dev/vdc'], description='Default storage pool description'), virtual_data_center_defaults=DotMap(secret_key='badsecret', description='Default virtual data center description'), management_clients=['192.168.2.0/24'], replication_groups=[DotMap(name='rg1', members=['vdc1', 'vdc2'], options=DotMap(description='My RG'))]), lawyers=DotMap(license_accepted=True))
	print(conf.dep.toDict()['facts']['replication_groups'])

	# recursive assignment
	print('\n== recursive assignment ==')
	# dict
	d = dict()
	d['a'] = 5
	print(id(d))
	d['recursive'] = d
	print(d)
	print(d['recursive']['recursive']['recursive'])
	# DotMap
	m = DotMap()
	m.a = 5
	print(id(m))
	m.recursive = m
	print(m.recursive.recursive.recursive)
	print(m)
	print(m.toDict())

	# kwarg
	print('\n== kwarg ==')
	def test(**kwargs):
		print(kwargs)
	class D:
		def keys(self):
			return ['a', 'b']
		def __getitem__(self, key):
			return 0
	a = {'1':'a', '2':'b'}
	b = DotMap(a, _dynamic=False)
	o = OrderedDict(a)
	test(**a)
	test(**b.toDict())
	test(**o)
	test(**D())

	# ordering
	print('\n== ordering ==')
	m = DotMap()
	m.alpha = 1
	m.bravo = 2
	m.charlie = 3
	m.delta = 4
	for k,v in m.items():
		print(k,v)

	# subclassing
	print('\n== subclassing ==')
	d = DotMap()
	o = OrderedDict()
	print(isinstance(d, dict))
	print(isinstance(o, dict))
	e = DotMap(m)
	print(e)

	# deepcopy
	print('\n== deepcopy ==')
	import copy
	t = DotMap()
	t.a = 1
	t.b = 3
	f = copy.deepcopy(t)
	t.a = 2
	print(t)
	print(f)

	# copy order preservation
	print('\n== copy order preservation ==')
	t = DotMap()
	t.a = 1
	t.b = 2
	t.c = 3
	copies = []
	print(id(t))
	for i in range(3):
		copyMap = copy.deepcopy(t)
		copies.append(copyMap)
		print(id(copyMap))
	print()
	for copyMap in copies:
		for k,v in copyMap.items():
			print(k,v)
		print()

	# bannerStr
	print('\n== bannerStr ==')
	t.cities.LA = 1
	t.cities.DC = 2
	t.cities.London.pop = 'many'
	t.cities.London.weather = 'rain'
	haiku = '\n'.join([
		"Haikus are easy",
		"But sometimes they don't make sense",
		"Refrigerator",
	])
	t.haiku = haiku
	t.teams.blue = 1
	t.teams.red = 2
	t.teams.green = 3
	t.colors.blue = 1
	t.colors.red = 2
	t.colors.green = 3
	t.numbers.short = list(range(4))
	t.numbers.early = list(range(10))
	t.numbers.backwards = list(range(10,-1,-1))
	t.deepLog.deeper.Q = list(range(4))
	print(t.bannerStr())

	# sub-DotMap deepcopy
	print('\n== sub-DotMap deepcopy ==')
	import copy
	l = []
	d = {'d1': {'d2': ''}}
	m = DotMap(d)
	for i in range(3):
		x = copy.deepcopy(m)
		x.d1.d2 = i
		l.append(x)
	for m in l:
		print(m)

	# tuple toDict
	print('\n== DotMap tuple toDict ==')
	m = DotMap({'a': 1, 'b': (11, 22, DotMap({'c': 3}))})
	d = m.toDict()
	print(d)

	# unpacking tests
	'''
	print('\n== Unpacking ==')
	d = {'a':1}
	print({**d})
	m = DotMap(a=1)
	print({**m.toDict()})
	m = DotMap(a=1)
	print({**m})
	'''

	# final print
	print()
