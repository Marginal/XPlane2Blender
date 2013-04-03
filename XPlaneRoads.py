#!BPY
""" Registration info for Blender menus:
Name: 'X-Plane Roads'
Blender: 245
Group: 'Export'
Tooltip: 'Export to X-Plane Road (.net)
"""
__author__ = "Ben Supnik"
__email__ = "bsupnik at xsquawkbox dot net"
__url__ = "http://scenery.x-plane.com/"
__version__ = "1.0"
__bpydoc__ = """\
This script makes X-Plane road files.  A lot of the routines are based on Jonathan Harris' X-Plane 8 OBJ export script; this
should be considered a derived work (and thus GPL).
"""

import sys
import Blender
from Blender import Armature, Mesh, Lamp, Image, Draw, Window
from Blender.Mathutils import Matrix, RotationMatrix, TranslationMatrix, MatMultVec, Vector, Quaternion, Euler
from XPlaneUtils import *
from XPlaneMacros import *
from XPlaneExport import ExportError
from re import *

def emit_multi_prop(file, obj, prop_name):
	count=0
	for p in obj.getAllProperties():
		if strip_suffix(p.name.upper()) == prop_name.upper():
			file.write("%s %s\n" % (strip_suffix(p.name.upper()), str(p.data)))
			count=count+1
	if count == 0 and obj.getParent() != None:
		emit_multi_prop(file,obj.getParent(), prop_name)

def emit_properties(file, obj, prop_list):
	for p in prop_list:
		emit_multi_prop(file,obj,p)

def checkFile (filename):
    try:
        file = open(filename, "rb")
    except IOError:
        return 1        
    file.close()
    if Draw.PupMenu("Overwrite?%%t|Overwrite file: %s" % filename)!=1:
        print "Cancelled\n"
        return 0
    return 1

class VT:
	def __init__(self, v, no, uv, w, want_up):
		self.v = v
		self.no = no
		self.uv = uv
		self.w = w
		if want_up:
			self.no[0]=0
			self.no[1]=0
			self.no[2]=1
		
	# WICKED CHEESY!  Compare string text to avoid failed compare for tiny jitters in FP.
	def equals(self, rhs):
		return str(self) == str(rhs)
	
	def __cmp__ (self,other):
		return cmp(str(self),str(other))
	
	def __str__ (self):
		out = "VERTEX %f %f %f\t%f %f %f\t%f %f\t" % (self.v[0], self.v[2], -self.v[1], self.no[0], self.no[2], -self.no[1], self.uv[0], self.uv[1])
		for w in self.w:
			out += " %s %f" % (w[0], w[1])
		out += "\n"
		return out

def far_lod_from_layers(layers):
	lod_far=4000
	if 2 in layers:
		lod_far=8000
	if 3 in layers:
		lod_far=23000
	return lod_far


def out_seg(file,grp,layer,shader_idx,width,hard,surface,graded,v1,v2,v3,uv1,uv2,uv3,ctr,len):
	lod_near=0
	lod_far=far_lod_from_layers(layer)
	surf=""
	if not hard:
		surf=' ' + surface
	uv_range = abs(uv3[1] - uv1[1])
	len_rat = len / abs(round(v3[1] - v1[1]))
	t_ratio =  len_rat * uv_range
	if graded:
		file.write("SEGMENT_GRADED %d\t%f %f\t%f\t%f %f %f %f %f %f%s\n" % (shader_idx, lod_near, lod_far, t_ratio,
			round(v1[0]-ctr,5), round(v1[2],5), round(uv1[0]*width,1), round(v2[0]-ctr,5), round(v2[2],5), round(uv2[0]*width, 1),
			surf))
	else:
		file.write("SEGMENT_DRAPED %d\t%f %f\t%f\t%f %f %f %f%s\n" % (shader_idx, lod_near, lod_far, t_ratio,
			round(v1[0]-ctr,5), round(uv1[0]*width,1), round(v2[0]-ctr,5), round(uv2[0]*width, 1),
			surf))
		

