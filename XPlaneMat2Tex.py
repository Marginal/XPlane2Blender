#!BPY
""" Registration info for Blender menus:
Name: 'Material to TexFace'
Blender: 249
Group: 'Image'
Tooltip: 'Copy the material texture to the face texture'
"""
__author__ = "Ben Supnik"
__email__ = "Ben Supnik, Ben Supnik <bsupnik:xsquawkbox*net>"
__url__ = "developer.x-plane.com"
__version__ = "3.11"
__bpydoc__ = """\

"""

#
# Copyright (c) 2012-2013 Ben Supnik
#
# This code is licensed under version 2 of the GNU General Public License.
# http://www.gnu.org/licenses/gpl-2.0.html
#
# See ReadMe-XPlane2Blender.html for usage.
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
