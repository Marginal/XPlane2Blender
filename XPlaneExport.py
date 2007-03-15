#------------------------------------------------------------------------
# X-Plane exporter helper classes for blender 2.34 or above
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
# 2005-09-23 v2.10
#  - Main export routines split out.
#
# 2005-11-11 v2.11
#  - Don't try to load texture if TEX isn't set.
# 
# 2005-11-18 v2.12
#  - Fix for relative texture paths.
#


import sys
import Blender
from Blender import NMesh, Lamp, Image, Draw, Window
from XPlaneUtils import Vertex

class ExportError(Exception):
    def __init__(self, msg):
        self.msg = msg


#------------------------------------------------------------------------
def checkFile (filename):
    try:
        file = open(filename, "rb")
    except IOError:
        return 1        
    file.close()
    if Draw.PupMenu("Overwrite?%%t|Overwrite file: %s" % filename)!=1:
        print "Cancelled\n"
        return 0
    return 1

#------------------------------------------------------------------------
def checkLayers (theObjects, iscockpit):
    if iscockpit:
        for object in theObjects:
            if not object.Layer&1:
                print "Warn:\tObjects were found outside layer 1 and were not exported."
                return
    else:
        for object in theObjects:
            if not object.Layer&7:
                print "Warn:\tObjects were found outside layers 1-3 and were not exported."
                return

