#!BPY
""" Registration info for Blender menus:
Name: 'X-Plane Object (.obj)'
Blender: 245
Group: 'Export'
Tooltip: 'Export to X-Plane object'
"""
__author__ = "Jonathan Harris"
__email__ = "Jonathan Harris, Jonathan Harris <x-plane:marginal*org*uk>"
__url__ = "XPlane2Blender, http://marginal.org.uk/x-planescenery/"
__version__ = "3.11"
__bpydoc__ = """\
This script exports to X-Plane v8, v9 or v10 object format.
"""

#
# Copyright (c) 2007 Jonathan Harris
#
# This code is licensed under version 2 of the GNU General Public License.
# http://www.gnu.org/licenses/gpl-2.0.html
#
# See ReadMe-XPlane2Blender.html for usage.
#

from XPlaneExport8_util import *
from XPlaneUtils import *

#------------------------------------------------------------------------
if Window.EditMode(): Window.EditMode(0)
try:
    obj=None
    sl = Blender.Scene.Get()

    scene = Blender.Scene.GetCurrent()

    baseFileName=Blender.Get('filename')
    l = baseFileName.lower().rfind('.blend')
    if l==-1: raise ExportError('Save this .blend file first')
    baseFileName=baseFileName[:l]

    if len(sl) > 1 and scene.getName() != 'Scene':
        scene_name = scene.getName()
        if scene_name[-4:].lower() == '.obj':
            scene_name = scene_name[:-4]
        baseFileName = os.path.dirname(baseFileName)
        baseFileName = os.path.join(baseFileName,scene_name)

    obj=OBJexport8(baseFileName+'.obj')
    obj.export(scene)
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
