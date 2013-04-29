#!BPY
""" Registration info for Blender menus:
Name: 'X-Plane Facade Export (.fac)'
Blender: 245
Group: 'Export'
Tooltip: 'Export a facade.'
"""
__author__ = "Ben Supnik"
__email__ = "bsupnik at xsquawkbox dot net"
__url__ = "www.x-plane.com"
__version__ = "1.0"
__bpydoc__ = """\
This script exports a facade from a Blender scene.
It is a derived work from Jonathn Harris' original exporter!!
"""

from Blender import Mesh, Group
from XPlaneExport8_util import *
from XPlaneUtils import *
from XPlaneExport import ExportError
from XPlaneLib import *
from XPlaneExport8_util import *


def make_degs(r):
    return round(r * 180.0 / 3.14159265)

#----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

def order_tris(a, b):
    a0=cmp(b[3].dot(a[0])+b[4],0)
    a1=cmp(b[3].dot(a[1])+b[4],0)
    a2=cmp(b[3].dot(a[2])+b[4],0)
    b0=cmp(a[3].dot(b[0])+a[4],0)
    b1=cmp(a[3].dot(b[1])+a[4],0)
    b2=cmp(a[3].dot(b[2])+a[4],0)
    a=a0+a1+a2
    b=b0+b1+b2
    if a == -3:		return 1
    elif a == 3:	return -1
    if b == -3:		return -1
    elif b == 3:	return 1
    if a == -2:		return 1
    elif a == 2:	return -1
    if b == -2:		return -1
    elif b == 2:	return 1
    else:			return 0

class VT:
    def __init__(self, v, no, uv, w):
        self.v = v
        self.no = no
        self.uv = uv
        self.w = w

    # WICKED CHEESY!  Compare string text to avoid failed compare for tiny jitters in FP.
    def equals(self, rhs):
        return str(self) == str(rhs)

    def __cmp__ (self,other):
        return cmp(str(self),str(other))

    def __str__ (self):
        out = "VERTEX %f %f %f\t%f %f %f\t%f %f\t" % (round(self.v[0],3), round(self.v[2],3), round(-self.v[1],3), self.no[0], self.no[2], -self.no[1], self.uv[0], self.uv[1])
        for w in self.w:
            out += " %s %f" % (w[0], w[1])
        out += "\n"
        return out

class Prim:
    def __init__(self, f):
        self.face=f
        self.idx=[]
        self.is_alpha = f.transp == Mesh.FaceTranspModes.ALPHA
        self.geo=[f.v[0].co,f.v[1].co,f.v[2].co]
        n=TriangleNormal(self.geo[0],self.geo[1],self.geo[2])
        self.geo.append(n)
        self.geo.append(-n.dot(self.geo[0]))

    def __cmp__(self, other):
        if self.is_alpha != other.is_alpha:
            if self.is_alpha:
                return 1
            else:
                return -1
        if self.is_alpha:
            return order_tris(other.geo,self.geo)	# back to front order
        else:
            return order_tris(self.geo,other.geo)	# front to back - if opaque, this reduces fill rate!

def xform_fixed(v,x):
    return v.co*x.rotationPart()+x.translationPart()

def xform_no(v,x):
    return v.no*x.rotationPart()

class FacMesh:
    def __init__(self):
        self.idx={}
        self.vlist=[]
        self.faces=[]
        self.idx_count=0

    def add_face(self,f,owner):
        mm=owner.getMatrix('localspace')
        np=Prim(f)
        for v, uv in map(None, f.verts, f.uv):
            if f.smooth:
                vt=VT(xform_fixed(v,mm),xform_no(v,mm),uv,[])
            else:
                vt=VT(xform_fixed(v,mm),xform_no(f,mm),uv,[])
            vts = str(vt)
            if vts in self.idx:
                np.idx.append(self.idx[vts])
            else:
                self.idx[vts] = len(self.vlist)
                np.idx.append(len(self.vlist))
                self.vlist.append(vt)
        if len(f.verts) != 3 and len(f.verts) != 4:
            raise ExportError("Mesh %s has a face that isn't a tri or quad." % owner.name)
        if not (f.mode & Mesh.FaceModes.INVISIBLE):
            if len(f.verts) == 3:	self.idx_count += 3
            else:					self.idx_count += 6
            self.faces.append(np)

    def output(self,fi):
        self.faces.sort()
        for v in self.vlist:
            fi.write("%s" % str(v))
        for f in self.faces:
            if len(f.idx) == 3:
                fi.write("IDX %d %d %d\n" % (f.idx[2], f.idx[1],f.idx[0]))
            else:
                fi.write("IDX %d %d %d %d %d %d\n" % (f.idx[3], f.idx[2],f.idx[1], f.idx[3], f.idx[1],f.idx[0]))

def findgroup(grp_list, ob):
    for group in grp_list[1:]:
        if ob in group.objects:
            return group
    return None


#----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

def find_objs_recursive(who,all,objs):
    if who.getType() == 'Empty' and has_prefix(who.name, 'OBJ'):
        objs.append(who)
    else:
        kids = getChildren(who,all)
        for k in kids:
            find_objs_recursive(k,all,objs)

