#!BPY
""" Registration info for Blender menus:
Name: 'X-Plane Annotation'
Blender: 249
Group: 'Import'
Tooltip: 'Import an OBJ annotation.'
"""
__author__ = "Ben Supnik"
__email__ = "Ben Supnik, Ben Supnik <bsupnik:xsquawkbox*net>"
__url__ = "developer.x-plane.com"
__version__ = "3.11"
__bpydoc__ = """\
This script imports X-Plane object annotations.
"""

#
# Copyright (c) 2012-2013 Ben Supnik
#
# This code is licensed under version 2 of the GNU General Public License.
# http://www.gnu.org/licenses/gpl-2.0.html
#
# See ReadMe-XPlane2Blender.html for usage.
#

import sys
import os
import Blender
from Blender import Armature, Object, Mesh, NMesh, Lamp, Image, Material, Texture, Draw, Window, Text, Registry
from Blender.Mathutils import Matrix, RotationMatrix, TranslationMatrix, Vector
from XPlaneUtils import *
from Blender.Window import GetCursorPos
from XPlaneExport import ExportError
from XPlaneImport_util import OBJimport, ParseError
from XPlaneLib import *

def set_pref_key(container, key, value):
    dict = Blender.Registry.GetKey(container)
    if not dict:
        dict={}
    dict[key]=value
    Blender.Registry.SetKey(container,dict)

def get_pref_key(container, key):
    dict = Blender.Registry.GetKey(container)
    if not dict:
        return None
    if not key in dict:
        return None
    return dict[key]


def make_relative_path(path_to_child, path_to_parent_dir):
    child = path_to_child.split('/')
    par = path_to_parent_dir.split('/')
    while len(par) > 0 and len(child) > 0 and par[0] == child[0]:
        child.pop(0)
        par.pop(0)
    ret = []
    for x in par:
        ret.append('..')
    ret.extend(child)
    return '/'.join(ret)

def append_to_inner(list, item):
    if len(list) == 0:
        list.append(item)
    elif type(list[-1][1]) != type([]):
        list.append(item)
    else:
        append_to_inner(list[-1][1], item)

def extend_pop_for(items, segments):
    if len(segments) != 0:
        if len(items) == 0 or type(items[-1][1]) != type([]) or segments[0] != items[-1][0]:
            items.append((segments[0], []))
        extend_pop_for(items[-1][1],segments[1:])

try:
    baseFileName=Blender.Get('filename')
    l = baseFileName.lower().rfind('.blend')
    if l==-1: raise ExportError('Save this .blend file first')
    root = locate_root(baseFileName)
    packs = get_scenery_packs(root[0])
    objs = get_local_assets(root[1],'.obj')
    items = get_library(root[0],'.obj')

    items.extend(objs)

    items = [(i[0],i[1],i[2],i[0]) for i in items]

    items.sort(key=lambda item: item[0])

    last_item =	get_pref_key('xplane.tools','annotate.last_item')
    if last_item:
        #pop_list.append((last_item[0],len(items)))
        #items.append(last_item)
        vpath='/'.join(last_item[0].split('/')[:-1])
        new_items = []
        for i in items:
            if i[0].startswith(vpath):
                new_items.append([i[0],i[1],i[2],"recent items/"+i[0].split('/')[-1]])
        items.extend(new_items)


    pop_list=[]

    for i in items:
        path=i[3].split('/')[:-1]
        extend_pop_for(pop_list,path)
        if len(path):
            append_to_inner(pop_list,(i[3].split('/')[-1],items.index(i)))
        else:
            pop_list.append((i[3].split('/')[-1],items.index(i)))


    r = Draw.PupTreeMenu(pop_list)
    if r >= 0:
        print items[r]
        set_pref_key('xplane.tools','annotate.last_item',items[r])
        cur = Window.GetCursorPos()
        mm = TranslationMatrix(Vector([0,0,0])).resize4x4()
        #mm = TranslationMatrix(Vector(Window.GetCursorPos())).resize4x4()
        importer=OBJimport(items[r][1],mm)
        importer.verbose=1
        try:
            sel = Blender.Scene.GetCurrent().objects.selected
            old_objs = set(Blender.Scene.GetCurrent().objects)
            obj_list = importer.doimport()
            new_objs = set(Blender.Scene.GetCurrent().objects)
            wrapper=Blender.Object.New('Empty','OBJ%s' % items[r][0].split('/')[-1])
            Blender.Scene.GetCurrent().objects.link(wrapper)
            added = new_objs-old_objs
            wrapper.makeParent(list(added),1,0)
            if len(sel) == 1:
                sel[0].makeParent([wrapper],1,0)
                base = sel[0].getLocation('worldspace')
                cur[0] -= base[0]
                cur[1] -= base[1]
                cur[2] -= base[2]
            wrapper.setLocation(cur[0], cur[1], cur[2])
            rel_path = items[r][0]
            if items[r][2]=='lcl':
                rel_path = make_relative_path(items[r][1],os.path.dirname(baseFileName))
            wrapper.addProperty('external',rel_path,'STRING')

            #for ob in obj_list:
            #	ob.setLocation(cur[0], cur[1], cur[2])

        except ParseError, e:
            Window.WaitCursor(0)
            Window.DrawProgressBar(0, 'ERROR')
            if e.type == ParseError.HEADER:
                msg='This is not a valid X-Plane v6, v7 or v8 OBJ file'
            elif e.type == ParseError.PANEL:
                msg='Cannot read cockpit panel texture'
            elif e.type == ParseError.NAME:
                msg='Missing dataref or light name at line %s\n' % obj.lineno
            elif e.type == ParseError.MISC:
                msg='%s at line %s' % (e.value, importer.lineno)
            else:
                thing=ParseError.TEXT[e.type]
                if e.value:
                    msg='Expecting a %s, found "%s" at line %s' % (thing, e.value, obj.lineno)
                else:
                    msg='Missing %s at line %s' % (thing, obj.lineno)
            print "ERROR:\t%s\n" % msg
            Draw.PupMenu("ERROR%%t|%s" % msg)
            Window.RedrawAll()
            Window.DrawProgressBar(1, 'ERROR')


    #print result
    Window.RedrawAll()
#Window.DrawProgressBar(1, 'ERROR')
except ExportError, e:
    print "%s" % e.msg
    Draw.PupMenu("ERROR: %s" % e.msg)
