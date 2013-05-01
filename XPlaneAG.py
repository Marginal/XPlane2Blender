#!BPY
""" Registration info for Blender menus:
Name: 'X-Plane AG (.agp)'
Blender: 249
Group: 'Export'
Tooltip: 'Export X-Plane autogen block'
"""
__author__ = "Ben Supnik"
__email__ = "Ben Supnik, Ben Supnik <bsupnik:xsquawkbox*net>"
__url__ = "developer.x-plane.com"
__version__ = "3.11"
__bpydoc__ = """\
This script exports X-Plane autogen blocks.
"""

#
# Copyright (c) 2012-2013 Ben Supnik
#
# This code is licensed under version 2 of the GNU General Public License.
# http://www.gnu.org/licenses/gpl-2.0.html
#
# See ReadMe-XPlane2Blender.html for usage.
#

# COORDINATE SYSTEM NOTE: we always use the local transform from annotations to the parent "entity level" block (E.g. tile_1).
# The advantage of this is that we can simply 'pull' the transforms on OBJs and trees directly from the euler/translation of their blocks.
# The disadvantage is that if there is a scale on the outer entity/file blocks, it is not applied...thus Alex MUST use scale=1 on these outer
# blocks to get something sane.
# If we were to use 'world space' transforms we'd have to apply the world space transform to the origin for all point objects, and frankly I'm not
# sure how we'd cope with rotations.


import sys
import math
import os
import Blender
from Blender import Armature, Mesh, Lamp, Image, Draw, Window
from Blender.Mathutils import Matrix, RotationMatrix, TranslationMatrix, MatMultVec, Vector, Quaternion, Euler
from XPlaneExport8_util import *
from XPlaneExport import getTexture, ExportError
from XPlaneUtils import *
from XPlaneMacros import *

def_lib_root="lib/g10"

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

def make_degs(r):
    return round(r * 180.0 / 3.14159265)

def near_zero(x):
    return x > -0.1 and x < 0.1

def interp(x1, y1, x2, y2, x):
    if x < x1:	return y1
    if x > x2:	return y2
    if y1 == y2:
        return (x1 + x2) * 0.5
    else:
        return y1 + (y2-y1) * (x-x1) / (x2-x1)

def face_has_vert_index(f,i):
    for v in f.v:
        if i == v.index:
            return True
    return False

def require_dir(parent,name):
    fpath=os.path.join(parent,name)
    if not os.path.exists(fpath):
        os.makedirs(fpath)

def next_fgon_edge(mesh, v_prev, v_now):
    for e in mesh.edges:
        if (e.flag & Mesh.EdgeFlags.FGON) == 0:
            if e.v1.index == v_now and e.v2.index != v_prev:
                return e.v2.index
            if e.v2.index == v_now and e.v1.index != v_prev:
                return e.v1.index
    else:
        print "ERROR: COULD NOT CLOSE FGON!"
        return -1

def get_fgon(mesh):
    vert_list=[]
    for e in mesh.edges:
        if (e.flag & Mesh.EdgeFlags.FGON) == 0:
            v_term = e.v1.index
            v_now = e.v2.index
            v_prev = v_term
            #print "start with %d " % v_term
            vert_list.append(v_term)
            while v_term != v_now:
                #print v_now
                vert_list.append(v_now)
                v_next = next_fgon_edge(mesh, v_prev, v_now)
                if v_next == -1:
                    print "ERROR: bad fgon %s" % o.name
                    break
                v_prev = v_now
                v_now = v_next
            break
    else:
        raise ExportError("ERROR: mesh %s apparently has no non-FGON edges?" % o.name)
    return vert_list

def fgon_cw(fgon_list,mesh):
    total_a=0
    for x in range(2,len(fgon_list)):
        p1=mesh.verts[fgon_list[0]].co
        p2=mesh.verts[fgon_list[x-1]].co
        p3=mesh.verts[fgon_list[x]].co
        v1=p2-p1
        v2=p3-p1
        total_a += (v1[0] * v2[1] - v1[1] * v2[0]) * 0.5
    return total_a < 0

def is_really_fgon(mesh):
    for e in mesh.edges:
        if e.flag & Mesh.EdgeFlags.FGON:
            return True
    return False