# Takes our every-obj set and a parent and finds all bitmaps (in roof_imges,wall_images and all
# mesh/obj pairs in roof_objs, wall_objs
def	find_images_recursive(who, all, roof_images,wall_images, roof_objs,wall_objs):
    if who.getType() == 'Mesh':
        if has_prefix(who.name,'ROOF'):
            mesh = who.getData(mesh=True)
            for f in mesh.faces:
                i = f.image
                if not i in roof_images:
                    roof_images.append(i)
            if not (mesh, who) in roof_objs:
                roof_objs.append((mesh, who))
        else:
            mesh = who.getData(mesh=True)
            for f in mesh.faces:
                i = f.image
                if not i in wall_images:
                    wall_images.append(i)
            if not (mesh, who) in wall_objs:
                wall_objs.append((mesh, who))
    children = getChildren(who,all)
    for c in children:
        if not has_prefix(c.name,'OBJ'):
            if not has_prefix(c.name,'SCR'):
                find_images_recursive(c, all, roof_images,wall_images, roof_objs, wall_objs)


#----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# The info is a dictionary of floors by floor name.
# Each floor name is a list of walls.
# Each wall is a list of proeperties and spellings
# Each spelling is a list of ints.
# { 'two_floor': [[0 0 100000 [0 1 2][0 2 3]]] }

def parse_spelling_info(lines, info):
    cur_floor = ''
    for (line_no, line) in enumerate(lines):
        lclean = line.split('#')[0].strip()
        token = lclean.split()
        if len(token) == 0: continue
        if len(token) >= 2 and token[0].upper() == 'FLOOR':
            floor_id=token[1]
            if floor_id in info: raise ExportError("Duplicate floor cmd on line %d: %s" % (line_no, line))
            info[floor_id] = []
            cur_floor = floor_id
        elif len(token) >= 6 and token[0].upper() == 'WALL':
            if not cur_floor in info: raise ExportError("Wall token found but no floor defined, line %d: %s" % (line_no, line))
            info[cur_floor].append([token[5], [token[1], token[2], token[3], token[4]]])
        elif len(token) >= 5 and token[0].upper() == 'WALL_RULE':
            if not cur_floor in info: raise ExportError("Wall token found but no floor defined, line %d: %s" % (line_no, line))
            info[cur_floor][-1][1].append([token[1], token[2], token[3], token[4]])
        elif len(token) >= 2 and token[0].upper() == 'SPELLING':
            if not cur_floor in info: raise ExportError("Spelling token found but no floor defined, line %d: %s" % (line_no, line))
            if len(info[cur_floor]) == 0: raise ExportError("Spelling token found but floor has no walls so far, line %d: %s" % (line_no, line))
            info[cur_floor][-1].append(token[1:])
        else:
            raise ExportError("Unknown text file contents: %s at line %d." % (line, line_no))


#----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

def mesh_cut_info(obj):
    mesh=obj.getData(mesh=True)
    tilt=0
    s_cuts={}
    t_cuts={}
    mm=obj.getMatrix('localspace')
    non_bent_faces = [f for f in mesh.faces if (f.mode & Mesh.FaceModes.TWOSIDE) == 0]
    bent_faces = [f for f in mesh.faces if (f.mode & Mesh.FaceModes.TWOSIDE) != 0]
    vl=[]
    ul=[]
    for f in non_bent_faces:
        vl.extend(f.verts)
        ul.extend(f.uv)
    vts = [xform_fixed(v,mm) for v in vl]
    x_min = min([v[0] for v in vts])
    y_min = min([v[1] for v in vts])
    z_min = min([v[2] for v in vts])
    x_max = max([v[0] for v in vts])
    y_max = max([v[1] for v in vts])
    z_max = max([v[2] for v in vts])
    s_min = min([u[0] for u in ul])
    t_min = min([u[1] for u in ul])
    s_max = max([u[0] for u in ul])
    t_max = max([u[1] for u in ul])

    for f in non_bent_faces:
        (w,h) = f.image.getSize()
        s1 = min([round(u[0]*w,1) for u in f.uv])
        t1 = min([round(u[1]*h,1) for u in f.uv])
        s2 = max([round(u[0]*w,1) for u in f.uv])
        t2 = max([round(u[1]*h,1) for u in f.uv])
        if (f.mode & Mesh.FaceModes.TILES) == 0:
            s_cuts[s1]=0
            t_cuts[t1]=0
        if not s1 in s_cuts: s_cuts[s1]=1
        if not s2 in s_cuts: s_cuts[s2]=1
        if not t1 in t_cuts: t_cuts[t1]=1
        if not t2 in t_cuts: t_cuts[t2]=1

    sl =s_cuts.keys()
    tl =t_cuts.keys()
    sl.sort()
    tl.sort()

    if len(bent_faces) > 0:
        by_z={}
        for f in bent_faces:
            (w,h) = f.image.getSize()
            for v,uv in map(None,f.verts,f.uv):
                by_z[v.co[2]]=(v,(round(uv[0]*w),round(uv[1]*h)))
        bottom_z = min(by_z.keys())
        top_z = max(by_z.keys())
        bottom_t = by_z[bottom_z][1][1]
        top_t = by_z[top_z][1][1]

        if not top_t in t_cuts:
            t_cuts[top_t] = 1
        tl.append(top_t)

    return (x_max-x_min,y_max-y_min,z_max-z_min,[x for x in sl],[y for y in tl],[s_cuts[k] for k in sl],[t_cuts[k] for k in tl], w, h,s_max-s_min,t_max-t_min, z_min)

#----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

