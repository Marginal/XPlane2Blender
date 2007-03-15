#!BPY
""" Registration info for Blender menus:
Name: 'Copy & Paste'
Blender: 232
Group: 'UV'
Tooltip: 'Copy selected texture to other faces'
"""
#------------------------------------------------------------------------
# UV Copy & Paste for blender 2.34 or above
#
# Copyright (c) 2004 Jonathan Harris
# 
# Mail: <x-plane@marginal.org.uk>
# Web:  http://marginal.org.uk/x-planescenery/
#
# See XPlane2Blender.html for usage
#
# This software is provided 'as-is', without any express or implied
# warranty. In no event will the author be held liable for any damages
# arising from the use of this software.
# 
# Permission is granted to anyone to use this software for any purpose,
# including commercial applications, and to alter it and redistribute it
# freely, subject to the following restrictions:
# 
# 1. The origin of this software must not be misrepresented; you must
#    not claim that you wrote the original software. If you use this
#    software in a product, an acknowledgment in the product
#    documentation would be appreciated but is not required.
# 
# 2. Altered source versions must be plainly marked as such, and must
#    not be misrepresented as being the original software.
# 
# 3. This notice may not be removed or altered from any source
#    distribution.
#
# 2004-09-02 v1.70
#  - New file
#
# 2004-09-04 v1.71
#
# 2004-09-10 v1.72
#  - Checks that in strip mode pasted faces are in same mesh.
#


import Blender
from Blender import Object, NMesh, Draw, BGL

# Globals
face = 0
meshname = ""
copynorm = Draw.Create(1)
copystrp = Draw.Create(0)


# Are two vertices equal?
def veq (a, b):
    for i in range (3):
        if abs (a.co[i]-b.co[i]) > 0.01:
            return 0
    return 1


# O(n!) algorithm I think!
def mapstrip (oldface, faces):
    donefaces=[]
    n = len(oldface.v)
    for f in range (len (faces)):
        face=faces[f]
        if face and len(face.v)==n:
            # Do the faces have a common edge?
            for i in range (n):
                for j in range (n):
                    # Order of vertices is reversed in faces pointing same way
                    if (veq (face.v[i], oldface.v[j]) and
                        veq (face.v[(i+1)%n], oldface.v[(j-1)%n])):

                        # Copy the texture co-ords
                        for k in range (n):
                            face.uv[(i+k)%n] = oldface.uv[(j-k)%n]

                        # Both faces must have same flags to share in a strip
                        face.image  = oldface.image
                        face.mode   = oldface.mode
                        face.smooth = oldface.smooth
                        face.transp = oldface.transp

                        # Done this face - remove from list
                        faces[f]=0

                        # Recurse
                        mapstrip (face, faces)


# the function to handle Draw Button events
def bevent (evt):
    global face, meshname, copynorm, copystrp
    
    if evt == 1:
        Draw.Exit()

    elif evt == 3:
        copynorm.val = 1
        copystrp.val = 0
        Draw.Redraw()
        
    elif evt == 4:
        copynorm.val = 0
        copystrp.val = 1
        Draw.Redraw()
        
    elif evt == 2:
        if copystrp.val:	# Reverse faces
            objects = Blender.Object.GetSelected()
            if (len(objects) != 1 or
                objects[0].getType() != "Mesh" or
                objects[0].name != meshname):
                Draw.PupMenu("Please select faces only in the same mesh - %s." % meshname)
                return
    
            mesh = objects[0].getData()
            faces = mesh.getSelectedFaces()
            if len(faces) > 1024:
                # 1024 takes a reasonable time due to inefficiency of this
                # algorithm and doesn't overflow Python's recursion limit
                Draw.PupMenu("Please select at most 1024 faces.")
                return
    
            Blender.Window.WaitCursor(1)
            mapstrip (face, faces)
            mesh.update()

        else:	# Just map
            n = len(face.v)
            for ob in Blender.Object.GetSelected():
                mesh = ob.getData()
                if ob.getType() == "Mesh":
                    for newface in mesh.getSelectedFaces():
                        newface.image  = face.image
                        newface.mode   = face.mode
                        newface.smooth = face.smooth
                        newface.transp = face.transp
                        for k in range (n):
                            newface.uv[k] = face.uv[k]
                mesh.update()
                
        Draw.Exit()
        Blender.Redraw()


# the function to handle input events
def event (evt, val):
    if evt == Draw.ESCKEY and not val:
        Draw.Exit()                 # exit when user presses ESC


# the function to draw the screen
def gui():
    global copynorm, copystrp
    
    size=BGL.Buffer(BGL.GL_FLOAT, 4)
    BGL.glGetFloatv(BGL.GL_SCISSOR_BOX, size)
    size=size.list
    x=int(size[2])
    y=int(size[3])
    bkgnd=180.5/256
    header=165.5/256
    panel=192.5/256
    BGL.glClearColor (bkgnd, bkgnd, bkgnd, 1)
    BGL.glClear (BGL.GL_COLOR_BUFFER_BIT)
    BGL.glColor3f (header, header, header)
    BGL.glRectd(7, y-8, 295, y-26 )
    BGL.glColor3f (panel, panel, panel)
    BGL.glRectd(7, y-27, 295, y-130 )
    BGL.glColor3d (1, 1, 1)
    BGL.glRasterPos2d(16, y-22)
    Draw.Text("UV Copy & Paste")
    BGL.glColor3d (0, 0, 0)
    BGL.glRasterPos2d(16, y-48)
    Draw.Text("Select the faces to paint and then press Paste")
    BGL.glRasterPos2d(16, y-75)
    Draw.Text("Copy type:", "small")
    copynorm = Draw.Toggle("Normal", 3, 73, y-79, 51, 17, copynorm.val,
                           "Copy texture to selected faces in the same or a different mesh")
    copystrp = Draw.Toggle("Strip", 4, 124, y-79, 51, 17, copystrp.val,
                           "Reverse copied texture as necessary to make a strip in the same mesh")
    Draw.Button("Paste", 2, 14, y-120, 100, 26)
    Draw.Button("Cancel", 1, 187, y-120, 100, 26)
  

#------------------------------------------------------------------------
# main routine
#------------------------------------------------------------------------
class StripError(Exception):
    def __init__(self, msg):
        self.msg = msg

try:
    if Blender.Get('version') < 234:
        raise StripError("Requires Blender version 2.34 or later.")

    if Blender.Window.EditMode():
        raise StripError("Please enter UV Face Select mode first.")
    
    objects = Blender.Object.GetSelected ()
    if len(objects) != 1:
        raise StripError("Please select one face in one mesh.")
                     
    ob = objects[0]
    if ob.getType() != "Mesh":
        raise StripError("Selected object is not a Mesh.")

    mesh = ob.getData()
    meshname = ob.name
    faces = mesh.getSelectedFaces ()
    if len (faces) != 1:
        raise StripError("Please select exactly one face.")

    face = faces[0]
    if not (mesh.hasFaceUV() or (face.mode & NMesh.FaceModes.TEX)):
        raise StripError("Selected face doesn't have a texture.")

    # 'Hard' faces can't be in a strip
    face.mode |= NMesh.FaceModes.DYNAMIC
    mesh.update()

    Draw.Register (gui, event, bevent)

except StripError, e:
    Draw.PupMenu ("ERROR:\t" + e.msg)
