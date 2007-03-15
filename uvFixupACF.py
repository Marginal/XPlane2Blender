#!BPY
""" Registration info for Blender menus:
Name: 'Merge _paint and _paint2'
Blender: 234
Group: 'UV'
Tooltip: 'Merge X-Plane plane_paint and plane_paint2 bitmaps'
"""
__author__ = "Jonathan Harris"
__url__ = ("Script homepage, http://marginal.org.uk/x-planescenery/")
__version__ = "2.32"
__bpydoc__ = """\
This script fixes up an imported plane's texture assignments to use
a single bitmap file.

Usage:<br>
  * Create a new texture bitmap with plane_paint on the left
    and plane paint2 on the right.<br>
  * Save the new texture bitmap as a PNG with the same name
    as the blend file.<br>
  * Run this script from the UVs menu in the UV/Image Editor<br>
    window.<br>
"""

#------------------------------------------------------------------------
# UV Resize for blender 2.34 or above
#
# Copyright (c) 2005 Jonathan Harris
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
# 2006-04-07 v2.20
#  - New file
#

import Blender
from Blender import Draw, Image, Scene, NMesh
from os.path import splitext

(newfile,ext)=splitext(Blender.Get('filename'))
for ext in ['.png', '.PNG', '.bmp', '.BMP']:
    try:
        tex=Image.Load(newfile+ext)
        dim=tex.getSize()

        objects = Scene.getCurrent().getChildren()
        for ob in objects:
            if ob.getType() == "Mesh" and ob.getData().hasFaceUV():
                mesh = ob.getData()
                for face in mesh.faces:
                    if face.mode & NMesh.FaceModes.TEX and face.image:
                        oldfile=face.image.filename.lower()
                        if '_paint.' in oldfile:
                            for i in range(len(face.uv)):
                                (s,t)=face.uv[i]
                                face.uv[i]=(s/2, t)
                                face.image=tex
                        elif '_paint2.' in oldfile:
                            for i in range(len(face.uv)):
                                (s,t)=face.uv[i]
                                face.uv[i]=(0.5+s/2, t)
                                face.image=tex
                ob.setName(ob.name.replace('*',''))
                mesh.name=mesh.name.replace('*','')
                mesh.update()

        Blender.Redraw()
        break

    except (RuntimeError, IOError):
        pass

else:
    msg='Can\'t load texture file %s.png or .bmp' % newfile
    print "ERROR:\t%s\n" % msg
    Draw.PupMenu("ERROR: %s" % msg)