def zone_filter_match(zone, filter_list):
    if len(filter_list) == 0:
        return True
    for f in filter_list:
        if zone.find(f) != -1:
            return True
    return False

def toupper(s):
    return s.upper()

def export_all(objs,path):
    kids=getChildren(None, objs)
    facs = filter_objects(kids,'Empty','FAC')

    for f in facs:
        export_fac(f, objs,path)

def export_fac(fac, all, dir):
    print "Exporting %s " % fac.name

    text = text_for_obj(fac.name)
    info={}
    if len(text) != 0:
        parse_spelling_info(text, info)

    fname = strip_prefix(fac.name,'FAC') + '.fac'

    partial = get_prop(fac,'path','.')

    prefix = ''
    parts = partial.count('/') + 1
    if partial == '.': parts = 0
    for n in range(parts):
        prefix += '../'


    export_path=os.path.join(partial,fname)
    export_path=os.path.join(path,export_path)
    if not os.path.exists(os.path.dirname(export_path)):
        os.makedirs(os.path.dirname(export_path))

    print export_path
    fi = open(export_path,'w')
    if len(text) > 0:
        fi.write("A\n1000\nFACADE\n\n")
    else:
        fi.write("A\n800\nFACADE\n\n")
    fac_props=[]
    is_graded=0
    fac_keys=['RING', 'HARD_WALL','HARD_ROOF','DOUBLED', 'FLOORS_MIN', 'FLOORS_MAX', 'LAYER_GROUP', 'LAYER_GROUP_DRAPED' ]
    accum_properties(fac,fac_keys,fac_props)
    for p in fac_props:
        fi.write("%s\n" % p)
    if has_prop(fac,'GRADED'):		# avoid using prop data in file
        fi.write("GRADED\n")
        is_graded=1
    if has_prop(fac,'vname'):
        (sim,pack)=locate_root(export_path)
        fi.write("EXPORT %s.fac %s\n" % (strip_suffix(get_prop(fac,'vname',fac.name)),os.path.normpath(export_path[len(pack)+1:])))


    zoning_types = [ 'ind_high_solid', 'ind_low_solid', 'urban_med_solid', 'urban_com_solid' ]
    tall_zoning_types = [ 'urban_high_solid' ]

    block_widths = [	7.5,	15,		22.5,   30,		45,		60,		75,		90 ]
    arch_heights = [	24, 32, 999 ]
    height_max_for_arch = { 24:24, 32:40, 999:999 }
    block_heights = [	[8,10],		[10,16],		[16,24],		[24,32],		[32,40],		[40,80],		[80,120],	[120,999] ]
    legal_block_heights = [ 8,10,16,24,32,40,80,120,999]
    block_depths = [ 30, 60, 90 ]

    num_fac_spelling_props=0
    for p in [ 'WIDTH_MIN', 'WIDTH_MAX', 'HEIGHT_MIN', 'HEIGHT_MAX', 'DEPTH', 'BLOCK_HEIGHT', 'BLOCK_VARIANT' ]:
        if has_prop(fac,p):
            num_fac_spelling_props = num_fac_spelling_props + 1

    if num_fac_spelling_props != 0 and num_fac_spelling_props != 7:
        raise ExportError("You only have some facade tags placed.  Typo?  %s" % fac.name)

    if num_fac_spelling_props == 7:
        (sim,pack)=locate_root(export_path)
        width_min = float(get_prop(fac,'WIDTH_MIN',0))
        width_max = float(get_prop(fac,'WIDTH_MAX',0))
        height_min = float(get_prop(fac,'HEIGHT_MIN',0))
        height_max = float(get_prop(fac,'HEIGHT_MAX',0))
        depth = get_prop(fac,'DEPTH','')
        arch_height = get_prop(fac,'BLOCK_HEIGHT','')
        # Alex hack alert: I've made it accept either commas or whitespace as separators, by the only method I could find - I apologise for the mess.
        if ',' in depth:
            depth_list = map(float,depth.split(','))
        else:
            depth_list = map(float,depth.split())
        if ',' in arch_height:
            arch_list = map(float,arch_height.split(','))
        else:
            arch_list = map(float,arch_height.split())
        if ',' in get_prop(fac,'BLOCK_VARIANT',''):
            var_list = map(toupper,get_prop(fac,'BLOCK_VARIANT','').split(','))
        else:
            var_list = map(toupper,get_prop(fac,'BLOCK_VARIANT','').split())
        zone_filter = get_prop(fac,'ZONE','')
        if zone_filter=='':
            zone_filter=[]
        else:
            if ',' in zone_filter:
                zone_filter = zone_filter.split(',')
            else:
                zone_filter = zone_filter.split()
        fallback = get_prop(fac,'FALLBACK','')
        if fallback == '1':
            fallback = '_FALLBACK'
        else:
            fallback = '_PRIMARY'
        density = get_prop(fac,'DENSITY','1.0')

        my_exp= os.path.normpath(export_path[len(pack)+1:])

        num_exp=0

        for d in block_depths:
            if float(d) in depth_list:
                for w in block_widths:
                    if w >= width_min and w <= width_max:
                        for z in zoning_types:
                            if zone_filter_match(z,zone_filter):
                                # ALEX - comment this back in to raise an error if a facade is too tall for the low zoning types but
                                # is hitting one of their buckets anyway.  When you put FLOORS_MIN in place this check shuts up, because
                                # you have FORCED the building to be tall enough to be non-silly even though the DSF says "10 meters, really!"
                                #if height_min > 10.0 and not has_prop(fac,'FLOORS_MIN'):
                                #	raise ExportError("The facade %s matches the non-tall zoning type %s.\nIt has no minimum floor directive but needs to be taller than 10m." % (fac.name, z))
                                if 'A' in var_list:
                                    fi.write("EXPORT%s %s lib/g10/autogen/%s_%dx%da.fac\t\t%s\n" % (fallback, density, z,w,d,my_exp))
                                    num_exp=num_exp+1
                                if 'B' in var_list:
                                    fi.write("EXPORT%s %s lib/g10/autogen/%s_%dx%db.fac\t\t%s\n" % (fallback, density, z,w,d,my_exp))
                                    num_exp=num_exp+1

                        for z in tall_zoning_types:
                            if zone_filter_match(z,zone_filter):
                                for bh in block_heights:
                                    if bh[0] >= height_min and bh[1] <= height_max:
                                        for ah in arch_heights:
                                            if float(ah) in arch_list and bh[1] <= height_max_for_arch[float(ah)]:
                                                #ALEX - comment these lines back in to fail export if the min/max height don't fall on bucket
                                                # boundaries.
                                                #if not height_min in legal_block_heights:
                                                #	raise ExportError("The facade %s has an illegal height min %f." % (fac.name, height_min))
                                                #if not height_max in legal_block_heights:
                                                #	raise ExportError("The facade %s has an illegal height max %f." % (fac.name, height_max))
                                                if 'A' in var_list:
                                                    fi.write("EXPORT%s %s lib/g10/autogen/%s_%d_%dx%dx%da.fac\t\t%s\n" % (fallback, density, z,ah,w,bh[1],d,my_exp))
                                                    num_exp=num_exp+1
                                                if 'B' in var_list:
                                                    fi.write("EXPORT%s %s lib/g10/autogen/%s_%d_%dx%dx%db.fac\t\t%s\n" % (fallback, density, z,ah,w,bh[1],d,my_exp))
                                                    num_exp=num_exp+1

        # This checks that we put at least ONE generated export directive in.  If we have none, that's probably a typo.
        if num_exp==0:
            raise ExportError("The facade %s has export bucketing tags but failed to fit in ANY bucket.  This is probably a tagging mistake." % fac.name)

    roof_images=[]
    wall_images=[]
    roof_meshes=[]
    wall_meshes=[]
    objs=[]

    find_objs_recursive(fac,all,objs)
    find_images_recursive(fac, all, roof_images,wall_images, roof_meshes,wall_meshes)
    if len(roof_images) > 1: raise ExportError("We found %d roof images." % len(roof_images))
    if len(wall_images) > 1: raise ExportError("We found %d wall images." % len(wall_images))

    # Ben says: disable this for now - we do want a roof with draped walls for fence around a draped parking lot (roof height = 0)
    #if len(roof_images) > 0 and not is_graded: raise ExportError("You cannot use a roof in a draped facade!")

    shader_keys=['TWO_SIDED','NO_BLEND', 'SPECULAR', 'BUMP_LEVEL', 'NO_SHADOW',
                'DECAL', 'DECAL_RGBA', 'DECAL_KEYED', 'DECAL_PARAMS', 'DECAL_PARAMS_PROJ','TEXTURE_DETAIL','NO_ALPHA','DITHERED_ALPHA','DECAL_LIB']


    if len(wall_images) > 0:
        wt = blender_relative_path(wall_images[0].getFilename())
        fi.write("SHADER_WALL\n")
        fi.write("TEXTURE %s\n" % (prefix + wt))
        core = get_core_texture(wt)
        if tex_exists(core+"_NML.png"): fi.write("TEXTURE_NORMAL 1.0 %s_NML.png\n" % (prefix+core))
        elif tex_exists(core+"_NML.dds"): fi.write("TEXTURE_NORMAL 1.0 %s_NML.dds\n" % (prefix+core))
        if tex_exists(core+"_LIT.png"): fi.write("TEXTURE_LIT %s_LIT.png\n" % (prefix+core))
        elif tex_exists(core+"_LITL.dds"): fi.write("TEXTURE_LIT %s_LIT.dds\n" % (prefix+core))

        shader_props=[]
        accum_properties(fac,shader_keys,shader_props)
        for p in shader_props:
            fi.write("%s\n" % p)

    if len(roof_images) > 0:
        fi.write("SHADER_ROOF\n")
        rt = blender_relative_path(roof_images[0].getFilename())
        fi.write("TEXTURE %s\n" % (prefix + rt))
        core = get_core_texture(rt)
        if tex_exists(core+"_NML.png"): fi.write("TEXTURE_NORMAL 1.0 %s_NML.png\n" % (prefix+core))
        elif tex_exists(core+"_NML.dds"): fi.write("TEXTURE_NORMAL 1.0 %s_NML.dds\n" % (prefix+core))
        if tex_exists(core+"_LIT.png"): fi.write("TEXTURE_LIT %s_LIT.png\n" % (prefix+core))
        elif tex_exists(core+"_LIT.dds"): fi.write("TEXTURE_LIT %s_LIT.dds\n" % (prefix+core))

        roof_empty=fac
        for o in all:
            if o.parent == fac and toupper(strip_suffix(o.name)) == 'ROOF_PROPS':
                roof_empty=o
        shader_props=[]
        accum_properties(roof_empty,shader_keys,shader_props)
        for p in shader_props:
            fi.write("%s\n" % p)

    if len(text) > 0 and len(roof_images):
        if len(roof_meshes) == 0: raise ExportError("Internal error - we found a roof image but no roof mesh!")
        x_min = y_min = s_min = t_min = 9999
        x_max = y_max = s_max = t_max = -9999
        mm=roof_meshes[0][1].getMatrix('localspace')
        for f in roof_meshes[0][0].faces:
            for v in f.verts:
                vv = xform_fixed(v,mm)
                x_min = min(x_min,vv[0])
                x_max = max(x_max,vv[0])
                y_min = min(y_min,vv[1])
                y_max = max(y_max,vv[1])
            for v in f.uv:
                s_min = min(s_min, v[0])
                s_max = max(s_max, v[0])
                t_min = min(s_min, v[1])
                t_max = max(s_max, v[1])
        fi.write("ROOF_SCALE %f %f\n\n" % ((x_max - x_min) / (s_max - s_min),(y_max - y_min) / (t_max - t_min)))

    obj_idx={}
    for o in objs:
        if not has_prop(o,'external'): raise ExportError("Object %s has no external property." % o.name)
        k = get_prop(o,'external',o.name)
        if not k in obj_idx:
            il = len(obj_idx)
            fi.write("OBJ %s\n" % k)
            obj_idx[k] = il

    floors = getChildren(fac, all)
    floors.sort(lambda x,y: cmp(x.name.lower(), y.name.lower()))
    for f in floors:
        if has_prefix(f.name,'LOD'):
            export_lod(f,all, fi)
        elif has_prefix(f.name,'SCR'):
            export_scraper(f,all,fi,os.path.join(dir,partial),prefix)
        elif not toupper(strip_suffix(f.name)) == 'ROOF_PROPS':
            if not strip_suffix(f.name) in info: raise ExportError("Floor %s is not defined in the text file." % f.name)
            export_floor(f, all, fi, info[strip_suffix(f.name)], obj_idx, objs)

    fi.close()

