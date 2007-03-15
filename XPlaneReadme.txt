XPlane2Blender - X-Plane import/export scripts for Blender 3D
-------------------------------------------------------------

Author: 	Jonathan Harris <x-plane@marginal.org.uk>
Version:	1.30
Latest version:	http://marginal.org.uk/x-planescenery/


Blender is an open source 3D object editor - http://www.blender3d.org/.
These Blender scripts export scenery created in Blender to X-Plane v7
.obj format for placement with World-Maker. The scripts also import
existing X-Plane v6 and v7 .obj scenery files into Blender. All X-Plane
object types are supported apart from Smoke_Black and Smoke_White
(which are not directly representable in Blender).


Requirements
------------
Blender 2.32 or later - http://www.blender3d.org/Download/


Installation
------------
Unpack the zip file to the folder containing your Blender scripts:

Windows:
 - C:\Program Files\Blender Foundation\Blender\.blender\scripts
   (assuming that you installed Blender to the default location).

Mac OS X:
 - /users/<you>/.blender/scripts
   (assuming that your home directory is in the default place).
   You will need to first create the last two sub-folders of that path:
   Run the Terminal app, and type mkdir ~/.blender/scripts

(Re)start Blender.
On Mac OS, also run the "Console" program that comes with Mac OS X and
which is found under "Utilities".

The scripts are run by choosing File -> Import -> X-Plane or
File -> Export -> X-Plane in Blender. (Some users report that X-Plane
doesn't appear under File->Import and/or File->Export on their machine.
The scripts can also be run another way - open XPlaneImport.py or
XPlaneExport.py in a Blender text window. Hit Alt-P to run).


Importing
---------
File -> Import -> X-Plane
Select a .obj file. The scenery is imported at the "3d Cursor" position.
Any problems with the import will be reported in the Console window as
lines starting "Warn" or "Error". The script works quite hard to
optimise for ease and speed of editing in Blender, so can be slow to
import large scenery.

You can import multiple scenery files and re-export them as a single
file. But note that the X-Plane .obj file format only supports the use
of one texture bitmap, so you'll have to create a single texture bitmap
file and remap all the scenery textures onto it before exporting.


Exporting
---------
File -> Export -> X-Plane
The output filename and location is the same as the current Blender
filename, but with a .obj extension. Always check the Console window for
messages reporting any problems with the export, which are displayed as
lines starting "Warn" or "Error".


Using Blender to create X-Plane scenery
---------------------------------------
Create a new folder under "Custom Scenery" in the X-Plane folder with
the name of the scenery collection that you're making. Create two
subfolders of this folder, named "custom objects" and
"custom object textures".
Save your Blender file in the "custom objects" folder with a descriptive
name, eg
  X-System 730\Custom Scenery\London\custom objects\house.blend
The X-Plane .obj file will be exported to the same place, eg
  X-System 730\Custom Scenery\London\custom objects\house.obj

Use Lamps and Meshes to construct your scenery. No other Blender object
types are exported.

Lamps:
 - R,G,B settings are exported to X-Plane. All other settings (including
   "Energy") are ignored.
 - Only Lamps of type "Lamp" are exported to X-Plane. Lamps of types
   "Area", "Spot", "Semi" and "Hemi" are ignored. You can use lamps of
   these other types to provide general illumination of your scene while
   editing in Blender.
 - Lamps with certain names have special behaviours when exported to
   X-Plane:
    "Flash"   - Light flashes.
    "Pulse"   - Red pulsing light. (R,G,B settings are ignored).
    "Strobe"  - White strobe light. (R,G,B settings are ignored).
    "Traffic" - Cycles red, orange, green. (R,G,B settings are ignored).

Meshes:
 - Create faces with 3 or 4 edges (called 'Tri's and 'Quad's in X-Plane).
 - In the "Texture Face" panel (available in "UV Face Select" mode):
    - "Tex" button controls whether the face has a texture.
      Create a .bmp or .png file in an image editor program in the
      "custom object textures" folder. Height and width must be powers
      of two (eg 256, 512, etc). Draw all the textures required by the
      scenery onto it. Areas of the texture that are coloured magenta or
      that have Alpha transparency (png files only) will be transparent
      when displayed in X-Plane.
      Use a "UV Image Editor" window to control mapping of the texture
      bitmap to the face.
    - "Collision" button controls whether the face is "hard" (ie
      landable on) in X-Plane. This only works for faces with 4 edges.
      Blender adds new faces with "Collision" on by default. Turn this
      off for faces that don't need it to speed up rendering in X-Plane.
    - "Tiles" button turns off depth-testing. Use this for horizontal
      faces to prevent nasty artifacts when displayed in X-Plane.
 - In the "Link and Materials" panel:
    - "Set Smooth" and "Set Solid" control whether to smooth edges of
      faces in a mesh. This is useful when using multiple faces to
      simulate a curved surface; go to "Object Mode", select the mesh
      and press "Set Smooth".
      The effect is only visible in Blender "3D View" windows when the
      "Viewport Shading" button is set to "Solid" or "Shaded", and in
      the "Render" window.
      Blender allows you (in "Edit Mode") to "Set Smooth" on individual
      faces. Don't do that - the results when exported to X-Plane are
      undefined. "Set Smooth" or "Set Solid" on the whole mesh instead.

