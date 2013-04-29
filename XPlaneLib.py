import sys
import os
import Blender
from Blender import Armature, Object, Mesh, NMesh, Lamp, Image, Material, Texture, Draw, Window, Text
from Blender.Mathutils import Matrix, RotationMatrix, TranslationMatrix, Vector
from XPlaneUtils import *
from Blender.Window import GetCursorPos
from XPlaneExport import ExportError
#from XPlaneImport import OBJimport, ParseError

# Given a path to ANY resource inside x-plane, return a tuple of: full path to x-plane folder, full path to scenery pack.
def locate_root(path):
	hierarchy = path.split('/')
	for known_folder in [['Custom Scenery',1], ['Global Scenery',1], ['default scenery',2]]:
		if known_folder[0] in hierarchy:
			idx = hierarchy.index(known_folder[0])
			return ('/'.join(hierarchy[:(idx+1-known_folder[1])]),'/'.join(hierarchy[:(idx+2)]))
	raise ExportError("X-Plane folder not found.  Your blender file must be INSIDE a scenery package!")

# return a list of all scenery pack path names
def get_scenery_packs(root):
	results=[]
	for known_folder in ['Custom Scenery','Global Scenery','Resources/default scenery']:
		try:
			packs=os.listdir(root+'/'+known_folder)
			for pack in packs:
				results.append(root+'/'+known_folder+'/'+pack)
		except OSError, e:
			pass
	return results

# Given a scenery pack, return pair partial, full paths to all art assets with a given suffix.	
def get_local_assets(pack, suffix):
	results=[]
	l=len(suffix)
	for root, dirs, files in os.walk(pack):
		for f in files:
			if f[-l:].lower() == suffix.lower():
				if root == pack:
					results.append([f,root+'/'+f,'lcl'])
				else:
					results.append([root[len(pack)+1:]+'/'+f,root+'/'+f,'lcl'])
	return results
	
# Given a scenery pack, get a list of tuples, full virtual, full real path for each lib entry.
def get_library_assets(pack, suffix):
	sl = len(suffix)
	results=[]
	try:
		fi=open(pack+'/library.txt','r')
		for l in fi:
			t=l.split()
			if len(t) > 2:				
				if t[0] in ['EXPORT','EXPORT_EXCLUDE','EXPORT_EXTEND']:
					if t[2][-sl:].lower() == suffix.lower():
						results.append([t[1],pack+'/'+t[2],'lib'])
		fi.close()
	except IOError, e:
		pass
	return results

# Given the x-plane folder, get the ENTIRE library for one asset type, as a list of tuples, virtual to full real.
def get_library(root,suffix):
	results=[]
	packs=get_scenery_packs(root)
	for p in packs:
		li = get_library_assets(p,suffix)
		results.extend(li)
	return results