def out_obj(obj,file,oname, mode, xyz,xr,yr,zr,spans,span_length,ctr):	
	oname = get_prop(obj,'external', oname)
	graded = has_prop(obj,'graded')
	cmd="OBJECT_DRAPED"
	if graded:
		cmd="OBJECT_GRADED"

	if mode == "DIST":
		repeat_len=(spans-1) * span_length
		if repeat_len <= 0.0 or span_length <= 0.0:
			raise ExportError("Object has repeat interval that is not positive: %s/%s" % (obj.parent.name,obj.name))
		start_offset=xyz[1]
		end_offset = min(start_offset,span_length-start_offset)
		while end_offset > span_length:
			end_offset = end_offset - span_length
		if end_offset < 1.0:
			end_offset = span_length
	else:
		repeat_len=span_length
		start_offset=xyz[1]
		end_offset=xyz[1]
		
	# note: this used to use the road modeled length as period.  But this sucks for Alex because he would have to model only ONE unit of road to get the right
	# pylon wavelength.  Then his end cap and pylon would overlap which would be visually undesireable.
	file.write("%s %s %s\t%f %f %f %f %f %f %f/%f %f/%f" % (cmd,mode,oname,
		xyz[0]-ctr,xyz[0]-ctr,
		round(zr * 180 / 3.14159265),
		round(zr * 180 / 3.14159265),
		repeat_len,repeat_len,
		start_offset,end_offset,
		start_offset,end_offset))
	if has_prop(obj,'obj_show_level'):
		file.write(" %s" % get_prop(obj,'obj_show_level',''))
	file.write("\n")
	obj_keys = ['OBJECT_FREQ', 'OBJECT_ALT' ];
	emit_properties(file, obj, obj_keys)
	return graded

def out_car(obj, file,oname, xyz,xr,yr,zr):
	rev = 0
	oname = get_prop(obj,'external', oname)
	graded = has_prop(obj,'graded')	
	if zr > 1.0: rev = 1
	cmd="CAR_DRAPED"
	if graded:
		cmd="CAR_GRADED"
	file.write("%s %d %f %f %f %s\n" % (cmd, rev, xyz[0], 60.0, 0.01, oname))

def near_zero(x):
	return x > -0.001 and x < 0.001

def bone_length_to_me(bone):
	r = 0.0
	b = bone.parent
	while b != None:
		r += b.length
		b = b.parent
	return r
	
	
def export_edge_bone(file, degree, finger, x, y, z, meta_rect):
	l=meta_rect[0]
	b=meta_rect[1]
	r=meta_rect[2]
	t=meta_rect[3]
	cx = (l+r)*0.5
	cy = (b+t)*0.5
	
	if degree == 3:
		if y > cy:
			corner = 0
		else:
			corner = 2
	else:
		if x < cx:
			if y < cy:
				corner=0
			else:
				corner=1
		else:
			if y < cy:
				corner=3
			else:
				corner=2
	if degree == 2:
		if corner == 3: corner = 0
		elif corner == 2: corner = 1
	
	corner_next = (corner + 1) % degree
	
	if finger == corner:
		is_right = 0
	elif finger == corner_next:
		is_right = 1
	else:
		raise ExportError("Junction references a finger that is not appropriate for its corner. finger = %d, corner = %d, degree = %d" % (finger, corner, degree))
	
	if degree == 3:
		if corner == 0:
			off_1 = t-y
			off_2 = l-x
		elif corner == 2:
			off_1 = x-l
			off_2 = b-y

		if finger == 0:
			dx = -1
			dz = 0
		elif finger == 1:
			dx = 0
			dz = -1
		elif finger == 2:
			dx = 0
			dz = 1
	else:
		if corner == 0:
			off_1 = x-l
			off_2 = b-y
		elif corner == 1:
			off_1 = t-y
			off_2 = l-x
		elif corner == 2:
			off_1 = r-x
			off_2 = y-t
		elif corner == 3:
			off_1 = y-b
			off_2 = x-r

		if finger == 0:
			dx = 0
			dz = 1
		elif finger == 1:
			dx = -1
			dz = 0
		elif finger == 2:
			dx = 0
			dz = -1
		elif finger == 3:
			dx = 1
			dz = 0
	
	off_1 = round(off_1,5)
	off_2 = round(off_2,2)
	x = round(x,5)
	y = round(y,5)
	z = round(z,5)
	
	if is_right:
		file.write("BONE_INTERSECTION_EDGE_RIGHT %d %f %f   %f %f %f %f %f %f\n" %( corner, off_1, off_2, x, z, -y, dx, 0, dz))
	else:
		file.write("BONE_INTERSECTION_EDGE_LEFT %d %f %f   %f %f %f %f %f %f\n" %( corner, off_1, off_2, x, z, -y, dx, 0, dz))