Lines:
 - Blender doesn't support Lines directly. Use a mesh with one 4-edged
   face instead. The pair of vertices at each end of the 'line' must be
   within 0.1 units of each other. The face must be the only face in its
   mesh and must not have a texture assigned to it.
   To colour the 'line', assign a Material to the face and set the
   Material's "Basic Colour" RGB values. Faces not linked to a Material
   will be exported coloured grey.


Optimising scenery for X-Plane
------------------------------
As well as basic 3- and 4-edged faces ('Tri's and 'Quad's), X-Plane
supports two compound types - 'Tri_Fan' and 'Quad_Strip'. These are
strips of two or more 'Tri's and 'Quad's that share common edges.
Because the faces in these strips share common edges, X-Plane and the
underlying OpenGL renderer have to do a third or a half as much work to
render them compared to individual 'Tri's and 'Quad's. This gives higher
frame rates.

In order for a pair of faces to be considered for inclusion in one of
these strips, the following conditions need to be true:
 - The faces must be part of the same mesh.
 - The faces must be facing the same way (eg both on the outside of a
   cube).
 - The faces must share a common edge.
 - The shared edge must have the same texture bitmap co-ordinates in
   both faces. In practice this means that the texture must be reversed
   in alternate faces in the strip. In the case of 'Tri's this can also
   be achieved by mapping a single area of the texture across all the
   'Tri's, with the tip of the 'Tri's at the centre of the texture area.
   Import KBSD_example.obj and look at the way that textures are mapped
   to the concrete base and to the sloped roof for an example of these
   techniques.

These compound types aren't supported directly by Blender. However, the
export script automatically tries to spot when it can use them and
reports in the Console when it succeeds.


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

Import
  "Custom Scenery\San Bernardino Example\custom objects\KSBD_example.obj"
from the standard X-Plane folder tree to see an example of how X-Plane
scenery is made.

See http://marginal.org.uk/x-planescenery/ for a tutorial on using
Blender to create X-Plane scenery.

See http://www.blender3d.org/Education/ for general Blender tutorials.

When creating boxes - eg a house or hangar body - you may find it easier
to create a Mesh "Cube" and delete any faces that are not required,
rather than create each face individually as Mesh "Plane"s.
In general, Meshes containing many faces are easier to edit than many
meshes that contain one face each. So if you're about to create a new
face that shares an edge with an existing mesh, add it to that existing
mesh rather than create it as a new standalone Mesh "Plane". To do this
select the existing mesh and go to "Edit Mode" before adding the plane.

X-Plane only displays one side of an object's face; faces are invisible
from behind. So don't make double-sided faces in Blender or you'll just
get confused. In order to see which side of a face is the visible side:
 - Go to Edit mode (you need to have an object selected to do this).
 - Hit F9 to see the "Editing" buttons.
 - Select "Draw Normals" and set "NSize" to at least 1.0 in the
   "Mesh Tools 1" panel. (I also like to select "Draw Faces" and
   "Draw Edges", but that's up to you).
When in edit mode, faces are now drawn with a short light blue line
coming from their centre. The visible side of the face is the side that
you are looking at when the line is pointing _towards_ you.

Mail me <x-plane@marginal.org.uk> with any questions, problems etc.
If reporting a problem, please try to send me the the .obj file (where
relevant) and the contents of the Console window. (In Mac OS X, this is
the "Console" program. In Windows this the window titled "Blender" that
looks like a Command Prompt).


Limitations
-----------
Import:
 - Smoke_Black and Smoke_White X-Plane objects are ignored.
 - Ambient, Difuse, Specular, Emission and Shiny attributes are ignored.
 - Level-of-detail is not supported. Any objects that are only visible
   from a non-zero distance are ignored.
Export:
 - Only Lamps and Mesh Faces (including 'lines') are exported.
 - All objects must share a single texture (this is a limitation of the
   X-Plane .obj file format). Multiple textures are not automagically
   merged into one file during the export.

