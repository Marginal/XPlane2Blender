#!BPY
""" Registration info for Blender menus:
Name: ' X-Plane Plane as scenery (.acf)...'
Blender: 234
Group: 'Import'
Tooltip: 'Import an X-Plane airplane (.acf)'
"""
__author__ = "Jonathan Harris"
__url__ = ("Script homepage, http://marginal.org.uk/x-planescenery/")
__version__ = "2.16"
__bpydoc__ = """\
This script imports X-Plane v7 and v8 airplanes into Blender, so that
they can be exported as X-Plane scenery.

Planes are imported with three levels of detail to maximise rendering
speed in X-Plane.

Limitations:<br>
  * Imported planes usually use two or more textures. All faces<br>
    must be made to share a single texture before export. (This is<br>
    a limitation of the X-Plane .obj file format).<br>
  * v6 planes are not supported. Convert v6 planes to v7 or v8<br>
    format in Plane Maker first.<br>
"""

import Blender
from XPlaneACF import ACFimport, ParseError

#------------------------------------------------------------------------
def file_callback (filename):
    print "Starting ACF import from " + filename
    Blender.Window.DrawProgressBar(0, "Opening ...")
    try:
        acf=ACFimport(filename, 1)
    except ParseError:
        Blender.Window.DrawProgressBar(1, "Error")
        print("ERROR:\tThis isn't a v7 or v8 X-Plane file!")
        Blender.Draw.PupMenu("ERROR:\tThis isn't a v7 or v8 X-Plane file!")
        return
    acf.doImport()
    Blender.Window.DrawProgressBar(1, "Finished")
    print "Finished\n"
    Blender.Redraw()


#------------------------------------------------------------------------
# main routine
#------------------------------------------------------------------------

Blender.Window.FileSelector(file_callback,"IMPORT .ACF")