class TILE:
    def __init__(self, obj):
        mesh=obj.getData(mesh=True)
        self.s1=9999
        self.s2=-9999
        self.t1=9999
        self.t2=-9999
        self.x1=9999
        self.x2=-9999
        self.y1=9999
        self.y2=-9999
        self.s_cuts=[]
        self.t_cuts=[]
        self.s_slop=[]
        self.t_slop=[]
        self.tile_count=len(mesh.faces)
        self.crop=[]
        self.normal_scale = get_prop(obj, 'TEXTURE_NORMAL', '1.0')
        self.detail_scale = get_prop(obj, 'TEXTURE_DETAIL', '1.0')
        self.terrain_scale = get_prop(obj, 'TEXTURE_TERRAIN', '1.0')
        self.hide_tile = has_prop(obj,'HIDE_TILE')
        self.share_y = has_prop(obj,'SHARE_Y')
        self.more_props = []
        tile_keys = ['DECAL_LIB', 'DITHER_ALPHA'];
        for t in tile_keys:
            if has_prop(obj,t):
                self.more_props.append("%s %s" % (t,get_prop(obj,t,'')))

        x1f= 9999
        x2f=-9999
        y1f= 9999
        y2f=-9999

        mm=obj.getMatrix('localspace')
        scaling = mm.scalePart()
        if scaling[0] < 0.9 or scaling[1] < 0.9 or scaling[2] < 0.9:
            raise ExportError("ERROR: object %s has scaling!" % obj.name)
        for f in mesh.faces:
            (self.tex_width,self.tex_height)=f.image.getSize()
            for v, uv in map(None,f.v, f.uv):
                vt=xform(v,mm)
                self.x1=min(self.x1,vt[0])
                self.x2=max(self.x2,vt[0])
                self.y1=min(self.y1,vt[1])
                self.y2=max(self.y2,vt[1])

                if(uv[0] < self.s1):
                    self.s1 = uv[0]
                    x1f = vt[0]
                if(uv[0] > self.s2):
                    self.s2 = uv[0]
                    x2f = vt[0]
                if(uv[1] < self.t1):
                    self.t1 = uv[1]
                    y1f = vt[1]
                if(uv[1] > self.t2):
                    self.t2 = uv[1]
                    y2f = vt[1]

                if not round(uv[0]*self.tex_width, 1) in self.s_cuts:
                    self.s_cuts.append(round(uv[0]*self.tex_width, 1))
                if not round(uv[1]*self.tex_height, 1) in self.t_cuts:
                    self.t_cuts.append(round(uv[1]*self.tex_height, 1))

            # This is a big nasty mess.  Basically we have to guess whether the author is
            # trying to make a trivial tile (tri or quad), a grid (for AG blocks) or an FGON
            # (for cropped blocks).
            # So: the fgon case happens when we have multiple faces AND at least one interior (fgon flagged) edge.
            # The trivial case happens when we have one face of degree 3 or 4.
            is_fgon = len(mesh.faces) > 1 and is_really_fgon(mesh)
            is_trivial = len(mesh.faces) == 1 and (len(f.v) == 3 or len(f.v) == 4)
            if is_trivial or is_fgon:
                # CROP LOGIC.  Get the fgon, write out the crop boundry.
                crop_raw = get_fgon(mesh)
                if fgon_cw(crop_raw,mesh):
                    crop_raw.reverse()
                #print "raw on %s got %d edges" % ( obj.name, len(crop_raw))
                self.crop=[]
                for i in crop_raw:
                    v = mesh.verts[i]
                    vt = xform(v,mm)
                    self.crop.append(vt)
            else:
                #$ AG Block logic.  Look for two-sided tiles, use to mark slop!
                if (f.mode & Mesh.FaceModes.TWOSIDE)==0:
                    smin=min(f.uv[0][0],f.uv[1][0],f.uv[2][0],f.uv[3][0])
                    tmin=min(f.uv[0][1],f.uv[1][1],f.uv[2][1],f.uv[3][1])
                    if not round(smin*self.tex_width, 1) in self.s_slop:
                        self.s_slop.append(round(smin*self.tex_width, 1))
                    if not round(tmin*self.tex_height, 1) in self.t_slop:
                        self.t_slop.append(round(tmin*self.tex_height, 1))
        if x1f > x2f:
            (self.x1,self.x2) = (self.x2,self.x1)
        if y1f > y2f:
            (self.y1,self.y2) = (self.y2,self.y1)

        f = mesh.faces[0]
        self.tex_name = blender_relative_path(f.image.getFilename())
        self.tex_scale = (self.x2-self.x1) / (self.s2 - self.s1)
        self.s1 *= self.tex_width
        self.s2 *= self.tex_width
        self.t1 *= self.tex_height
        self.t2 *= self.tex_height
        self.s_cuts.sort()
        self.t_cuts.sort()
        self.s_slop.append(self.s_cuts[-1])
        self.t_slop.append(self.t_cuts[-1])
        self.rotation=get_prop(obj,"ROTATION",0)
        aspect = ((self.s2 - self.s1) * (self.y2 - self.y1)) / ((self.t2 - self.t1) * (self.x2 - self.x1))
        if aspect < 0.8 or aspect > 1.2:
            if aspect < -1.2 or aspect > -0.8:
                raise ExportError("WARNING: aspect ratio of tile %s is not 1:1." % obj.name)

    def write_tex_header(self,file):
        file.write("TEXTURE %s\n" % self.tex_name)
        core = get_core_texture(self.tex_name)
        if tex_exists(core+"_NML.png"): file.write("TEXTURE_NORMAL %s %s_NML.png\n" % (self.normal_scale, core))
        elif tex_exists(core+"_NML.dds"): file.write("TEXTURE_NORMAL %s %s_NML.dds\n" % (self.normal_scale, core))
        if tex_exists(core+"_DTL.png"): file.write("TEXTURE_DETAIL %s %s_DTL.png\n" % (self.detail_scale, core))
        elif tex_exists(core+"_DTL.dds"): file.write("TEXTURE_DETAIL %s %s_DTL.dds\n" % (self.detail_scale, core))
        if tex_exists(core+"_CTL.png"): file.write("TEXTURE_CONTROL %s_CTL.png\n" % core)
        elif tex_exists(core+"_CTL.dds"): file.write("TEXTURE_CONTROL %s_CTL.dds\n" % core)
        if tex_exists(core+"_TRN.png"): file.write("TEXTURE_TERRAIN %s %s %s_TRN.png\n" % (self.terrain_scale, self.terrain_scale, core))
        elif tex_exists(core+"_TRN.dds"): file.write("TEXTURE_TERRAIN %s %s %s_TRN.dds\n" % (self.terrain_scale, self.terrain_scale, core))
        if tex_exists(core+"_LIT.png"): file.write("TEXTURE_LIT %s_LIT.png\n" % core)
        elif tex_exists(core+"_LIT.dds"): file.write("TEXTURE_LIT %s_LIT.dds\n" % core)

        file.write("TEXTURE_SCALE %f %f\n" % (self.tex_width,self.tex_height))
        file.write("TEXTURE_WIDTH %f\n\n" % self.tex_scale)
        for s in self.more_props:
            file.write("%s\n" % s)

    def write_tile_header(self,file):
        if self.tile_count==1 or len(self.crop) > 0:
            bounds = (self.s1,self.t1,self.s2,self.t2)
            if self.x2 < self.x1:
                file.write("#X flip.\n");
                bounds = (bounds[2],bounds[1],bounds[0],bounds[3])
            if self.y2 < self.y1:
                file.write("#Y flip.\n");
                bounds = (bounds[0],bounds[3], bounds[2],bounds[1])
            file.write("TILE %f %f %f %f\n\n" % bounds)
            file.write("ROTATION %s\n" % (self.rotation))
            if len(self.crop) > 0:
                file.write("CROP_POLY")
                for v in self.crop:
                    file.write(" %f %f" % (self.scale_st(v[0],v[1],"CROP POLYGON")))
                file.write("\n")
            if self.hide_tile:
                file.write("HIDE_TILE\n")
            if self.share_y:
                file.write("SHARE_Y\n")
        else:
            for s in self.s_cuts:
                file.write("CUT_H %f\n" % s)
                if not s in self.s_slop:
                    file.write("SLOP_H\n")
            for t in self.t_cuts:
                file.write("CUT_V %f\n" % t)
                if not t in self.t_slop:
                    file.write("SLOP_V\n")
            file.write("END_CUTS\n\n")
    def scale_st(self,x, y,debug):
        x_slop = math.fabs(self.x1 - self.x2) * 0.05
        y_slop = math.fabs(self.y1 - self.y2) * 0.05
        if self.x1 < self.x2:
            if x < (self.x1-x_slop) or x > (self.x2+x_slop): raise ExportError("ERROR: UV coordinates %f,%f are out of bounds (%s) - X normal case!" % (x,y,debug))
        else:
            if x < (self.x2-x_slop) or x > (self.x1+x_slop): raise ExportError("ERROR: UV coordinates %f,%f are out of bounds (%s) - X flip case!" % (x,y,debug))
        if self.y1 < self.y2:
            if y < (self.y1-y_slop) or y > (self.y2+y_slop): raise ExportError("ERROR: UV coordinates %f,%f are out of bounds (%s) - Y normal case!" % (x,y,debug))
        else:
            if y < (self.y2-y_slop) or y > (self.y1+y_slop): raise ExportError("ERROR: UV coordinates %f,%f are out of bounds (%s) - Y flip case!" % (x,y,debug))
        return (interp(self.x1,self.s1,self.x2,self.s2,x),interp(self.y1,self.t1,self.y2,self.t2,y))
    def scale_stst(self,x1, y1, x2, y2,debug):
        (s1,t1) = self.scale_st(x1,y1,debug)
        (s2,t2) = self.scale_st(x2,y2,debug)
        return (s1,t1,s2,t2)