#------------------------------------------------------------------------
def getTexture (theObjects, layermask, iscockpit, fileformat):
    texture=None
    havepanel=False
    multierr=False
    panelerr=False
    nobj=len(theObjects)
    texlist=[]
    layers=0

    for o in range (nobj-1,-1,-1):
        object=theObjects[o]

        if layermask==1 and not iscockpit:
            if layers==0:
                layers = object.Layer&7
            elif object.Layer&7 and layers^(object.Layer&7):
                layermask=7
                print "Info:\tMultiple Levels Of Detail found"
                
        if not object.Layer&layermask:
            continue
            
        objType=object.getType()
        if objType == "Mesh":
            mesh=object.getData()
            if mesh.hasFaceUV():
                for face in mesh.faces:
                    if (face.mode&NMesh.FaceModes.TEX) and face.image:
                        # Need to canonicalise pathnames to avoid false dupes
                        fixedfile=face.image.filename
                        if fixedfile[0:2] in ['//', '\\\\']:
                            # Path is relative to .blend file
                            fixedfile=Blender.Get('filename')
                            l=fixedfile.rfind(Blender.sys.dirsep)
                            if l!=-1:
                                fixedfile=(fixedfile[:l+1]+
                                           face.image.filename[2:])
                            else:
                                fixedfile=face.image.filename[2:]
                        if Blender.sys.dirsep=='\\':
                            # Windows
                            if fixedfile[0] in ['/', '\\']:
                                # Add drive letter
                                for drive in [Blender.Get('filename'),
                                              Blender.sys.progname]:
                                    if drive and not drive[0] in ['/', '\\']:
                                        f=drive.lower()[:2]+'\\'+fixedfile[1:]
                                        try:
                                            file=open(f, 'rb')
                                        except IOError:
                                            pass
                                        else:
                                            file.close()
                                            fixedfile=f
                                            break
                            else:
                                # Lowercase drive lettter
                                fixedfile=fixedfile[0].lower()+fixedfile[1:]
                        while fixedfile.find('..')!=-1:
                            # Remove relative stuff
                            r=fixedfile.rfind('..')
                            l=fixedfile[:r-1].rfind(Blender.sys.dirsep)
                            if l==-1:
                                break	# Ugh?
                            fixedfile=fixedfile[:l]+fixedfile[r+2:]
                        if 0:	#fixedfile!=face.image.filename:
                            try:
                                face.image=Image.Load(fixedfile)
                            except IOError:
                                pass
                            else:
                                mesh.update()

                        if face.image.name.lower().find("panel.")!=-1:
                            # Check that at least one panel texture is OK
                            if len(face.v)==3 and fileformat==7:
                                raise ExportError("Only quads can use the instrument panel texture,\n\tbut tri using panel texture found in mesh \"%s\"." % object.name)
                            if not havepanel:
                                havepanel=True
                                iscockpit=True
                                layermask=1
                                panelerr=(fileformat==7)
                            if panelerr:
                                try:
                                    height=face.image.getSize()[1]
                                except RuntimeError:
                                    raise ExportError("Can't load instrument panel texture file")
                                for uv in face.uv:
                                    if (uv[0]<0.0  or uv[0]>1.0 or
                                        (1-uv[1])*height>768 or uv[1]>1.0):
                                        break
                                else:
                                    panelerr=0
                        else:
                            # Check for multiple textures
                            if ((not texture) or
                                (str.lower(fixedfile)==str.lower(texture))):
                                texture = fixedfile
                                texlist.append(str.lower(fixedfile))
                            else:
                                if not multierr:
                                    multierr=1
                                    print "Warn:\tMultiple texture files found:"
                                    print texture
                                if not str.lower(fixedfile) in texlist:
                                    texlist.append(str.lower(fixedfile))
                                    print fixedfile
        elif (iscockpit and objType == "Lamp"
              and object.getData().getType() == Lamp.Types.Lamp):
            raise ExportError("Cockpit objects can't contain lights.")
                        
    if multierr:
        raise ExportError("OBJ format supports one texture file, but multiple files found.")
                                
    if panelerr:
        raise ExportError("At least one instrument panel texture must be within 1024x768.")

    if not texture:
        return (None, False, layermask)

    try:
        tex=Image.Load(texture)
        dim=tex.getSize()
    except (RuntimeError, IOError):
    	raise ExportError("Can't load texture file \"%s\"" % texture)
    else:
        for l in dim:
            while l:
                l=l/2
                if l&1 and l>1:
                    raise ExportError("Texture file height and width must be powers of two.\n\tPlease resize the file. Use Image->Replace to load the new file.")

    l=texture.rfind(Blender.sys.dirsep)
    if l!=-1:
        l=l+1
    else:
        l=0
    if texture[l:].find(' ')!=-1:
        raise ExportError("Texture filename \"%s\" contains spaces.\n\tPlease rename the file. Use Image->Replace to load the renamed file." % texture[l:])

    while 1:
        l=texture.find(Blender.sys.dirsep)
        if l==-1:
            break
        texture=texture[:l]+':'+texture[l+1:]

    if texture[-4:].lower() == '.bmp':
        if fileformat==7:
            texture = texture[:-4]
    elif texture[-4:].lower() == '.png':
        if fileformat==7:
            texture = texture[:-4]
    else:
        raise ExportError("Texture file must be in bmp or png format.\n\tPlease convert the file. Use Image->Replace to load the new file.")
    
    # try to guess correct texture path
    if iscockpit:
        print "Info:\tUsing algorithms appropriate for a cockpit object."
    elif fileformat==7:
        for prefix in ["custom object textures", "autogen textures"]:
            l=texture.lower().rfind(prefix)
            if l!=-1:
                texture = texture[l+len(prefix)+1:]
                return (texture, havepanel, layermask)
        print "Warn:\tCan't guess path for texture file. Please fix in the .obj file."

    # just return bare filename
    l=texture.rfind(":")
    if l!=-1:
        texture = texture[l+1:]
    return (texture, havepanel, layermask)

#------------------------------------------------------------------------
def isLine(object, linewidth):
    # A line is represented as a mesh with one 4-edged face, where vertices
    # at each end of the face are less than self.linewidth units apart

    nmesh=object.getData()
    if (len(nmesh.faces)!=1 or len(nmesh.faces[0].v)!=4 or
        nmesh.faces[0].mode&NMesh.FaceModes.TEX):
        return False
    
    mm=object.getMatrix()
    f=nmesh.faces[0]
    v=[]
    for i in range(4):
        v.append(Vertex(f.v[i][0],f.v[i][1],f.v[i][2], mm))
    for i in range(2):
        if (v[i].equals(v[i+1],linewidth) and
            v[i+2].equals(v[(i+3)%4],linewidth)):
            return True
    return False

