#!BPY
""" Registration info for Blender menus:
Name: 'X-Plane Road (.net)...'
Blender: 249
Group: 'Import'
Tooltip: 'Import an X-Plane road network (.net)'
"""
__author__ = "Ben Supnik"
__email__ = "Ben Supnik, bsupnik at xsquawkbox dot net"
__url__ = "X-Plane, wiki.x-plane.com"
__version__ = "1.00"
__bpydoc__ = """\
This script is a derivative work of Jonathan Harris' X-Plane blender scripts, and is covered under the terms of the GPL.
"""

import sys
import os
import Blender
from Blender import Armature, Object, Mesh, NMesh, Lamp, Image, Material, Texture, Draw, Window, Text
from XPlaneUtils import *

# Use this is Z to have draped roads below graded, so author can see both for transitionals.
draped_y=-5


def TEXT_create_or_clear(name):
    existing = Blender.Text.Get()
    for e in existing:
        if e.name == name:
            e.clear()
            return e
    return Blender.Text.New(name)

class ParseError(Exception):
    def __init__(self, type, value=""):
        self.type = type
        self.value = value
    HEADER = 0
    TOKEN  = 1
    INTEGER= 2
    FLOAT  = 3
    NAME   = 4
    MISC   = 5
    EOF    = 6
    EOL    = 7
    TEXT   = ["Header", "Command", "Integer", "Number", "Name", "Misc", "EOF", "EOL" ]

class	TXTFile:
    def __init__(self, filename):
        self.lines=[]
        file=open(filename,'r')
        for line in file:
            lines = line.split('\r\n')
            for l in lines:
                ls=l.strip()
                if len(ls) > 0:
                    self.lines.append(ls)
        file.close()
        self.lineno=1

    def get_token(self, want_pop, eol_ok):
        if len(self.lines) < 1:
            raise ParseError(ParseError.EOF)
        toks = self.lines[0].split(None,1)
        if not eol_ok and len(toks) == 0:
            raise ParseError(ParseError.EOL)
        if len(toks) == 0:
            return ""
        if want_pop:
            if len(toks) == 1:
                self.lines[0] = ""
            else:
                self.lines[0] = toks[1]
        return toks[0]

    def TXT_is_done(self):
        return len(self.lines) == 0

    def TXT_str_scan_eoln(self):
        if len(self.lines) < 1:
            raise ParseError(ParseError.EOF)
        l = self.lines.pop(0)
        self.lineno += 1
        return l

    def TXT_str_scan_match(self,token):
        t = self.get_token(False, True)
        return t == token

    def TXT_int_scan(self):
        t = self.get_token(True, False)
        try:
            return int(t)
        except ValueError:
            raise ParseError(ParseError.INTEGER, t)

    def TXT_flt_scan(self):
        t = self.get_token(True, False)
        try:
            return float(t)
        except ValueError:
            raise ParseError(ParseError.INTEGER, t)

    def TXT_str_scan_space(self):
        return self.get_token(True, False)

    def TXT_str_scan_space_optional(self):
        return self.get_token(True, True)

def prop_import(obj, tag, line):
    obj.addProperty(tag,line,'STRING')