def out_trln(file, v0,v1,tile,name):
    file.write("TREE_LINE %f %f %f %f" % tile.scale_stst(v0[0],v0[1],v1[0],v1[1],name))
    file.write(" %s\n" % name)

def out_tree(file, xr, yr, v0, v1, angle, name):
    file.write("TREE %f %f %f %f %s\n" % (xr, yr, angle, math.sqrt((v0[0]-v1[0])*(v0[0]-v1[0])+(v0[1]-v1[1])*(v0[1]-v1[1])), name))

def child_obj_name(wrapper,all):
    choices = getChildren(wrapper,all)
    for c in choices:
        nm=strip_suffix(c.name)
        # For Alex - skip LD1
        if nm[-3:] != 'LD1':
            if c.getType() == 'Mesh':
                return c.name
            if c.getType() == 'Empty':
                return c.name
    raise ExportError("ERROR: could not find real physical name for obj %s." % wrapper.name)
    return wrapper.name[3:]

# What name should we export the OBJ as into the library?  If we have the 'external' property then
# that IS the full path.  If not, strip the prefix, and use the lib root and current theme to synthesize
# the path.
def lib_obj_name(obj,theme,lib_root):
    if has_prop(obj,'external'):
        return get_prop(obj,'external',obj.name)
    elif obj.name[0:7] == 'OBJcom_':
        oname=strip_prefix(obj.name,'OBJ')
        return "objects/%s.obj" % oname
    else:
        #if has_prop(obj,'vname'):
        #	return get_prop(obj,'vname',obj.name)
        oname=strip_prefix(obj.name,'OBJ')
        if theme=='unparsable':
            return "objects/%s.obj" % oname
        else:
            return "%s/%s/%s.obj" % (lib_root,theme,oname)