def export_floor(obj, all, fi, info, obj_idx, objs):
    fi.write("\nFLOOR %s\n" % obj.name)
    kids = getChildren(obj, all)
    roofs = filter_objects(kids,'Mesh','ROOF')
    segs = filter_objects(kids,'Empty','SEG')
    crvs = filter_objects(kids,'Empty','CRV')

    #------- EXTRACT ROOF HEIGHTS FROM ALL ROOF OBJECTS -------
    all_roofs=[]
    for r in roofs:
        max_height=0
        mm=r.getMatrix('localspace')
        mesh=r.getData(mesh=True)
        two_sided=0
        x_min=9999
        y_min=9999
        for f in mesh.faces:
            for i in [0,1,2]:
                vv = xform_fixed(f.v[i],mm)
                max_height=max(vv[2],max_height)
                x_min=min(x_min,f.v[i].co[0])
                y_min=min(y_min,f.v[i].co[1])
            if f.mode & Mesh.FaceModes.TWOSIDE:
                two_sided=1
        all_roofs.append([r, max_height, two_sided, x_min, y_min])

    all_roofs.sort(lambda x,y: cmp(x[1],y[1]))

    for rr in all_roofs:
        r = rr[0]
        roof_h=[]
        mm=r.getMatrix('localspace')
        mesh=r.getData(mesh=True)
        for f in mesh.faces:
            vv = xform_fixed(f.v[0],mm)
            if not vv[2] in roof_h:
                roof_h.append(vv[2])
        if len(roof_h) > 0:
            roof_h.sort()
            fi.write("ROOF_HEIGHT")
            for h in roof_h:
                fi.write(" %f" % round(h,3))
            fi.write("\n")
            if rr[2] and rr[1] != 0.0:
                fi.write("TWO_SIDED_ROOF\n");
            for o in objs:
                if o.parent == r:
                    oi = obj_idx[get_prop(o,'external',o.name)]
                    loc=o.getMatrix('localspace').translationPart()
                    fi.write("ROOF_OBJ_HEADING %d %f %f %f" % (oi, loc[0] - rr[3], loc[1] - rr[4], make_degs(-o.RotZ)))
                    if has_prop(o,'show_level'):
                        fi.write(" %s" % get_prop(o,'show_level',''))
                    fi.write("\n")


    seg_map={}
    crv_map={}
    for s in segs:
        i=int(strip_prefix(s.name,'SEG'))
        if i in seg_map: raise ExportError("The segment %s re-uses a segment index number." % s.name)
        seg_map[i] = s
    for s in crvs:
        i=int(strip_prefix(s.name,'CRV'))
        if i in crv_map: raise ExportError("The curved segment %s re-uses a segment index number." % s.name)
        crv_map[i] = s

    for i in xrange(len(segs)):
        if not i in seg_map: raise ExportError("The floor %s is missing a segment, index number %d." % (obj.name, i))
        export_wall2(seg_map[i], all, fi, obj_idx)

    for i in xrange(len(crvs)):
        if not i in crv_map: raise ExportError("The floor %s is missing a curved segment, index number %d." % (obj.name, i))
        export_wall2(crv_map[i], all, fi, obj_idx)

    if len(info) == 0: raise ExportError("There are no walls defined for floor %s" % (obj.name))

    if len(seg_map) != len(crv_map): raise ExportError("There are a different number of curved and flat segments. %d curved, %d flat." % (len(crv_map), len(seg_map)))

    for w in info:
        fi.write("WALL %s %s %s %s %s\n" % (w[1][0], w[1][1], w[1][2], w[1][3], w[0]))
        if len(w) == 2: raise ExportError("There are no spellings defined for a wall in %s." % (obj.name))
        for r in w[1][4:]:
            fi.write("WALL_RULE %s %s %s %s\n" % (r[0],r[1],r[2],r[3]))
        for s in w[2:]:
            fi.write("SPELLING")
            for ss in s:
                idx = int(ss)
                if idx < 0 or idx >= len(segs): raise ExportError("Wall %s %s %s has a spelling with index %d that is out of range." % (w[0],w[1],w[2], idx))
                fi.write(" %s" % ss)
            fi.write("\n")

