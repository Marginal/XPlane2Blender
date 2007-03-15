#!BPY
""" Registration info for Blender menus:
Name: 'Double bitmap size'
Blender: 234
Group: 'UV'
Tooltip: 'Adjust textures to enlarged bitmap'
"""
__author__ = "Jonathan Harris"
__url__ = ("Script homepage, http://marginal.org.uk/x-planescenery/")
__version__ = "2.34"
__bpydoc__ = """\
This script fixes up selected meshes' texture assignments after doubling
the size of the bitmap file.

Usage:<br>
  * Double the size of the texture bitmap file in an image editor.<br>
  * Use Image->Reload to load the resized bitmap.<br>
  * Select a mesh or meshes.<br>
  * Run this script from the UVs menu in the UV/Image Editor<br>
    window.<br>
  * Choose the location of the textures in the bitmap file.<br>
  * Press the Resize button.<br>
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
# 2005-03-02 v2.00
#  - New file
#

import Blender
from Blender import Object, NMesh, Draw, BGL

# Globals
buttons=[]
for i in range(8):
    buttons.append(Draw.Create(0))
scale=[
    #smul, tmul, soff, toff
    (0.5,   1,   0,   0),
    (0.5,   1, 0.5,   0),
    (  1, 0.5,   0, 0.5),
    (  1, 0.5,   0,   0),
    (0.5, 0.5,   0, 0.5),
    (0.5, 0.5, 0.5, 0.5),
    (0.5, 0.5,   0,   0),
    (0.5, 0.5, 0.5,   0)]


# the function to handle Draw Button events
def bevent (evt):
    global buttons, scale

    if evt==101:
        Draw.Exit()

    elif evt==100:
        for i in range(len(buttons)):
            if buttons[i].val:
                (smul, tmul, soff, toff) = scale[i]
                break
        else:
            return

        objects = Blender.Object.GetSelected()
        for ob in objects:
            if ob.getType() == "Mesh":
                mesh = ob.getData()
                if mesh.hasFaceUV():
                    for face in mesh.faces:
                        if face.mode & NMesh.FaceModes.TEX:
                            for i in range(len(face.uv)):
                                (s,t)=face.uv[i]
                                face.uv[i]=(soff+s*smul, toff+t*tmul)
                    mesh.update()

        Draw.Exit()
        Blender.Window.Redraw(-1)

    else:
        for b in buttons:
            b.val=0
        buttons[evt-1].val=1
        Draw.Redraw()


# the function to handle input events
def event (evt, val):
    if evt == Draw.ESCKEY and not val:
        Draw.Exit()                 # exit when user presses ESC


# the function to draw the screen
def gui():
    global buttons

    size=BGL.Buffer(BGL.GL_FLOAT, 4)
    BGL.glGetFloatv(BGL.GL_SCISSOR_BOX, size)
    size=size.list
    x=int(size[2])
    y=int(size[3])

    # Default theme
    text   =[  0,   0,   0, 255]
    text_hi=[255, 255, 255, 255]
    header =[195, 195, 195, 255]
    panel  =[255, 255, 255,  40]
    back   =[180, 180, 180, 255]

    # Actual theme
    if Blender.Get('version') >= 235:
        theme=Blender.Window.Theme.Get()
        if theme:
            theme=theme[0]
            text=theme.get('ui').text
            space=theme.get('buts')
            text_hi=space.text_hi
            header=space.header
            panel=space.panel
            back=space.back

    BGL.glEnable (BGL.GL_BLEND)
    BGL.glBlendFunc (BGL.GL_SRC_ALPHA, BGL.GL_ONE_MINUS_SRC_ALPHA)
    BGL.glClearColor (float(back[0])/255, float(back[1])/255,
                      float(back[2])/255, 1)
    BGL.glClear (BGL.GL_COLOR_BUFFER_BIT)
    BGL.glColor4ub (max(header[0]-30, 0),	# 30 appears to be hard coded
                    max(header[1]-30, 0),
                    max(header[2]-30, 0),
                    header[3])
    BGL.glRectd(7, y-8, 295, y-28)
    BGL.glColor4ub (panel[0], panel[1], panel[2], panel[3])
    BGL.glRectd(7, y-28, 295, y-152)
    BGL.glColor4ub (text_hi[0], text_hi[1], text_hi[2], text_hi[3])
    BGL.glRasterPos2d(16, y-23)
    Draw.Text("UV Resize")
    BGL.glColor4ub (text[0], text[1], text[2], text[3])
    BGL.glRasterPos2d(16, y-48)
    Draw.Text("Select the location of the textures in the new")
    BGL.glRasterPos2d(16, y-62)
    Draw.Text("bitmap and press Resize")

    buttons[0]=Draw.Toggle(" ", 1, 24,  y-90,  14, 14, buttons[0].val)
    buttons[1]=Draw.Toggle(" ", 2, 38,  y-90,  14, 14, buttons[1].val)

    buttons[2]=Draw.Toggle(" ", 3, 80,  y-90,  14, 14, buttons[2].val)
    buttons[3]=Draw.Toggle(" ", 4, 80,  y-104, 14, 14, buttons[3].val)

    buttons[4]=Draw.Toggle(" ", 5, 122, y-90,  14, 14, buttons[4].val)
    buttons[5]=Draw.Toggle(" ", 6, 136, y-90,  14, 14, buttons[5].val)
    buttons[6]=Draw.Toggle(" ", 7, 122, y-104, 14, 14, buttons[6].val)
    buttons[7]=Draw.Toggle(" ", 8, 136, y-104, 14, 14, buttons[7].val)

    Draw.Button("Cancel", 101, 187, y-142, 100, 26)
    Draw.Button("Resize", 100, 14, y-142, 100, 26)


#------------------------------------------------------------------------
# main routine
#------------------------------------------------------------------------

Draw.Register (gui, event, bevent)