class NETimport:
    def __init__(self, filename):
        self.m=TXTFile(filename)
        self.junc=[]
        self.chain=[]
        self.chain_width=0
        self.chain_length=0
        self.chain_center=0
        self.shader_idx=0
        self.scale = 1
        self.shaders = SHADER_SET()
        self.filename=filename

    def doimport(self):
        h1 = self.m.TXT_str_scan_space()
        self.m.TXT_str_scan_eoln()
        v = self.m.TXT_int_scan()
        self.m.TXT_str_scan_eoln()
        h2 = self.m.TXT_str_scan_space()
        self.m.TXT_str_scan_eoln()
        if h1.upper() != 'A' and h1.upper() != 'I':
            raise ParseError(ParseError.MISC,"Bad header, must be A or I")
        if v != 800:
            raise ParseError(ParseError.MISC,"Bad version, must be 800")
        if h2.upper() != 'ROADS':
            raise ParseError(ParseError.MISC,"Bad header, file class must be ROADS")

        header=[]
        footer=[]

        dir = os.path.dirname(self.filename)
        last_name=''

        while not self.m.TXT_is_done():
            t = self.m.TXT_str_scan_space()
            if t in ['#SHADER', 'TEXTURE','TEXTURE_LIT','TEXTURE_NORMAL','NO_BLEND','ONE_SIDED','SPECULAR','DECAL','DECAL_RGBA','DECAL_KEYED','DECAL_PARAMS','DECAL_LIB',
                    'NO_APHA','DITHER_ALPHA','TEXTURE_TILE','TEXTURE_DETAIL','TEXTURE_CONTROL','TEXTURE_TERRAIN',
                    'VARIANTS','CAR_MODEL','TRAIN','TRAIN_VARIANT','TRAIN_CAR']:
                t += ' '
                t += self.m.TXT_str_scan_eoln()
                if self.shaders.is_shader_line(t):
                    self.shaders.handle_shader_line(t)
                header.append(t)
            elif t in ['ROAD_DRAPED','ROAD_DRAPE_CHOICE','#VROAD']:
                t += ' '
                t += self.m.TXT_str_scan_eoln()
                footer.append(t)
            elif t == 'SCALE':
                self.scale = self.m.TXT_flt_scan()
                self.m.TXT_str_scan_eoln()
            elif t == '#ROAD':
                last_name=self.m.TXT_str_scan_eoln()
            elif t == 'ROAD_TYPE':
                self.shaders.load_all_images(dir)
                id = self.m.TXT_str_scan_space()
                self.chain=Blender.Object.New('Empty','ROA%s.%s' % (id, last_name))
                self.chain_width = self.m.TXT_flt_scan()
                self.chain_length = self.m.TXT_flt_scan()
                self.shader_idx = self.m.TXT_int_scan()
                self.chain_center=self.chain_width*0.5
                prop_import(self.chain,'RGB',self.m.TXT_str_scan_eoln())
                prop_import(self.chain,'NAME',last_name)
                Blender.Scene.GetCurrent().objects.link(self.chain)
                num_id = int(id)
                core = num_id / 1000
                grad = num_id % 10
                side  = (num_id / 100) % 10
                self.chain.setLocation(core * 100, (side * 5 + grad) * 200, 0)
            elif t == 'ROAD_CENTER':
                self.chain_center = self.m.TXT_flt_scan()
                self.m.TXT_str_scan_eoln()
            elif t in ['SHOW_LEVEL', 'REQUIRE_EVEN']:
                prop_import(self.chain,t,self.m.TXT_str_scan_eoln())
            elif t == 'SEGMENT_GRADED' or t == 'SEGMENT_DRAPED':
                shader_idx = self.m.TXT_int_scan()
                near_lod = self.m.TXT_flt_scan()
                far_lod = self.m.TXT_flt_scan()
                t_scale = self.m.TXT_flt_scan()
                x1 = self.m.TXT_flt_scan() - self.chain_center
                if t == 'SEGMENT_GRADED':	y1 = self.m.TXT_flt_scan()
                else:						y1 = draped_y
                s1 = self.m.TXT_flt_scan() / self.scale
                x2 = self.m.TXT_flt_scan() - self.chain_center
                if t == 'SEGMENT_GRADED':	y2 = self.m.TXT_flt_scan()
                else:						y2 = draped_y
                s2 = self.m.TXT_flt_scan() / self.scale
                surf = self.m.TXT_str_scan_space_optional()
                self.m.TXT_str_scan_eoln()
                nm = Mesh.New()
                verts =[ [ x1, 0, y1], [ x2, 0, y2], [x2, self.chain_length, y2], [x1, self.chain_length, y1]]
                loc = self.chain.getLocation('localspace')
                #for v in verts:
                #	v[0] += loc[0]
                #	v[1] += loc[1]
                #	v[2] += loc[2]
                faces = [[0,1,2,3 ]]
                nm.verts.extend(verts)
                nm.faces.extend(faces)
                nm.faceUV= 1
                my_img = self.shaders.material_for_idx(shader_idx)
                # append won't work, materials is returned by value or somethign silly.
                nm.materials += [my_img]
                for f in nm.faces:
                    f.image=my_img.textures[0].tex.image
                    f.mode|=Mesh.FaceModes.TEX
                    f.transp=Mesh.FaceTranspModes.ALPHA
                    if t == 'SEGMENT_DRAPED':
                        f.mode|=Mesh.FaceModes.TILES
                        if self.shaders.poly_os_for_idx(shader_idx) == 0:
                            print "WARNING: draped segment has non-draped shader."
                    else:
                        if self.shaders.poly_os_for_idx(shader_idx) > 0:
                            print "WARNING: draped segment has non-draped shader."
                    f.uv[0][0] = s1
                    f.uv[1][0] = s2
                    f.uv[2][0] = s2
                    f.uv[3][0] = s1
                    f.uv[0][1] = 0
                    f.uv[1][1] = 0
                    f.uv[2][1] = t_scale
                    f.uv[3][1] = t_scale
                    f.mat=nm.materials.index(my_img)
                ob = Object.New('Mesh',"%d" % shader_idx)
                ob.setLocation(loc[0],loc[1],loc[2])
                Blender.Scene.GetCurrent().objects.link(ob)
                ob.link(nm)
                kids=[]
                kids.append(ob)
                self.chain.makeParent(kids,1,1)
            elif t == 'WIRE':
                lod_near = self.m.TXT_flt_scan()
                lod_far = self.m.TXT_flt_scan()
                dx = self.m.TXT_flt_scan() * self.chain_width - self.chain_center
                y = self.m.TXT_flt_scan()
                droop = self.m.TXT_flt_scan()
                nm = Mesh.New()
                verts =[ [ dx, 0, y * droop], [ dx, 0, y], [dx, self.chain_length, y], [dx, self.chain_length, y * droop]]
                faces = [[0,1,2,3 ]]
                loc = self.chain.getLocation('localspace')
                #for v in verts:
                #	v[0] += loc[0]
                #	v[1] += loc[1]
                #	v[2] += loc[2]
                nm.verts.extend(verts)
                nm.faces.extend(faces)
                nm.faceUV=1
                for f in nm.faces:
                    f.mode|=Mesh.FaceModes.TWOSIDE
                ob = Object.New('Mesh',"wire")
                ob.setLocation(loc[0],loc[1],loc[2])
                Blender.Scene.GetCurrent().objects.link(ob)
                ob.link(nm)
                kids=[]
                kids.append(ob)
                self.chain.makeParent(kids,1,1)
                self.m.TXT_str_scan_eoln()
            else:
                self.m.TXT_str_scan_eoln()

        h = TEXT_create_or_clear('header')
        f = TEXT_create_or_clear('footer')
        for l in header:
            h.write("%s\n" % l)
        for l in footer:
            f.write("%s\n" % l)

def file_callback (filename):
    obj=NETimport(filename)
    try:
        obj.doimport()
        Blender.Scene.GetCurrent().update()
    except ParseError, e:
        Window.WaitCursor(0)
        Window.DrawProgressBar(0, 'ERROR')
        if e.type == ParseError.HEADER:
            msg='This is not a valid X-Plane v6, v7 or v8 OBJ file'
        elif e.type == ParseError.NAME:
            msg='Missing dataref or light name at line %s\n' % obj.m.lineno
        elif e.type == ParseError.MISC:
            msg='%s at line %s' % (e.value, obj.m.lineno)
        else:
            thing=ParseError.TEXT[e.type]
            if e.value:
                msg='Expecting a %s, found "%s" at line %s' % (thing, e.value, obj.m.lineno)
            else:
                msg='Missing %s at line %s' % (thing, obj.m.lineno)
        print "ERROR:\t%s\n" % msg
        Draw.PupMenu("ERROR%%t|%s" % msg)
        Window.RedrawAll()
        Window.DrawProgressBar(1, 'ERROR')

Window.FileSelector(file_callback,"Import road.net")