def export_wall2(wall, all, fi, obj_idx):
    kids = getChildren(wall, all)
    if has_prefix(wall.name,'SEG'):
        fi.write("SEGMENT %s\n" % strip_prefix(wall.name,'SEG'))
    else:
        fi.write("SEGMENT_CURVED %s\n" % strip_prefix(wall.name,'CRV'))
    grp_list = Group.Get()
    grp_list.sort(lambda x,y: cmp(x.name.lower(), y.name.lower()))
    grp_list.insert(0,None)
    for layer, lod in [[1,5000], [2,20000]]:
        for gi, g in enumerate(grp_list):
            my_kids=[]
            for k in kids:
                if layer in k.layers:
                    if findgroup(grp_list,k) == g:
                        if k.getType() == 'Mesh':
                            my_kids.append(k)
            if len(my_kids) > 0:
                out_mesh=FacMesh()
                for k in my_kids:
                    mesh=k.getData(mesh=True)
                    if k.getType()!='Mesh' or k.modifiers:
                        mesh=Mesh.New()
                        mesh.getFromObject(k)

                    for f in mesh.faces:
                        out_mesh.add_face(f,k)
                divs = 4
                if has_prefix(wall.name,'SEG'): divs = 1
                divs = int(float(get_prop(wall,'divs',divs)))
                fi.write("MESH %d %f %d %d %d\n" % (gi, lod, divs, len(out_mesh.vlist), out_mesh.idx_count))
                out_mesh.output(fi)
                fi.write("\n")
    for k in kids:
        if k.getType() == 'Empty' and has_prefix(k.name,'OBJ'):
            ki = obj_idx[get_prop(k,'external',k.name)]
            loc=k.getMatrix('localspace').translationPart()

            if has_close_prop(k,['GRADED','DRAPED']) == 'GRADED':
                fi.write("ATTACH_GRADED %d %f %f %f %f" % (ki, loc[0], loc[2], -loc[1], make_degs(-k.RotZ)))
            else:
                fi.write("ATTACH_DRAPED %d %f %f %f %f" % (ki, loc[0], loc[2], -loc[1], make_degs(-k.RotZ)))
            if has_prop(k,'show_level'):
                fi.write(" %s" % get_prop(k,'show_level',''))
            fi.write("\n");

