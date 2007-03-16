#!BPY
""" Registration info for Blender menus:
Name: 'X-Plane v7 Object (.obj)'
Blender: 240
Group: 'Export'
Tooltip: 'Export to X-Plane v7 format object (.obj)'
"""
__author__ = "Jonathan Harris"
__email__ = "Jonathan Harris, Jonathan Harris <x-plane:marginal*org*uk>"
__url__ = "XPlane2Blender, http://marginal.org.uk/x-planescenery/"
__version__ = "2.35"
__bpydoc__ = """\
This script exports scenery created in Blender to X-Plane v7 .obj
format for placement with World-Maker.

Limitations:<br>
  * Only Lamps and Meshes (including "lines") are exported.<br>
  * All faces must share a single texture (this is a limitation of<br>
    the X-Plane .obj file format) apart from cockpit panel faces<br>
    which can additionally use the cockpit panel texture. Multiple<br>
    textures are not automagically merged into one file during the<br>
    export.
"""

#------------------------------------------------------------------------
# X-Plane exporter for blender 2.34 or above
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
baseFileName=Blender.Get('filename')
l = baseFileName.lower().rfind('.blend')
if l!=-1:
    baseFileName=baseFileName[:l]

obj=OBJexport7(baseFileName+'.obj', __version__, False)
scene = Blender.Scene.GetCurrent()
try:
    obj.export(scene)
except ExportError, e:
    Window.WaitCursor(0)
    Window.DrawProgressBar(0, 'ERROR')
    for o in scene.getChildren(): o.select(0)
    if e.objs:
        layers=[]
        for o in e.objs:
            o.select(1)
            for layer in o.layers:
                if layer<=3 and not layer in layers: layers.append(layer)
        Window.ViewLayers(layers)
        Window.RedrawAll()
    print "ERROR:\t%s\n" % e.msg
    Draw.PupMenu("ERROR: %s" % e.msg)
    Window.DrawProgressBar(1, 'ERROR')
    if obj.file: obj.file.close()