def export_app_bone(file, x, y, z, meta_rect):
	l=meta_rect[0]
	b=meta_rect[1]
	r=meta_rect[2]
	t=meta_rect[3]
	x = round(x,5)
	y = round(y,5)
	z = round(z,5)
	
	cy = (b+t)*0.5
	if y < cy:
		file.write("BONE_APPROACH_RIGHT 1 %f %f   %f %f %f -1 0 0\n" % (b-y,x-l, x, z, -y))
	else:
		file.write("BONE_APPROACH_LEFT 1 %f %f   %f %f %f -1 0 0\n" % (t-y,x-l, x, z, -y))
	
def export_any_bone(file, name, x, y, z, dx, dy, dz):
	if has_prefix(name, 'EL'):
		cmd="BONE_INTERSECTION_EDGE_LEFT"
		metrics=strip_prefix(name,'EL')
	elif has_prefix(name, 'ER'):
		cmd="BONE_INTERSECTION_EDGE_RIGHT"
		metrics=strip_prefix(name,'ER')
	elif has_prefix(name, 'AL'):
		cmd="BONE_APPROACH_LEFT"
		metrics=strip_prefix(name,'AL')
	elif has_prefix(name, 'AR'):
		cmd="BONE_APPROACH_RIGHT"
		metrics=strip_prefix(name,'AR')
	else:
		raise ExportError("Bone %s - I cannot parse this prefix" % name)
	metrics = metrics.replace(",",".",3)
	nums = metrics.split()
	if len(nums) != 3:
		raise ExportError("Bone %s - I cannot parse these numbers: %s" % (name, metrics))
	file.write("%s %d %f %f     %f %f %f   %f %f %f\n" % (cmd, int(nums[0]),float(nums[1]),float(nums[2]),  x,z,-y,   dx,dz,-dy))
	
	
	
def read_lib(path, list):
	try:
		fi = open(path,'r')
		for line in fi:
			l = line.split()
			if len(l) > 2:
				if l[0] == 'EXPORT_EXTEND' or l[0] == 'EXPORT' or l[0] == 'EXPORT_EXCLUDE':
					list.append(l[1])
		fi.close()
	except:
		print "No library found."

def read_dirs(path, partial, lib):
	files = os.listdir(path)
	for f in files:
		if len(f) > 4 and f[-4:].lower() == '.obj':
			lib.append(partial[1:]+'/'+f)
		if os.path.isdir(path+'/'+f):
			read_dirs(path+'/' + f, partial + '/' + f, lib)
			
def add_subs(matches, value, fmt):
	ret = []
	for m in matches:
		pat = fmt % m
		rep = str(value + float(m))
		p = [pat, rep]
		ret.append(p)
	return ret

def do_macros(file, obj, l,c,r,d):
	lpat = compile("LFT\(([^)]*)\)")
	rpat = compile("RGT\(([^)]*)\)")
	cpat = compile("CTR\(([^)]*)\)")
	
	dict = [['(DRP)', d]]

	for p in obj.getAllProperties():
		if strip_suffix(p.name.upper()) == 'MACRO':
			m = get_macro(p.data)
			if m != None:
				lf = lpat.findall(m)
				rf = rpat.findall(m)
				cf = cpat.findall(m)
				dict += add_subs(lf,l,'LFT(%s)')
				dict += add_subs(cf,c,'CTR(%s)')
				dict += add_subs(rf,r,'RGT(%s)')
				for d in dict:
					m = m.replace(d[0],d[1])
				file.write("%s" % m)

#
# Desired behavior
# 
# A---B---C---D
#
# spots A & D only used for begin/end - left blank for distance.
# number of spans must be number of elems in seq + 1 - this is a TWO pylon seq
# No blanks - Alex MUST provide obj C for the two pattern repeat.  If he wants B 
# over and over he gives me only two spans.

def guess_spans(length, bgn_objs, end_objs, mid_objs):
	locs=[]
	for l in [bgn_objs, end_objs, mid_objs]:
		for o in l:
			locs.append(o.getMatrix('localspace').translationPart()[1])
	if len(bgn_objs) < 1:
		locs.append(0)
	if len(end_objs) < 1:
		locs.append(length)
	locs.sort()
	if len(locs) < 3:
		return 1	
	real_len = round(locs[-1] - locs[0])
	for span in xrange(1,10):
		target_length = real_len / span
		worst_fractional_error = 0
		#print "Trying span %f, target length: %f" % (span, target_length)
		for l in locs:
			ratio = l / target_length
			fractional_error = abs(ratio - round(ratio))
			worst_fractional_error = max(worst_fractional_error, fractional_error)
			#print "  for obj at %f, ratio %f, error %f" % (l, ratio, fractional_error)
		if worst_fractional_error < 0.1:
			#print "Keeping span %f, err %f" % (span, worst_fractional_error)
			return span			
	return 1
	