def export_lod(lod,all,fi):
    fi.write("LOD %s\n" % get_prop(lod,'LOD',strip_prefix(lod.name,'LOD')))
    kids = getChildren(lod,all)
    kids.sort(lambda x,y: cmp(x.name.lower(), y.name.lower()))
    for k in kids:
        mi = mesh_cut_info(k)
        has_lrbt=0
        if has_prop(k, 'lrbt'):
            has_lrbt=1
            lrbt_string=get_prop(k,'lrbt','')
            if ',' in lrbt_string:
                lrbt_strings=lrbt_string.split(',')
            else:
                lrbt_strings=lrbt_string.split()
            if len(lrbt_strings) != 4:
                raise ExportError("LOD object %s has mal-formed lrbt property %s" % (k.name, lrbt_string))
            lrbt=[			float(lrbt_strings[0]),			float(lrbt_strings[1]),			float(lrbt_strings[2]),			float(lrbt_strings[3])]
            total_h = len(mi[3])-1
            total_v = len(mi[4])-1
            if (lrbt[0]+lrbt[1]) > total_h:
                raise ExportError("Facade %s has %d left, %d right, but only %d total h panels." % (k.name,lrbt[0],lrbt[1],total_h))
            if (lrbt[2]+lrbt[3]) > total_v:
                raise ExportError("Facade %s has %d bottom, %d top, but only %d total v panels." % (k.name,lrbt[2],lrbt[3],total_v))
            if has_prop(k,'ROOF_SLOPE') and lrbt[3] < 1:
                raise ExportError("Facade %s has roof slope but no top layers. Check lrbt property!" % k.name)
        #print "bounds: %f,%f,%f  tex: %f,%f  uv bounds: %f,%f depth %f" % (mi[0],mi[1],mi[2],mi[7],mi[8],mi[9],mi[10], mi[11])
        fi.write("TEX_SIZE %f %f\n" % (mi[7], mi[8]))
        if has_prefix(k.name,'WALL'):
            fi.write("WALL %s\n" % get_prop(k,'WALL',strip_prefix(k.name,'WALL')))
            if has_prop(k,'WALL_RULE'):
                fi.write("WALL_RULE %s\n" % get_prop(k,'WALL_RULE',''))
            if has_prop(k,'ROOF_SLOPE'):
                if has_prop(k,'SLANT') and get_prop(k,'SLANT','1') == '0':
                    fi.write("ROOF_SLOPE %s\n" % get_prop(k,'ROOF_SLOPE','0'))
                else:
                    fi.write("ROOF_SLOPE %s SLANT\n" % get_prop(k,'ROOF_SLOPE','0'))
            s_range = mi[9]
            t_range = mi[10]
            fi.write("SCALE %f %f\n" % (mi[0] / s_range, mi[2] / t_range))
            if mi[11] < 0.0:
                fi.write("BASEMENT_DEPTH %f\n" % (-mi[11] * mi[8] * mi[10] / mi[2]))
            cuts=['LEFT','CENTER','RIGHT']
            idx=0
            if sum(mi[5]) == 1:
                idx = 1
            for n in xrange(1,len(mi[3])):
                nn=n-1
                if has_lrbt:
                    idx=1
                    if nn < lrbt[0]: idx=0
                    if nn >= (total_h-lrbt[1]): idx = 2
                fi.write("%s %f %f\n" % (cuts[idx], mi[3][nn],mi[3][n]))
                if mi[5][n] != mi[5][nn]:
                    idx=idx+1
            cuts=['BOTTOM','MIDDLE','TOP']
            idx=0
            for n in xrange(1,len(mi[4])):
                nn=n-1
                if has_prop(k,'ROOF_SLOPE'):
                    if n == (len(mi[4])-1):
                        idx=2
                if has_lrbt:
                    idx=1
                    if nn < lrbt[2]: idx=0
                    if nn >= (total_v-lrbt[3]): idx = 2
                fi.write("%s %f %f\n" % (cuts[idx], mi[4][nn],mi[4][n]))
                if mi[6][n] != mi[6][nn]:
                    idx=idx+1
        else:
            if len(mi[3]) != 3 or len(mi[4]) != 3: raise ExportError("Roof is not cut into four quads.")
            fi.write("ROOF_SCALE %f %f %f %f %f %f %f %f\n" % (mi[3][0],mi[4][0],mi[3][1],mi[4][1],mi[3][2],mi[4][2],mi[0],mi[1]))


