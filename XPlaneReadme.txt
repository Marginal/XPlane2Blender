XPlane2Blender - X-Plane import/export scripts for Blender 3D
-------------------------------------------------------------

Author: 	Jonathan Harris <x-plane@marginal.org.uk>
Version:	1.0
Latest version:	http://marginal.org.uk/x-plane

Requirements:	Blender 2.3 or later <http://www.blender3d.org/Download/>
		Python 2.2 <http://www.python.org/2.2.3/> (Blender 2.3
		does not support Python 2.3 at time or writing).


Blender is an open source 3D object editor <http://www.blender3d.org/>.
These scripts import X-Plane v6 and v7 scenery files (.obj) into Blender
for editing, and export back to X-Plane v7 obj format for placement with
World-Maker. All X-Plane object types are supported apart from Line,
Smoke_Black and Smoke_White (none of which are directly representable in
Blender).


Importing
---------
Open XPlaneImport.py in a Blender text window. Hit Alt-P to run. Select
a .obj file. Any problems with the import will be listed in the console
window with lines starting "Warn" or "Error".

You can import multiple scenery files and re-export them as a single
file. But note that the X-Plane .obj file format only supports one
texture, so you'll have to create a single texture bitmap (x and y sizes
must be a power of two) and remap all the object textures onto it before
exporting.


Exporting
---------
Open XPlaneExport.py in a Blender text window. Hit Alt-P to run. The
output filename is the same as the current Blender filename, but with a
.obj extension. Any problems with the export will be listed in the
console window with lines starting "Warn" or "Error".


Using Blender to create X-Plane scenery
---------------------------------------
Use Lamps and Meshes. No other Blender object types are exported.

Lamps:
 - R,G,B settings are exported to X-Plane. All other settings (including
   "Energy") are ignored.
 - Lamp types "Spot", "Semi" and "Hemi" are not exported. You can use
   lamps of these types to provide general illumination of your scene.
 - Lamps with certain names have special meanings to X-Plane:
    "Flash"   - Light flashes.
    "Pulse"   - Red pulsing light. (R,G,B settings are ignored).
    "Strobe"  - White strobe light. (R,G,B settings are ignored).
    "Traffic" - Cycles red, orange, green. (R,G,B settings are ignored).

Meshes:
 - Use faces with 3 or 4 edges.
 - In the "Texture Face" panel (available in "UV Face Select" mode):
    - "Tex" button controls whether the face has a texture. Use a
      "UV Image Editor" window to control mapping of the texture to the
      face.
    - "Collision" button controls whether the face is "hard" (ie
      landable on) in X-Plane.
    - "Tiles" button turns off depth-testing. Use this for all
      horizontal faces to prevent nasty display artifacts in X-Plane.
 - In the "Link and Materials" panel:
    - "Set Smooth" and "Set Solid" control whether to smooth edges.
      Useful when using faces to simulate a curved surface - set smooth
      on each face. The effect is only visible in Blender when the
      smoothed faces are part of the same mesh, and only in the Render
      window.


Random hints
------------
Blender has a quirky user interface:
 - Right mouse button does what you would expect Left mouse button to do
 - Space does what you would expect Right mouse button to do
 - The user interface is "modal". Buttons and keys do different things
   depending on whether you are in "Object", "Edit" or "UV Face Select"
   mode. (And I thought modal UIs went out with "vi"). Tab changes mode.
You get used to the mode thing. Sadly, I'm not aware of any way to remap
the button and key assignments, which remain annoying.

Import "Custom Scenery\San Bernardino Example\custom objects\KSBD_example.obj"
to play with an example X-Plane object.

See http://www.blender3d.org/Education/ for some tutorials to help you
get started. 

X-Plane only renders one side of an object's face, so don't make double-
sided faces in Blender or you'll just get confused. In order to see
which side of a face is the visible side:
 - Go to Edit mode (you need to have an object selected to do this).
 - Hit F9 to see the "Editing" buttons.
 - Select "Draw Normals" and set "NSize" to at least 1.0 in the
   "Mesh Tools 1" panel. (I also like to select "Draw Faces" and
   "Draw Edges", but that's up to you).
When in edit mode, faces are now drawn with a short light blue line
coming from their centre. The visible side of the face is the side that
you are looking at when the line is pointing _towards_ you.

Mail me <x-plane@marginal.org.uk> with any questions, problems etc.


Limitations
-----------
Import:
 - Line, Smoke_Black and Smoke_White objects are ignored.
 - Ambient, Difuse, Specular, Emission and Shiny attributes are ignored.
 - Level-of-detail is not supported. Any objects that are only visible
   from a non-zero distance are ignored.
Export:
 - All objects must share a single texture (this is a limitation of the
   X-Plane .obj file format).
 - No use is made of the more efficient Quad_Strip and Tri_Fan objects.