#------------------------------------------------------------------------
#-- Exporter Class
#------------------------------------------------------------------------
class RoadExport:

	#------------------------------------------------------------------------
	def __init__(self, filename):		
		#--- public you can change these ---
		self.debug=1	# extra debug info in console

		#--- class private don't touch ---
		self.file=None
		self.filename=filename
		self.log=[]
		self.lib=[]
		self.last_scale=0
		lib_path=os.path.dirname(filename)+'/library.txt'
		read_lib(lib_path, self.lib)
		read_dirs(os.path.dirname(filename),'',self.lib)

    #------------------------------------------------------------------------
	def export(self, scene):
		print 'Starting road.net export to ' + self.filename

		if not checkFile(self.filename):
			return

		self.file = open(self.filename, 'w')
		self.file.write("A\n800\nROADS\n\n")
		
		self.shaders = SHADER_SET()
		
		header = text_for_obj('header')
		for h in header:
			self.file.write("%s\n" % h)
			if self.shaders.is_shader_line(h):
				self.shaders.handle_shader_line(h)

		scenes = Scene.Get()
		for s in scenes:
# ALEX - COMMENT OUT THIS LINE TO EXPORT EVERY SCENE!  LEAVE IT IN TO GET ONLY THE CURRENT SCENE.
			if s == scene:
				self.file.write("# Scene %s:\n" % s.getName())
				things = getAllDepth(0,s.objects)
				self.export_things(things,s.objects)

		footer = text_for_obj('footer')
		for f in footer:
			self.file.write("%s\n" % f)


		self.file.close		
		if self.log:
			r=Draw.PupMenu('|'.join([a[0] for a in self.log]))
	
	def export_group(self, obj, scene):
		self.file.write("# Group: %s\n" % strip_suffix(obj.name))
		children = getChildren(obj, scene)
		self.export_things(children, scene)
		
	def export_things(self, things, scene):
		bridges = filter_objects(things,'Empty', 'BRG')
		roads = filter_objects(things,'Empty', 'ROA')
		plugs = filter_objects(things,'Armature', 'PLG')
		byts = filter_objects(things,'Armature', 'BYT')
		grups = filter_objects(things,'Empty', 'GRP')
		roads.extend(bridges)
		plugs.extend(byts)

		roads.sort(key=sort_obj_by_name)
		plugs.sort(key=sort_obj_by_name)
		grups.sort(key=sort_obj_by_name)
		
		for r in roads:
			self.export_chain(r, scene)
		for p in plugs:
			self.export_plug(p, scene)
		for g in grups:
			self.export_group(g, scene)
	
	def export_chain(self, obj, scene):
		if self.debug: print "Exporting chain based on empty obj %s." % obj.name
		# First pass: pull out all segments.  Hels us find real lenght
		max_len=0
		name=strip_suffix(obj.name[3:])
		
		
		annotations = getChildren(obj,scene)
		segs = filter_objects(annotations,'Mesh', '')
		objs = filter_objects(annotations,'Empty','OBJ')
		obj2 = filter_objects(annotations,'Mesh','OBJ')
		ends = filter_objects(annotations,'Empty','END')
		end2 = filter_objects(annotations,'Mesh','END')
		bgns = filter_objects(annotations,'Empty','BGN')
		bgn2 = filter_objects(annotations,'Mesh','BGN')
		vrts = filter_objects(annotations,'Empty','VRT')
		vrt2 = filter_objects(annotations,'Mesh','VRT')
		cars = filter_objects(annotations,'Empty','CAR')
		car2 = filter_objects(annotations,'Mesh','CAR')
		objs.extend(obj2)
		ends.extend(end2)
		bgns.extend(bgn2)
		vrts.extend(vrt2)
		cars.extend(car2)

		bounds = []
		
		for s in segs:
			if 1 in s.layers or 2 in s.layers or 3 in s.layers:
				if not s in objs and not s in ends and not s in bgns and not s in cars and not s in vrts:
					mesh=s.getData(mesh=True)					
					mm=s.getMatrix('localspace')
					for v in mesh.verts:
						vc=xform(v,mm)
						if len(bounds) == 0:
							bounds.extend(vc)
							bounds.extend(vc)
						else:
							for n in [0,1,2]:
								bounds[n  ] = min(bounds[n  ],vc[n])
								bounds[n+3] = max(bounds[n+3],vc[n])

		rwidth = abs(round(bounds[3] - bounds[0],4))
		rlength = abs(round(bounds[4] - bounds[1],4))
		rwidth = float(get_prop(obj,'width',str(rwidth)))
		rgb = get_prop(obj, 'RGB', "1 1 1")

		num_lengths=1
		if has_prop(obj,'spans'):
			num_lengths=float(get_prop(obj,'spans','1'))			
		else:
			num_lengths = guess_spans(rlength, bgns, ends, objs)
		rlength /= num_lengths
		self.file.write("\n#%s (%d spans)\n" % (get_prop(obj,'NAME',obj.name[3:]), num_lengths))
		self.file.write("ROAD_TYPE %s %.4f %.4f 0 %s\n" % (name.split('.')[0], rwidth, rlength, rgb))
		if has_prop(obj,'ROAD_CENTER'):
			bounds[0] = -float(get_prop(obj,'ROAD_CENTER',str(rwidth*0.5)))
		elif has_prop(obj,'width'):
			bounds[0] = -(rwidth*0.5)
		self.file.write("ROAD_CENTER %f\n" % -bounds[0])
		road_keys = ['REQUIRE_EVEN', 'SHOW_LEVEL' ];
		emit_properties(self.file, obj, road_keys)
		self.last_scale = 0

		general_mode='DRAPED'

		for s in segs:
			if 1 in s.layers or 2 in s.layers or 3 in s.layers:
				if not s in objs and not s in ends and not s in bgns and not s in cars and not s in vrts:
					surf=get_prop(s,'surface','asphalt')
					mesh=s.getData(mesh=True)					
					mm=s.getMatrix('localspace')
					for f in mesh.faces:
						if f.mode & Mesh.FaceModes.TWOSIDE:
							n=len(f.v)
							if n != 4:
								raise ExportError("   found degenerate wires with %d verts in mesh %s." % (n, s.name))
							else:
								v=f.verts
								uv=f.uv
								for idx in range(0,4):										
									max_len = max(max_len,round(v[idx].co[1]))
								
								v0=xform(f.v[0],mm)
								v1=xform(f.v[1],mm)
								v2=xform(f.v[2],mm)
								v3=xform(f.v[3],mm)			
								
								y_min = min(v1[2],v2[2],v3[2],v0[2])
								y_max = max(v1[2],v2[2],v3[2],v0[2])
								x = v1[0]
								self.file.write("WIRE 0 20000\t%f %f %f\n" % ((x - bounds[0]) / rwidth, y_max, 1.0 - y_min / y_max))
						else:
							#if f.image.filename[:2] != '//':
							#	raise ExportError("The image %s is not using a relative path.  It is needed by obj %s." % (f.image.name, obj.name))								
							#if not f.image.has_data:
							#	f.image.reload()
							#if not f.image.has_data:
							#	raise ExportError("The image %s is not loaded - perhaps the texture is misisng; it is needed by obj %s." % (f.image.name, obj.name))
							#(width,height)=f.image.getSize()								
							mat=mesh.materials[f.mat]							
							im = mat.textures[0].tex.image
							if not im.has_data:
								raise ExportError("The image %s is not loaded - perhaps the texture is misisng; it is needed by obj %s." % (im.name, obj.name))
							
							(width,height)=im.getSize()								
							#graded = has_prop(obj,'graded')
							graded = 1
							if f.mode & Mesh.FaceModes.TILES:
								graded = 0
							poly_os = 1
							if graded:
								general_mode='GRADED'
								poly_os = 0
							shader_idx=self.shaders.shader_idx(mesh,f)
							hard_face = f.mode & Mesh.FaceModes.DYNAMIC
							n=len(f.v)
							if n != 4:
								raise ExportError("   found degenerate face with %d verts in mesh %s." % (n, s.name))
							else:
								if width != self.last_scale:
									self.last_scale = width
									self.file.write("SCALE %d\n" % width)
								v=f.verts
								uv=f.uv
								for idx in range(0,4):										
									max_len = max(max_len,round(v[idx].co[1]))

								v0=xform(f.v[0],mm)
								v1=xform(f.v[1],mm)
								v2=xform(f.v[2],mm)
								v3=xform(f.v[3],mm)			
								
								if near_zero(v0[1]) and near_zero(v1[1]):
									out_seg(self.file, name, s.layers, shader_idx,width,hard_face,surf,graded,v0,v1, v2, uv[0],uv[1],uv[2],bounds[0],rlength)
								elif near_zero(v1[1]) and near_zero(v2[1]):
									out_seg(self.file, name, s.layers, shader_idx,width,hard_face,surf,graded,v1,v2, v3, uv[1],uv[2],uv[3],bounds[0],rlength)
								elif near_zero(v2[1]) and near_zero(v3[1]):
									out_seg(self.file, name, s.layers, shader_idx,width,hard_face,surf,graded,v2,v3, v0, uv[2],uv[3],uv[0],bounds[0],rlength)
								elif near_zero(v3[1]) and near_zero(v0[1]):
									out_seg(self.file, name, s.layers, shader_idx,width,hard_face,surf,graded,v3,v0, v1, uv[3],uv[0],uv[1],bounds[0],rlength)
								else:
									# Map merges xyz vert obj and uv tuples into one big mess of pairs, which for with pair
									# iterator then pulls apart.  Python does not do for a,b in x, y: apparently.
									for v, uv in map(None, f.verts, f.uv):
										print v0
										print v1
										print v2
										print v3
										print uv[0], uv[1]
									raise ExportError( "I was not able to pull apart this face (in mesh %s)." % s.name)
								seg_keys = ['SEGMENT_NORMALS']
								emit_properties(self.file, s, seg_keys)


		for o in objs:
			if 1 in o.layers or 2 in o.layers or 3 in o.layers:
				oname = self.lib_lookup(strip_prefix(o.name,'OBJ'))
				if num_lengths < 2:
					raise ExportError( "%s: This distance-baesd object can't be used on a one-span segment: %s." % (obj.name, o.name))
				if out_obj(o, self.file,oname,  "DIST", o.getMatrix('localspace').translationPart(), o.RotX, o.RotY, o.RotZ, num_lengths,rlength,bounds[0]):
					general_mode='GRADED'
		for o in bgns:
			if 1 in o.layers or 2 in o.layers or 3 in o.layers:
				oname = self.lib_lookup(strip_prefix(o.name,'BGN'))
				if out_obj(o, self.file,oname,  "BEGIN", o.getMatrix('localspace').translationPart(), o.RotX, o.RotY, o.RotZ, num_lengths,rlength,bounds[0]):
					general_mode='GRADED'
		for o in ends:
			if 1 in o.layers or 2 in o.layers or 3 in o.layers:
				oname = self.lib_lookup(strip_prefix(o.name,'END'))
				if out_obj(o, self.file,oname, "END", o.getMatrix('localspace').translationPart(), o.RotX, o.RotY, o.RotZ, num_lengths,rlength,bounds[0]):
					general_mode='GRADED'
		for o in vrts:
			if 1 in o.layers or 2 in o.layers or 3 in o.layers:
				oname = self.lib_lookup(strip_prefix(o.name,'VRT'))
				if out_obj(o, self.file,oname, "VERT", o.getMatrix('localspace').translationPart(), o.RotX, o.RotY, o.RotZ, num_lengths,rlength,bounds[0]):
					general_mode='GRADED'
		for o in cars:
			if 1 in o.layers or 2 in o.layers or 3 in o.layers:
				oname = self.lib_lookup(strip_prefix(o.name,'CAR'))
				out_car(o, self.file,oname, o.getMatrix('localspace').translationPart(), o.RotX, o.RotY, o.RotZ)

		o = obj
		while o != None:
			do_macros(self.file,o,0,-bounds[0],rwidth,general_mode)
			o = o.parent

	def export_plug(self, obj, scene):
		if self.debug: print "Exporting plug based on armature obj %s." % obj.name

		plug_keys = ['JUNCTION_DRAPED', 'JUNCTION_GRADED', 'JUNCTION_EMBANKED', 'JUNCTION_BRIDGE',
					'JUNCTION_COMPOSITE_CORNER', 'JUNCTION_COMPOSITE_APPROACH', 'JUNCTION_COMPOSITE_CENTER', 'BEZIER_OFFSET', 'JUNCTION_MINIMA', 'MAX_SHEAR', 'CUTBACK' ];
		self.file.write("# Junction %s.\n" % obj.name)
		emit_properties(self.file, obj, plug_keys)

		degree = 0
		for label in ['JUNCTION_DRAPED', 'JUNCTION_GRADED', 'JUNCTION_EMBANKED', 'JUNCTION_BRIDGE']:
			if has_prop(obj,label):
				degree = int(get_prop(obj,label,'0'))
		if has_prop(obj,'JUNCTION_COMPOSITE_CORNER'): degree = 2
		if has_prop(obj,'JUNCTION_COMPOSITE_APPROACH'): degree = 4
		if has_prop(obj,'JUNCTION_COMPOSITE_CENTER'): degree = 1

		for p in obj.getAllProperties():
			if strip_suffix(p.name.upper()) == 'MATCH':
				mn = get_road_match(p.data)
				if mn == None:
					mn = str(p.data)
				mn_cut = mn.split()
				for i in range(0,len(mn_cut),2):
					if not mn_cut[i] in ['io', 'in', 'out']:
						raise ExportError( "%s: This matching directive is illegal: %s" % (obj.name, mn))
				self.file.write("MATCH %s\n" % mn)

		annotations = getChildren(obj,scene)
		meshes = filter_objects(annotations,'Mesh', '')
		
		meta_rect = [ 0, 0, 10, 10 ];
		for m in meshes:
			if has_prefix(m.name,'META'):
				mesh=m.getData(mesh=True)
				meta_rect[0] = meta_rect[2] = mesh.verts[0].co[0]
				meta_rect[1] = meta_rect[3] = mesh.verts[0].co[1]
				for v in mesh.verts:
					meta_rect[0] = min(meta_rect[0],v.co[0])
					meta_rect[2] = max(meta_rect[2],v.co[0])
					meta_rect[1] = min(meta_rect[1],v.co[1])
					meta_rect[3] = max(meta_rect[3],v.co[1])
	
		if degree < 1:
			raise ExportError( "%s: this junctions degree could not be determined." % obj.name)
		
		
		arm=obj.getData()

		bone_ct=0
		bone_idx=dict()

		annotations = getChildren(obj,scene)
		objs = filter_objects(annotations,'Empty','OBJ')
		
		for bn, bone in arm.bones.items():
			bh = bone.head['ARMATURESPACE']
			bt = bone.tail['ARMATURESPACE']
			if has_prefix(bn,'BEZ'):				
				bone_len = bone_length_to_me(bone)
				self.file.write("BONE_BEZIER %s %f   %f %f %f  %f %f %f\n" % (strip_prefix(bn,'BEZ'), bone_len, bh[0], bh[2], -bh[1], bt[0]-bh[0],bt[2]-bh[2],bh[1]-bt[1]))
			elif has_prefix(bn,'EDG'):
				finger = int(strip_prefix(bn,'EDG'))
				export_edge_bone(self.file,degree, finger, bh[0],bh[1],bh[2], meta_rect)
			elif has_prefix(bn,'APP'):
				if not has_prop(obj,'JUNCTION_COMPOSITE_APPROACH') and not has_prop(obj,'JUNCTION_COMPOSITE_CENTER'):
					raise ExportError( "%s: You cnanot use approach bones except on a composite app or center piece: %s", (obj.name % bn))
				export_app_bone(self.file,bh[0],bh[1],bh[2], meta_rect)
			else:
				export_any_bone(self.file,bn,bh[0],bh[1],bh[2],bt[0]-bh[0],bt[1]-bh[1],bt[2]-bh[2])
			bone_idx[bn]=bone_ct
			bone_ct+=1
		
		vert_list=[]

		shader_idx=-1
		lod_now=-1
		surf_now=None
		up_verts=[]
		vti = []

		for o in meshes:
			if not has_prefix(o.name,'META'):
				mesh=o.getData(mesh=True)

				for f in mesh.faces:

					while len(vti) < len(mesh.verts):
						vti.append([])

					for v, uv in reversed(map(None, f.verts, f.uv)):
						weight_list = mesh.getVertexInfluences(v.index)
						if len(weight_list) == 0: raise ExportError( "ERROR: plug/byt %s  OB %s mesh %s is missing its vertex weighting." % (obj.name, o.name, mesh.name))
						weight_list.sort(key=lambda w: w[1], reverse=True)
						for w in weight_list:
							w[0] = bone_idx[w[0]]
						want_up=False
						if not v in up_verts:
							for e in mesh.edges:
								if (e.flag & Mesh.EdgeFlags.SEAM):
									for vv in e:
										if vv == v:
											want_up = True
											up_verts.append(v)
							
						vt=VT(v.co,v.no,uv,weight_list, want_up)
						#print "checking vert %d against: " % v.index
						#print vti[v.index]
						for j in vti[v.index]:
							if vt.equals(vert_list[j]):
								#print "found it at %d" % j
								break
						else:
							vti[v.index].append(len(vert_list))
							#print "Adding - new list is."
							#print vti[v.index]
							vert_list.append(vt)
		for v in vert_list:
			self.file.write(str(v))

		for o in meshes:
			if not has_prefix(o.name,'META'):
				mesh=o.getData(mesh=True)
				for f in mesh.faces:
					if len(f.verts) != 3 and len(f.verts) != 4:
						raise ExportError( "ERROR: %d verts in face.\n" % len(f.verts))
					else:
						this_idx = self.shaders.shader_idx(mesh, f)
						this_lod = far_lod_from_layers(o.layers)
						this_surf = "none"
						if not (f.mode & Mesh.FaceModes.DYNAMIC):
							this_surf = get_prop(o,'surface','asphalt')
						if this_idx != shader_idx or this_lod != lod_now or this_surf != surf_now:
							self.file.write("JUNC_SHADER %d %d %s\n" % (this_idx, int(this_lod), this_surf ))
						shader_idx = this_idx
						lod_now = this_lod
						surf_now = this_surf
						if len(f.verts) == 3:
							self.file.write("TRI ")
						else:
							self.file.write("QUAD ")
						for v, uv in reversed(map(None, f.verts, f.uv)):
							weight_list = mesh.getVertexInfluences(v.index)
							weight_list.sort(key=lambda w: w[1], reverse=True)
							for w in weight_list:
								w[0] = bone_idx[w[0]]
							vt=VT(v.co,v.no,uv,weight_list, v in up_verts)
							#print "Try to match v %d (%s) against. " % (v.index, str(vt))
							#print vti[v.index]
							for j in vti[v.index]:
								#print " trying %d (%s)." % (j, str(vert_list[j]))
								if vt.equals(vert_list[j]):
									self.file.write(" %d" % j)
									break
							else:
								raise ExportError("ERROR: mesh indexing failed for BYT.")
							
						self.file.write("\n")
						
		for o in objs:
			bn = o.parentbonename
			bidx = bone_idx[bn]
			oname = strip_prefix(o.name,'OBJ')
			oname = get_prop(o,'external', oname)
			draped = not has_prop(o,'graded')
			if oname[-4:] != '.obj':
				oname += '.obj'
			#print oname
			#print "Obj is at: %f, %f, %f" % (o.LocX, o.LocY, o.LocZ)
			#print "Transform:"
			xyz=o.getMatrix('localspace').translationPart()
			self.file.write("JUNC_OBJECT %f %f %f   %f %d  %d 1.0   0 0 0 0 0 0 %s" % (xyz[0], xyz[2], -xyz[1], round(-o.RotZ * 180 / 3.14159265), draped, bidx, oname))
			if has_prop(o,'obj_show_level'):
				self.file.write(" %s" % get_prop(o,'obj_show_level',''))
			self.file.write("\n")
			obj_keys = ['OBJECT_ALT', 'OBJECT_FREQ' ]
			emit_properties(self.file, o, obj_keys)
			
			for p in o.getAllProperties():
				if strip_suffix(p.name.upper()) == 'MACRO':
					self.file.write("%s" % get_macro(p.data))
		
					

		do_macros(self.file,obj,0,0,0,'DRAPED')
	
	
		
	def lib_lookup(self,partial):
		for l in self.lib:
			if l.count(partial):
				return l
		return partial


#------------------------------------------------------------------------
if Window.EditMode(): Window.EditMode(0)
try:
	obj=None
	scene = Blender.Scene.GetCurrent()

	baseFileName=Blender.Get('filename')
	l = baseFileName.lower().rfind('.blend')
	if l==-1: raise ExportError('Save this .blend file first')
	baseFileName=baseFileName[:l]
	obj=RoadExport(baseFileName+'.net')
	obj.export(scene)
	Draw.PupMenu("Road export complete.")

except ExportError, e:
	if e.msg:
		Window.WaitCursor(0)
		Window.DrawProgressBar(0, 'ERROR')
		print "ERROR:\t%s.\n" % e.msg
		Draw.PupMenu("ERROR%%t|%s" % e.msg)
		Window.DrawProgressBar(1, 'ERROR')
except IOError, e:
    Window.WaitCursor(0)
    Window.DrawProgressBar(0, 'ERROR')
    print "ERROR:\t%s\n" % e.strerror
    Draw.PupMenu("ERROR%%t|%s" % e.strerror)
    Window.DrawProgressBar(1, 'ERROR')
    if obj and obj.file: obj.file.close()
