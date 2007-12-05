#!BPY
""" Registration info for Blender menus:
Name: 'X-Plane CSL Object (.obj)'
Blender: 243
Group: 'Export'
Tooltip: 'Export to X-Plane CSL format object (.obj)'
"""
__author__ = "Jonathan Harris"
__email__ = "Jonathan Harris, Jonathan Harris <x-plane:marginal*org*uk>"
__url__ = ["XPlane2Blender, http://marginal.org.uk/x-planescenery/",
           "X-IvAp, http://www.ivao.aero/softdev/X-IvAp/"]
__version__ = "3.01"
__bpydoc__ = """\
This script exports scenery created in Blender to X-Plane CSL .obj
format for use with XSquawkbox and X-IvAp.

Limitations:<br>
  * Only Lamps and Meshes are exported.<br>
  * All faces must share a single texture (this is a limitation of<br>
    the X-Plane .obj file format). Multiple textures are not<br>
    automagically merged into one file during the export.
"""

#------------------------------------------------------------------------
# X-Plane exporter for blender 2.43 or above
#
# Copyright (c) 2004,2005 Jonathan Harris
# 
# Mail: <x-plane@marginal.org.uk>
# Web:  http://marginal.org.uk/x-planescenery/
#
# See XPlane2Blender.html for usage.
#
# This software is licensed under a Creative Commons License
#   Attribution-ShareAlike 2.5:
#
#   You are free:
#     * to copy, distribute, display, and perform the work
#     * to make derivative works
#     * to make commercial use of the work
#   Under the following conditions:
#     * Attribution: You must give the original author credit.
#     * Share Alike: If you alter, transform, or build upon this work, you
#       may distribute the resulting work only under a license identical to
#       this one.
#   For any reuse or distribution, you must make clear to others the license
#   terms of this work.
#
# This is a human-readable summary of the Legal Code (the full license):
#   http://creativecommons.org/licenses/by-sa/2.5/legalcode
#
#

import Blender
from Blender import Draw, Window
from XPlaneExport import OBJexport7, ExportError

if Window.EditMode(): Window.EditMode(0)
try:
    obj=None
    scene = Blender.Scene.GetCurrent()

    baseFileName=Blender.Get('filename')
    l = baseFileName.lower().rfind('.blend')
    if l==-1: raise ExportError('Save this .blend file first')
    baseFileName=baseFileName[:l]
    obj=OBJexport7(baseFileName+'.obj', __version__, True)
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
