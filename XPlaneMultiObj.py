#!BPY
""" Registration info for Blender menus:
Name: 'X-Plane Object Bulk Export (.obj)'
Blender: 245
Group: 'Export'
Tooltip: 'Export a scene to multiple objects.'
"""
__author__ = "Ben Supnik"
__email__ = "Ben Supnik, Ben Supnik <bsupnik:xsquawkbox*net>"
__url__ = "developer.x-plane.com"
__version__ = "3.11"
__bpydoc__ = """\
This script exports multiple OBJs from a Blender scene.
"""

#
# Copyright (c) 2012-2013 Ben Supnik
#
# This code is licensed under version 2 of the GNU General Public License.
# http://www.gnu.org/licenses/gpl-2.0.html
#
# See ReadMe-XPlane2Blender.html for usage.
#

from XPlaneExport8_util import *
from XPlaneUtils import *
from XPlaneExport import ExportError
from XPlaneLib import *

def export_hier(parent, all,root,depth):
    total = 0
    kids=getChildren(parent, all)
    objs = filter_objects(kids,'Empty','OBJ')
    objs += filter_objects(kids,'Empty','VRT')
    objs += filter_objects(kids,'Empty','END')
    objs += filter_objects(kids,'Empty','BGN')

    grps = filter_objects(kids,'Empty','GRP')
    for g in grps:
        total = total + export_hier(g, all,root,depth+1)

    # Alex does NOT want the outer-most OBJs to be exported.  His projects
    # apparently contain lots of random objects floating around.
    # This if statement could be nuked to restore the old behavior.
    # The current impl lets free objects out if there simply are no groups.

    #if depth > 0:					#This would STRICTLY skip free objs.
    if depth > 0 or len(grps) == 0:			#This takes free objs if there are no groups.
        for o in objs:
            n = strip_suffix(o.name)[3:]
            n = get_prop(o,'rname',n)
            n += '.obj'
            partial = get_prop(o,'path','.')
            export_path=os.path.join(partial,n)
            export_path=os.path.join(root,export_path)
            if not os.path.exists(os.path.dirname(export_path)):
                os.makedirs(os.path.dirname(export_path))
            try:
                (sim,pack)=locate_root(export_path)
            except ExportError, e:
                pack=None
            exporter=OBJexport8(export_path)
            exporter.additive_lod=1
            my_parts=getGrandChildren(o,all)
            #if self.debug:
            #	for p in my_parts:
            #		print " object export %s will export DB %s" % (oname, p.name)
            prefix = ''
            parts = partial.count('/') + 1
            if partial == '.': parts = 0
            for n in range(parts):
                prefix += '../'
            exporter.openFile(my_parts,o,prefix)
            exporter.writeHeader()
            if has_prop(o,'vname'):
                if pack == None:
                    raise ExportError("Illegal vname directive on %s - blender file is not in a scenery pack." % o.name)
                exporter.file.write("EXPORT %s.obj %s\n" % (strip_suffix(get_prop(o,'vname',o.name)),os.path.normpath(export_path[len(pack)+1:])))
            if has_prop(o,'vname1'):
                exporter.file.write("EXPORT %s.obj %s\n" % (strip_suffix(get_prop(o,'vname1',o.name)),os.path.normpath(export_path[len(pack)+1:])))
            if has_prop(o,'vname2'):
                exporter.file.write("EXPORT %s.obj %s\n" % (strip_suffix(get_prop(o,'vname2',o.name)),os.path.normpath(export_path[len(pack)+1:])))
            exporter.writeObjects(my_parts)
            total = total + 1
    return total
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

    count = export_hier(None, scene.objects,path,0)
    Draw.PupMenu("Export complete: %d objects." % count)

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
