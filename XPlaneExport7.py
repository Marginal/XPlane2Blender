#!BPY
""" Registration info for Blender menus:
Name: ' X-Plane v7 Object (.obj)'
Blender: 234
Group: 'Export'
Tooltip: 'Export to X-Plane v7 format object (.obj)'
"""
__author__ = "Jonathan Harris"
__url__ = ("Script homepage, http://marginal.org.uk/x-planescenery/")
__version__ = "2.05"
__bpydoc__ = """\
This script exports scenery created in Blender to X-Plane v7 .obj
format for placement with World-Maker.

Limitations:<br>
  * Only Lamps and Mesh Faces (including "lines") are exported.<br>
  * All faces must share a single texture (this is a limitation of<br>
    the X-Plane .obj file format) apart from cockpit panel faces<br>
    which can additionally use the cockpit panel texture. Multiple<br>
    textures are not automagically merged into one file during the<br>
    export.
"""

import Blender
from XPlaneExport import OBJexport, ExportError

if Blender.Window.EditMode():
    Blender.Draw.PupMenu("Please exit Edit Mode first.")
else:
    baseFileName=Blender.Get('filename')
    l = baseFileName.lower().rfind('.blend')
    if l!=-1:
        baseFileName=baseFileName[:l]

    obj=OBJexport(baseFileName+'.obj', 7)
    scene = Blender.Scene.getCurrent()
    try:
        obj.export(scene)
    except ExportError, e:
        Blender.Window.DrawProgressBar(1, "Error")
        msg="ERROR:\t"+e.msg+"\n"
        print msg
        Blender.Draw.PupMenu(msg)
        if obj.file:
            obj.file.close()