def export_scraper(obj,all,fi,dir,prefix):
    if not has_prop(obj,'STEP'): raise ExportError("Object %s does not have a step property." % obj.name)
    if not has_prop(obj,'FLOORS'): raise ExportError("Object %s does not have a floors property." % obj.name)
    pairs=getChildren(obj,all)
    pairs.sort(lambda x,y: cmp(x.name.lower(), y.name.lower()))
    model_pairs=[]
    delta_agl=0
    agl_span=0
    for p in pairs:
        kids = getChildren(p,all)
        base=None
        tower=None
        pad=None
        pins=[]
        for k in kids:
            if has_prefix(k.name,'BASE'):
                if base != None: raise ExportError("There are two bases in this scraper: %s and %s." % (k.name, base.name))
                base = k
            elif has_prefix(k.name,'TWR'):
                if tower != None: raise ExportError("There are two towers in this scraper: %s and %s." % (k.name, tower.name))
                tower = k
            elif has_prefix(k.name,'PAD'):
                if pad != None: raise ExportError("There are two pads in this scraper: %s and %s." % (k.name, pad.name))
                pad = k
            elif has_prefix(k.name,'PIN'):
                ploc=k.getMatrix('localspace').translationPart()
                pins.append(ploc[0])
                pins.append(ploc[1])
        if base == None: raise ExportError("There is no base in the scaper %s." % obj.name)
        if tower == None and pad != None: raise ExportError("You cannot use a pad without a tower in %s." % obj.name)
        #if tower == None: raise ExportError("There is no tower in the scaper %s." % obj.name)
        delta_agl = 0
        delta_pad = 0
        base_x = 0
        base_z = 0
        base_r = 0
        tower_x = 0
        tower_z = 0
        tower_r = 0
        pad_x = 0
        pad_z = 0
        pad_r = 0
        # basen = name of obj, basep = fully qualified path to export, basek = all real children of obj, basel = library path or None if non-lib.
        basen = get_prop(base,'rname',strip_prefix(base.name,'BASE'))+'.obj'
        basep = dir+'/' + basen
        basek = getGrandChildren(base,all)
        basel = None
        bases = get_prop(base,'show_level','1 1')
        if has_prop(base,'external'):
            basel = get_prop(base,'external',None)

        if tower != None:
            towern = get_prop(tower,'rname',strip_prefix(tower.name,'TWR'))+'.obj'
            towerp = dir+'/' + towern
            towerk = getGrandChildren(tower,all)
            towerl = None
            if has_prop(tower,'external'):
                towerl = get_prop(tower,'external',None)
            towers = get_prop(tower,'show_level','1 1')
        else:
            towern = ""
            towerp = ""
            towerk = []
            towerl = None
            towers = '1 1'
        if pad != None:
            padn = get_prop(pad,'rname',strip_prefix(pad.name,'PAD'))+'.obj'
            padp = dir+'/' + padn
            padk = getGrandChildren(pad,all)
            padl = None
            if has_prop(pad,'external'):
                padl = get_prop(pad,'external',None)
            pads = get_prop(pad,'show_level','1 1')
        else:
            padn = ""
            padp = ""
            padk = []
            padl = None
            pads = '1 1'

        base_x = base.getMatrix('localspace').translationPart()[0]
        base_z = -base.getMatrix('localspace').translationPart()[1]
        base_r = make_degs(-base.RotZ)

        #print basen, towern
        #print basep, towerp
        #print basek, towerk
        if basel == None:
            exp_base = OBJexport8(basep)
            exp_base.additive_lod=1
            exp_base.us_mat=0
            exp_base.openFile(basek,base,prefix)
            exp_base.writeHeader()
            exp_base.writeObjects(basek)

        if tower != None:
            delta_agl = tower.getMatrix('localspace').translationPart()[2]
            tower_x = tower.getMatrix('localspace').translationPart()[0]
            tower_z = -tower.getMatrix('localspace').translationPart()[1]
            tower_r = make_degs(-tower.RotZ)
            if towerl == None:
                exp_tower = OBJexport8(towerp)
                exp_tower.additive_lod=1
                exp_tower.us_mat=0
                exp_tower.openFile(towerk,tower,prefix)
                exp_tower.writeHeader()
                exp_tower.writeObjects(towerk)

            if pad != None:
                delta_pad = pad.getMatrix('localspace').translationPart()[2] - tower.getMatrix('localspace').translationPart()[2]
                pad_x = pad.getMatrix('localspace').translationPart()[0]
                pad_z = -pad.getMatrix('localspace').translationPart()[1]
                pad_r = make_degs(-pad.RotZ)
                if padl == None:
                    exp_pad = OBJexport8(padp)
                    exp_pad.additive_lod=1
                    exp_pad.us_mat=0
                    exp_pad.openFile(padk,pad,prefix)
                    exp_pad.writeHeader()
                    exp_pad.writeObjects(padk)

        agl_span=0
        for o in towerk:
            mm=o.getMatrix('localspace')
            if o.getType()=='Mesh':
                mesh=o.getData(mesh=True)
                for v in mesh.verts:
                    vt=xform_fixed(v,mm)
                    agl_span = max(vt[2],agl_span)
        if len(towerk) == 0:
            # fallback case - no tower, take HEIGHT_MIN/MAX TAGS
            height_min = float(get_prop(obj,'HEIGHT_MIN',0))
            height_max = float(get_prop(obj,'HEIGHT_MAX',0))
            agl_span=height_min
            delta_agl=height_max-height_min

        if basel != None:			basen = basel
        if padl != None:			padn = padl
        if towerl != None:			towern = towerl

        model_pairs.append([[basen,base_x,base_z,base_r,bases],[towern,tower_x,tower_z,tower_r, towers],[padn,pad_x,delta_pad,pad_z,pad_r, pads],pins])

    fi.write("FACADE_SCRAPER %f %f %s %s\n" % (agl_span, agl_span + delta_agl, get_prop(obj,'STEP','4'), get_prop(obj,'FLOORS','2')))
    for m in model_pairs:
        print m
        fi.write("FACADE_SCRAPER_MODEL_OFFSET %f %f %f %s %s" % (m[0][1],m[0][2],m[0][3],m[0][0],m[0][4]))

        if m[1][0] == "":
            fi.write(" 0 0 0 - 1 1 ")
        else:
            fi.write(" %f %f %f %s %s " % (m[1][1],m[1][2],m[1][3],m[1][0],m[1][4]))
        for p in m[3]:
            fi.write(" %f" % -p)
        fi.write("\n")
        if m[2][0] != "":
            fi.write("FACADE_SCRAPER_PAD %f %f %f %f %s %s\n" % (m[2][1],m[2][2],m[2][3],m[2][4], m[2][0], m[2][5]))


