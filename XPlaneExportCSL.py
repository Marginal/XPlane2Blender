#!BPY
""" Registration info for Blender menus:
Name: ' X-Plane CSL Object (.obj)'
Blender: 240
Group: 'Export'
Tooltip: 'Export to X-Plane CSL format object (.obj)'
"""
__author__ = "Jonathan Harris"
__url__ = ("Script homepage, http://marginal.org.uk/x-planescenery/")
__version__ = "2.24"
__bpydoc__ = """\
This script exports scenery created in Blender to X-Plane CSL .obj
format for use with XSquawkbox.

Limitations:<br>
  * Only Lamps and Meshes are exported.<br>
  * All faces must share a single texture (this is a limitation of<br>
    the X-Plane .obj file format). Multiple textures are not<br>
    automagically merged into one file during the export.
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
#   Attribution-ShareAlike 2.0:
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
#   http://creativecommons.org/licenses/by-sa/2.0/legalcode
#
#

import Blender
from XPlaneExport import OBJexport7, ExportError

#------------------------------------------------------------------------
if Blender.Window.EditMode():
    Blender.Draw.PupMenu("Please exit Edit Mode first.")
else:
    baseFileName=Blender.Get('filename')
    l = baseFileName.lower().rfind('.blend')
    if l!=-1:
        baseFileName=baseFileName[:l]

    obj=OBJexport7(baseFileName+'.obj', __version__, True)
    scene = Blender.Scene.getCurrent()
    try:
        obj.export(scene)
    except ExportError, e:
        Blender.Window.WaitCursor(0)
        Blender.Window.DrawProgressBar(0, 'ERROR')
        print "ERROR:\t%s\n" % e.msg
        Blender.Draw.PupMenu("ERROR: %s" % e.msg)
        Blender.Window.DrawProgressBar(1, 'ERROR')
        if obj.file:
            obj.file.close()
