#!BPY
""" Registration info for Blender menus:
Name: 'Material to TexFace'
Blender: 249
Group: 'Image'
Tooltip: 'Copy the material texture to the face texture'
"""
__author__ = "Ben Supnik"
__email__ = "bsunpik at xsquawkbox dot noet"
__url__ = "wiki.x-plane.com"
__version__ = "3.09"
__bpydoc__ = """\

"""

#------------------------------------------------------------------------
# UV Resize for blender 2.43 or above
#
# Copyright (c) 2006,2007 Jonathan Harris
#
# Mail: <x-plane@marginal.org.uk>
# Web:  http://marginal.org.uk/x-planescenery/
#
# See XPlane2Blender.html for usage.
#
# This software is licensed under a Creative Commons License
#   Attribution-Noncommercial-Share Alike 3.0:
#
#   You are free:
#    * to Share - to copy, distribute and transmit the work
#    * to Remix - to adapt the work
#
#   Under the following conditions:
#    * Attribution. You must attribute the work in the manner specified
#      by the author or licensor (but not in any way that suggests that
#      they endorse you or your use of the work).
#    * Noncommercial. You may not use this work for commercial purposes.
#    * Share Alike. If you alter, transform, or build upon this work,
#      you may distribute the resulting work only under the same or
#      similar license to this one.
#
#   For any reuse or distribution, you must make clear to others the
#   license terms of this work.
#
# This is a human-readable summary of the Legal Code (the full license):
#   http://creativecommons.org/licenses/by-nc-sa/3.0/
#
#
# 2006-04-07 v2.20
#  - New file
#
# 2007-10-16 v2.45
#  - Fix for Blender 2.45
#
# 2008-04-08 v3.09
#  - Fix for break in version 3.03
#

import Blender
from Blender import Draw, Image, Scene, Window, Material, Texture, Object, NMesh

try:
    for ob in Scene.GetCurrent().objects:
        if ob.getType() == "Mesh":
            #print "Mesh %s " % ob.name
            mesh = ob.getData()
            changed = False
            for face in mesh.faces:
                #print "face with"
                if face.mode & NMesh.FaceModes.TEX and face.image:
                    #print "   %s" % face.image.name
                    wanted = mesh.materials[face.mat].textures[0].tex.image
                    has = face.image
                    #print "  but wanted %s %s" % (mesh.materials[face.mat].name, wanted.name)
                    if has != wanted:
                        print "Using %s but should have had (%s) %s" % (has.name, wanted.name, mesh.materials[face.mat].name)
                        face.image = wanted
                        changed = True
            if changed:
                mesh.update()


    Window.RedrawAll()

except (RuntimeError, IOError):
    print "ERROR"
#    msg='Can\'t load texture file %s.png or .bmp' % newfile
##   print "ERROR:\t%s\n" % msg
#    Draw.PupMenu("ERROR: %s" % msg)