#------------------------------------------------------------------------
if Window.EditMode(): Window.EditMode(0)
try:
    obj=None
    sl = Blender.Scene.Get()

    scene = Blender.Scene.GetCurrent()

    baseFileName=Blender.Get('filename')
    l = baseFileName.lower().rfind('.blend')
    if l==-1: raise ExportError('Save this .blend file first')
    path=os.path.dirname(baseFileName)

    export_all(scene.objects,path)

    Draw.PupMenu("Facade export complete.")

except ExportError, e:
    for o in scene.objects: o.select(0)
    if e.objs:
        layers=[]
        if isinstance(e.objs, tuple):
            (o,mesh,faces)=e.objs
            o.select(1)
            layers=o.layers
            for f in mesh.faces: f.sel=0
            if faces:
                for f in faces: f.sel=1
                for i in range(len(mesh.faces)):
                    if mesh.faces[i]==faces[0]:
                        mesh.activeFace=i
                        break
        else:
            for o in e.objs:
                o.select(1)
                for layer in o.layers:
                    if (layer<=3 or not o.Layers&7) and not layer in layers:
                        layers.append(layer)
        Window.ViewLayers(layers)
        Window.RedrawAll()
    if e.msg:
        Window.WaitCursor(0)
        Window.DrawProgressBar(0, 'ERROR')
        print "ERROR:\t%s.\n" % e.msg
        Draw.PupMenu("ERROR%%t|%s" % e.msg)
        Window.DrawProgressBar(1, 'ERROR')
    if obj and obj.file: obj.file.close()
except IOError, e:
    Window.WaitCursor(0)
    Window.DrawProgressBar(0, 'ERROR')
    print "ERROR:\t%s\n" % e.strerror
    Draw.PupMenu("ERROR%%t|%s" % e.strerror)
    Window.DrawProgressBar(1, 'ERROR')
    if obj and obj.file: obj.file.close()