def lib_fac_name(obj,theme):
    if has_prop(obj,'external'):
        return get_prop(obj,'external',obj.name)
    else:
        raise ExportError("ERROR: The facade %s has no external property." % obj.name)
#------------------------------------------------------------------------
#-- Exporter Class
#------------------------------------------------------------------------
class AGExport:

    #------------------------------------------------------------------------
    def __init__(self, path, objdir):
        #--- public you can change these ---
        self.debug=1	# extra debug info in console

        #--- class private don't touch ---
        self.file=None
        self.path=path
        self.objdir=objdir
        self.log=[]

        #--- crap to make Jonathan's utils happy! ---
        self.iscockpit=0
        self.layermask=1
        self.obj_name_list=[]
        self.fac_name_list=[]

        p=path.find("Custom Scenery/")
        if p==-1:
            p=path.find("default scenery/")
        if p==-1:
            p=path.find("global scenery/")
        if p==-1:
            self.theme="unknown"
        else:
            self.theme=path[p:]
            p=self.theme.find('/')
            if p==-1:
                self.theme="unparsable"
            else:
                self.theme=self.theme[p+1:]
                p=self.theme.find('/')
                if p==-1:
                    self.theme="unparsable"
                else:
                    self.theme=self.theme[p+1:]

    #------------------------------------------------------------------------
    def export(self, scene):
        files = getAllDepth(0,scene.objects)

        for f in files:
            if f.getType() == 'Empty':
                self.export_ag_file(f,scene)

    def export_ag_file(self, obj, scene):
        if self.debug: print "Starting export of %s" % obj.name
        want_groups=0
        self.obj_name_list=[]
        self.fac_name_list=[]

        real_name=strip_suffix(obj.name[3:])
        suffix='.'+obj.name[0:3].lower()

        export_name=os.path.join(self.path,real_name+suffix)

        print 'Starting AG export to ' + export_name

        is_ags=False

        if not checkFile(export_name):
            return

        if has_prefix(obj.name,'agb'):
            self.file = open(export_name, 'w')
            self.file.write("A\n1000\nAG_BLOCK\n\n")
        elif has_prefix(obj.name,'ags'):
            self.file = open(export_name, 'w')
            self.file.write("A\n1000\nAG_STRING\n\n")
            is_ags=True
        elif has_prefix(obj.name,'agp'):
            self.file = open(export_name, 'w')
            self.file.write("A\n1000\nAG_POINT\n\n")
        else:
            if not obj.name[0:3].upper() in ['OBJ','BGN', 'END','VRT']:
                print "ERROR: object %s is of unknown type." % obj.name
            return

        vname = get_prop(obj, 'vname', real_name)
        vname1 = get_prop(obj, 'vname1', real_name)
        vname2 = get_prop(obj, 'vname2', real_name)

        want_tile_ids = has_prop(obj,'tile_ids')

        lib_root = get_prop(obj,'lib_root',def_lib_root)

        self.file.write("EXPORT %s/%s/%s %s/%s\n\n" % (lib_root,self.theme,vname+suffix,self.theme,real_name+suffix));
        if vname != vname1: self.file.write("EXPORT %s/%s/%s %s/%s\n\n" % (lib_root,self.theme,vname1+suffix,self.theme,real_name+suffix));
        if vname != vname2 and vname1 != vname2: self.file.write("EXPORT %s/%s/%s %s/%s\n\n" % (lib_root,self.theme,vname2+suffix,self.theme,real_name+suffix));

        top_level_objects = getChildren(obj, scene.objects)
        top_level_objects.sort(key=sort_obj_by_name)

        # we also grab any 'surplus' objects floating around at the 'tile/variant' level.
        # these will NOT be used as annotations but for OBJs we still run the export.  This gets
        # Alex (1) more files out on disk and (2) the EXPORT name in the .agp for copying to
        # library.txt with a shell script.
        # we have to recurse to get only OUR annotations per file - otherwise we get cross-talk between tiles, which is bad.
        variants = getChildren(obj, scene.objects)
        annotations = []
        for v in variants:
            annotations += getChildren(v,scene.objects)
        annotations_real = getAllDepth(2,scene.objects)
        objs = filter_objects(annotations,'Empty', 'OBJ')
        facs = filter_objects(annotations,'Mesh', 'FAC')
        tiles = filter_objects(annotations,'Mesh', 'TILE')
        objs += filter_objects(variants,'Empty','OBJ')

        # objs += filter_objects(extras,'Empty','OBJ')

        print "For AG %s" % obj.name
        for v in variants:
            print "Foudn variant %s" % v.name
        for a in annotations:
            print "Found annotation %s" % a.name
        for r in annotations_real:
            print "Real annotation: %s" % r.name
        for o in objs:
            print "found obj container %s" % o.name

        if len(tiles)==0:
            raise ExportError("ERROR: no tiles were found in the AG export file %s." % obj.name)
            return

        tt=TILE(tiles[0])

        ag_keys = [ 'HIDE_TILES', 'TILE_LOD', 'LAYER_GROUP', 'CROP', 'MINIMUM_OVERLAP', 'VEGETATION', 'CREASE_ANGLE', 'CAPS', 'FILL_LAYER',
                    'SLOPE_LIMIT', 'OVERLAP_H', 'OVERLAP_V', 'SPELLING_S', 'SPELLING_T', 'CORNER', 'SPELLING' ];
        global_props=[]
        accum_properties(obj, ag_keys, global_props)

        text_props=text_for_obj(obj.name)


        for o in facs:
            fname=lib_fac_name(o,self.theme)
            if not fname in self.fac_name_list:
                self.fac_name_list.append(fname)
                # Ben says: facades are ALWAYS external, do NOT run facade exporter here.
                #self.file.write("EXPORT %s/%s/%s.fac %s/objects/%s.fac\n" % (lib_root, self.theme, fname, self.theme,fname))

        #
        # OBJ GENERATION
        #
        # Now is a good time to export OBJs for any attached OBJS...why not?
        #
        obj_exp_list=[]			# List of real files for export.
        obj_lib_list=[]			# List of virtual->real path pairs for export lib entries.
        for o in objs:
            lname=lib_obj_name(o,self.theme, lib_root)
            if not lname in self.obj_name_list:
                self.obj_name_list.append(lname)
            # if an OBJ is tagged external, don't go writing the OBJ; that means we're using something that already exists.
            if not has_prop(o,'external'):
                l=o.name.rfind('.')
                export_name=strip_suffix(child_obj_name(o,scene.objects))+'.obj'
                export_path=os.path.join(self.objdir,export_name)
                if not export_name in obj_exp_list:
                    exporter=OBJexport8(export_path)
                    exporter.additive_lod=1
                    exporter.use_mat=0
                    my_parts=getGrandChildren(o,scene.objects)
                    exporter.openFile(my_parts,o,'../')
                    exporter.writeHeader()
                    exporter.writeObjects(my_parts)
                    # don't double-accume obj-name list because it is used to build the obj index table!!
                    obj_exp_list.append(export_name)
                else:
                    if self.debug: print "Skipping second export of OBJ %s (%s)" % (lname,export_name)
                if not [lname,export_name] in obj_lib_list:
                    if o.name[0:7] != 'OBJcom_':
                        self.file.write("EXPORT %s %s/objects/%s\n" % (lname, self.theme,export_name))
                    obj_lib_list.append([lname,export_name])
                else:
                    if self.debug: print "Skipping second lib entry of OBJ %s (%s)" % (lname,export_name)
            else:
                if self.debug: print "Skipping external OBJ %s" % lname
        self.file.write("\n")

        #
        # Write headers
        #
        tt.write_tex_header(self.file)
        if has_prop(obj,'macro'):
            macro=get_macro(get_prop(obj,'macro',''))
            if macro!=None:
                self.file.write(macro)
            else:
                raise ExportError("WARNING: missing macro %s." % get_prop(obj,'macro',''))
        self.file.write("\n")
        for g in global_props:
            self.file.write("%s\n" % g)
        self.file.write("\n")
        for n in self.obj_name_list:
            self.file.write("OBJECT %s\n" % n)
        for n in self.fac_name_list:
            self.file.write("FACADE %s\n" % n)
        self.file.write("\n")

        tile_list=[]

        #
        # TILE ANNOTATION EXPORT
        #
        for o in top_level_objects:
            if not has_prefix(o.name,'obj'):
                if is_ags and want_tile_ids:
                    self.export_ag_tile(o, getChildren(o,scene.objects),scene.objects,lib_root, tile_list)
                else:
                    self.export_ag_tile(o, getChildren(o,scene.objects),scene.objects,lib_root, None)

        for g in text_props:
            self.file.write("%s\n" % g)

        print tile_list

        self.file.close
        if self.log:
            r=Draw.PupMenu('|'.join([a[0] for a in self.log]))


    #######################################################################################################################################
    # This routine exports one AG tile
    #######################################################################################################################################
    def export_ag_tile(self, obj, ann_list,all,lib_root, valid_ids):
        if self.debug: print "Exporting ag tile based on empty obj %s." % obj.name
        name=obj.name
        if valid_ids != None:
            if not name.isdigit(): raise ExportError("ERROR: tile %s has a name that is not a vaild numeric tile ID." % name);
            self.file.write("\nTILE_ID %s\n" % name)
            valid_ids.append(name)
        else:
            self.file.write("\n# Tile: %s\n" % name)
        # Pass 1.  Work up an OBJ master list for indexing, and find the tile boundaries.
        has_tile=0

        objs = filter_objects(ann_list,'Empty', 'OBJ')
        facs = filter_objects(ann_list,'Mesh', 'FAC')
        tiles = filter_objects(ann_list,'Mesh', 'TILE')
        trees = filter_objects(ann_list,'Mesh', 'TREE')
        trlns = filter_objects(ann_list,'Mesh', 'TRLN')
        pins = filter_objects(ann_list,'Lamp', 'PIN')
        metas = filter_objects(ann_list,'Mesh','META')

        if self.debug: print "   %d annotations, %d objs, %d faces, %d tiles, %d trees, %d tree lines, %d pins" % (len(ann_list), len(objs),len(facs),len(tiles),len(trees),len(trlns),len(pins))

        if len(tiles) != 1:
            raise ExportError("ERROR: tile %s has %d tile objects." % (obj.name, len(tiles)))
            return

        tt=TILE(tiles[0])

        tt.write_tile_header(self.file)

        #
        # ATTACHED OBJECTS
        #
        for o in objs:
            #Ben says: this used to have an anti-dupe logic using a layer check...but...that should NOT be necessary!
            #One OBJ for each export.
            oname=lib_obj_name(o,self.theme,lib_root)
            #xr=tt.scale_s(o.LocX)
            #yr=tt.scale_t(o.LocY)
            loc=o.getMatrix('localspace').translationPart()
            (xr,yr)=tt.scale_st(loc[0],loc[1],o.name)
            if has_prop(o,"STEP"):
                agl_span = 0
                step = get_prop(o,"step",1.0)
                delta_agl = o.getMatrix('localspace').translationPart()[2]
                scraper_parts = getGrandChildren(o,all)
                for s in scraper_parts:
                    mm=s.getMatrix('localspace')
                    if s.getType()=='Mesh':
                        mesh=s.getData(mesh=True)
                        for v in mesh.verts:
                            vt=xform(v,mm)
                            agl_span = max(vt[2],agl_span)
                self.file.write("OBJ_SCRAPER %f %f %f %d %f %f %s" % (xr, yr, make_degs(-o.RotZ), self.obj_name_list.index(oname), agl_span, agl_span + delta_agl, step))
            elif has_prop(o,"DELTA"):
                self.file.write("OBJ_DELTA %f %f %f %s %d" % (xr, yr, make_degs(-o.RotZ), get_prop(o,"DELTA",0.0), self.obj_name_list.index(oname)))
            elif has_prop(o,"GRADED"):
                self.file.write("OBJ_GRADED %f %f %f %d" % (xr, yr, make_degs(-o.RotZ), self.obj_name_list.index(oname)))
            else:
                self.file.write("OBJ_DRAPED %f %f %f %d" % (xr, yr, make_degs(-o.RotZ), self.obj_name_list.index(oname)))
            if has_prop(o,'show_level'):
                self.file.write(" %s" % get_prop(o,'show_level',''))
            self.file.write("\n")

        #
        # TREE LINES
        #
        for o in trlns:
            mesh=o.getData(mesh=True)
            mm=o.getMatrix('localspace')
            if len(mesh.faces) != 1:
                raise ExportError("ERROR: mesh %s has %d faces." % (o.name, len(mesh.faces)))
                continue
            f=mesh.faces[0]
            if len(f.v) != 4:
                raise ExportError("ERROR: mesh %s has %d vertices." % (o.name, len(f.v)))
            v0=xform(f.v[0],mm)
            v1=xform(f.v[1],mm)
            v2=xform(f.v[2],mm)
            v3=xform(f.v[3],mm)
            exp_layer_name=strip_prefix(o.name,'TRLN')
            if near_zero(v0[2]) and near_zero(v1[2]):
                out_trln(self.file, v0,v1,tt,exp_layer_name)
            elif near_zero(v1[2]) and near_zero(v2[2]):
                out_trln(self.file, v1,v2,tt,exp_layer_name)
            elif near_zero(v2[2]) and near_zero(v3[2]):
                out_trln(self.file, v2,v3,tt,exp_layer_name)
            elif near_zero(v3[2]) and near_zero(v0[2]):
                out_trln(self.file, v3,v0,tt,exp_layer_name)
            else:
                raise ExportError("ERROR: Tree line seems to have no zero intersect" % o.name)
        #
        # INDIVIDUAL TREES
        #
        for o in trees:
            mesh=o.getData(mesh=True)
            loc=o.getMatrix('localspace').translationPart()
            (xr,yr)=tt.scale_st(loc[0],loc[1],o.name)
            hi=0
            lo=0
            mm=o.getMatrix('localspace')
            for f in mesh.faces:
                if len(f.v) != 4:
                    raise ExportError("ERROR: the tree %s has a face that is not four-sided." % o.name)
                v0=xform(f.v[0],mm)
                v1=xform(f.v[1],mm)
                v2=xform(f.v[2],mm)
                v3=xform(f.v[3],mm)
                if near_zero(v0[2]) and near_zero(v1[2]):
                    out_tree(self.file, xr, yr, v0,v1, make_degs(-o.RotZ), strip_prefix(o.name,'TREE'))
                    break
                elif near_zero(v1[2]) and near_zero(v2[2]):
                    out_tree(self.file, xr, yr, v1,v2, make_degs(-o.RotZ), strip_prefix(o.name,'TREE'))
                    break
                elif near_zero(v2[2]) and near_zero(v3[2]):
                    out_tree(self.file, xr, yr, v2,v3, make_degs(-o.RotZ), strip_prefix(o.name,'TREE'))
                    break
                elif near_zero(v3[2]) and near_zero(v0[2]):
                    out_tree(self.file, xr, yr, v3,v0, make_degs(-o.RotZ), strip_prefix(o.name,'TREE'))
                    break
                else:
                    print v0, v1, v2, v3
                    raise ExportError("ERROR: Tree %s seems to have non zero intersect" % o.name)
        #
        # FACADES
        #
        for o in facs:
            mesh=o.getData(mesh=True)
            idx=self.fac_name_list.index(lib_fac_name(o, self.theme))
            # We are going to find one non-fgon edge (that is, an edge not internal to the triangulation of the fgon) and
            # then loop around edge connectivity to find the perimeter.  There MIGHT be a blender way to do this with indexing,
            # but for the small number of edges we have, screw it...next_fgon_edge is O(N)
            if not is_really_fgon(mesh):
                if len(mesh.faces) != 1 or len(mesh.faces[0].verts) != 4:
                    raise ExportError("Mesh %s is not an fgon." % mesh.name)
            vert_list=get_fgon(mesh)
            if fgon_cw(vert_list,mesh):
                vert_list.reverse()

            if len(vert_list) < 2:
                raise ExportError("ERROR: mesh %s has too few vertices." % o.name)
                continue
            mm=o.getMatrix('localspace')
            v = mesh.verts[0]
            vt = xform(v,mm)
            h = vt[2]

            # Rotate the vertex list to have all but one zero interception first.  This ensures that all non-zero
            # are continuous; for fence-style facades, this means we won't have the end, then circulate to the beginning.
            n = 0
            found_any_near_zero=0
            for ii, i in enumerate(vert_list):
                if near_zero(xform(mesh.verts[i],mm)[2]):
                    n=ii
                    found_any_near_zero=1
            if n != 0:
                vert_list[:]=   vert_list[n:] + vert_list[:n]

            # What the hell is THIS?  Well, if we have a FENCE style facade, the fgon-cw test above is going to produce CRAP because
            # the facade isn't co-planar.  So: take the first face and compare its normal in the order we traverse it (e.g. grabbing its 4
            # verts as they pass by in the stream) to the real face normal.  If the user flipped the face, flip the stream.
            if found_any_near_zero:
                v_our_order=[]
                f=mesh.faces[0]
                for i in vert_list:
                    if face_has_vert_index(f,i):
                        v_our_order.append(i)
                n=TriangleNormal(mesh.verts[v_our_order[0]].co,mesh.verts[v_our_order[1]].co,mesh.verts[v_our_order[2]].co)
                if f.no.dot(n) < 0:
                    vert_list.reverse()

            # Nuke zero intercepts so that fences are now 'just the fence'.
            vert_list[:] = [v for v in vert_list if not near_zero(xform(mesh.verts[v],mm)[2])]

            wlist=[]
            for i in xrange(1,len(vert_list)):
                v1 = vert_list[i-1]
                v2 = vert_list[i]
                for f in mesh.faces:
                    if face_has_vert_index(f,v1) and face_has_vert_index(f,v2):
                        if f.mode & Mesh.FaceModes.TILES:
                            wlist.append(1)
                        else:
                            wlist.append(0)
                        break
                else: raise ExportError("Internal error: we never found a face.")

            wlist.append(0)

            if sum(wlist) > 0:
                self.file.write("FAC_WALLS %d %f" % (idx,h))
                for x,i in enumerate(vert_list):
                    v = mesh.verts[i]
                    vt = xform(v,mm)
                    #print vt
                    (xr,yr)=tt.scale_st(vt[0],vt[1],o.name)
                    self.file.write(" %f %f %d" % (xr,yr,wlist[x]))
                self.file.write("\n")
            else:
                self.file.write("FAC %d %f" % (idx,h))
                for i in vert_list:
                    v = mesh.verts[i]
                    vt = xform(v,mm)
                    #print vt
                    (xr,yr)=tt.scale_st(vt[0],vt[1],o.name)
                    self.file.write(" %f %f" % (xr,yr))
                self.file.write("\n")
        #
        # PINS
        #
        for o in pins:
            loc=o.getMatrix('localspace').translationPart()
            (xr,yr)=tt.scale_st(loc[0],loc[1],o.name)
            self.file.write("%s %f %f\n" % (strip_prefix(o.name,'PIN'), xr, yr))
        #
        # Meta-rects
        #
        for o in metas:
            mesh=o.getData(mesh=True)
            if len(mesh.faces) != 1:
                raise ExportError("ERROR: meta object %s does not have one face." % o.name)
                break
            f=mesh.faces[0]
            if len(f.verts) != 4:
                raise ExportError("ERROR: face for meta object %s does not have four sides." % o.name)
                break
            mm=o.getMatrix('localspace')
            v0=xform(f.v[0],mm)
            v1=xform(f.v[1],mm)
            v2=xform(f.v[2],mm)
            v3=xform(f.v[3],mm)
            WWS=4.25
            if strip_prefix(o.name,'META').lower() == 'block_edge':
                self.file.write("EDGE_MAX %f %f %f %f\n" % (tt.scale_stst(min(v0[0],v1[0],v2[0],v3[0])-WWS,min(v0[1],v1[1],v2[1],v3[1])-WWS,max(v0[0],v1[0],v2[0],v3[0])+WWS,max(v0[1],v1[1],v2[1],v3[1])+WWS,o.name)))
            else:
                self.file.write("%s " % strip_prefix(o.name,'META'))
                self.file.write("%f %f %f %f\n" % tt.scale_stst(min(v0[0],v1[0],v2[0],v3[0]),min(v0[1],v1[1],v2[1],v3[1]),max(v0[0],v1[0],v2[0],v3[0]),max(v0[1],v1[1],v2[1],v3[1]),o.name))

#------------------------------------------------------------------------
if Window.EditMode(): Window.EditMode(0)
try:
    obj=None
    scene = Blender.Scene.GetCurrent()

    baseFileName=Blender.Get('filename')
    l = baseFileName.lower().rfind('.blend')
    if l==-1: raise ExportError('Save this .blend file first')
    path=os.path.dirname(baseFileName)
    require_dir(path,'objects')
    #require_dir(path,'textures')
    obj=AGExport(path,os.path.join(path,'objects'))
    obj.export(scene)
    Draw.PupMenu("Export complete.")

except IOError, e:
    Window.WaitCursor(0)
    Window.DrawProgressBar(0, 'ERROR')
    print "ERROR:\t%s\n" % e.strerror
    Draw.PupMenu("ERROR%%t|%s" % e.strerror)
    Window.DrawProgressBar(1, 'ERROR')
    if obj and obj.file: obj.file.close()
except ExportError, e:
    if e.msg:
        Window.WaitCursor(0)
        Window.DrawProgressBar(0, 'ERROR')
        print "ERROR:\t%s.\n" % e.msg
        Draw.PupMenu("ERROR%%t|%s" % e.msg)
        Window.DrawProgressBar(1, 'ERROR')
