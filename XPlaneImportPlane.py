#!BPY
""" Registration info for Blender menus:
Name: ' X-Plane Plane as scenery (.acf)...'
Blender: 234
Group: 'Import'
Tooltip: 'Import an X-Plane airplane (.acf)'
"""
__author__ = "Jonathan Harris"
__url__ = ("Script homepage, http://marginal.org.uk/x-planescenery/")
__version__ = "2.04"
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
#------------------------------------------------------------------------
# X-Plane importer for blender 2.34 or above
#
# Copyright (c) 2004, 2005 Jonathan Harris
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
# 2004-02-01 v1.00
#  - First public version
#
# 2004-08-22 v1.10
#  - Requires XPlane2Blender 1.50 since DYNAMIC flag has been reversed
#  - Support for 7.40 format planes
#  - Improved texture placement (thanks to Austin for sharing his code).
#  - Fixed bug where VTOL vector was ignored on engines
#  - Misc Bodies 3-8 now imported, but using texture from Misc Bodies 1&2
#
# 2004-08-28 v1.11
#  - Fix for changed layer semantics in Blender 234 (fix to Blender bug #1212)
#  - Add single-letter suffix to mesh names to denote layer
#
# 2004-08-28 v1.12
#  - Requires Blender 234 due to changed layer semantics of Blender fix #1212
#
# 2004-08-28 v1.13
#
# 2004-12-31 v1.14
#  - Fixed bug with zero length bodies
#  - Truncate pre-730 planes at fuselage location 12 - improves smoothing.
#
# 2005-03-01 v1.15
#  - Fixed parsing bug with non-zero values of is_hm or is_ga.
#
# 2005-04-24 v2.00
#  - Added support for v8 planes and weapons.
#  - All bodies and weapons imported using correct texture.
#  - Airfoil width read from .afl file.
#
# 2005-05-10 v2.02
#  - Add '*' to mesh names for parts that use non-primary texture.
#

import sys
import Blender
from Blender import Object, NMesh, Lamp, Image, Material, Window, Mathutils
from Blender.Mathutils import Vector, Matrix, RotationMatrix, TranslationMatrix, MatMultVec
from struct import unpack
from math import hypot, pi, sin, cos
from XPlaneUtils import Vertex, UV, findTex

class ParseError(Exception):
    pass



#------------------------------------------------------------------------
#-- ACFimport --
#------------------------------------------------------------------------
class ACFimport:
    LAYER1=1
    LAYER2=2
    LAYER3=4
    LAYER1MKR=' H'
    LAYER2MKR=' M'
    LAYER3MKR=' L'
    IMAGE2MKR='*'	# Marker for parts with non-primary texture

    F2M=0.3048		# foot->metre constant

    # bodies smaller than this [m] skipped
    THRESH2=2.5
    THRESH3=7

    #------------------------------------------------------------------------
    def __init__(self, filename):
        self.debug=0	# extra debug info in console. >=2:dump txt file
        if Blender.sys.dirsep=='\\':
            # Lowercase Windows drive lettter
            self.filename=filename[0].lower()+filename[1:]
        else:
            self.filename=filename
        self.acf=DEFfile(self.filename, self.debug)
        self.scene = Blender.Scene.getCurrent();
        self.navloc = Vertex(0.0, 0.0, 0.0)
        self.tailloc = Vertex(0.0, 0.0, 0.0)
        self.wingc = {}
        self.image=0
        self.image2=0
        self.mm=Matrix([ self.F2M, 0.0, 0.0, 0.0],
                       [0.0, -self.F2M, 0.0, 0.0],
                       [0.0, 0.0, -self.F2M, 0.0],
                       [0.0,   0.0,   0.0,   1.0])
        cur=Window.GetCursorPos()
        self.cur=Vertex(cur[0], cur[1], cur[2])
        
        texfilename=self.filename[:self.filename.rindex('.')]+'_paint'
        for extension in [".bmp", ".png"]:
            try:
                file = open(texfilename+extension, "rb")
            except IOError:
                pass
            else:
                for extension2 in [".bmp", ".png"]:
                    try:
                        self.image2 = Image.Load(texfilename+'2'+extension2)
                    except IOError:
                        pass

                # Handle spaces in primary texture filename
                if 0:	#Blender.sys.basename(texfilename).find(" ") != -1:
                    basefilename=Blender.sys.basename(texfilename)
                    newfilename=""
                    for i in range(len(basefilename)):
                        if basefilename[i]==" ":
                            newfilename+="_"
                        else:
                            newfilename+=basefilename[i]
                    print "Info:\tCreated new texture file \"%s\"" % (
                        newfilename+extension)
                    newfilename=(Blender.sys.dirname(texfilename)+
                                 Blender.sys.dirsep+newfilename)
                    newfile=open(newfilename+extension, "wb")
                    newfile.write(file.read())
                    newfile.close()
                    texfilename=newfilename
                file.close()
                self.image = Image.Load(texfilename+extension)
                return
        print "Warn:\tNo texture file found"
        

    #------------------------------------------------------------------------
    def doImport(self):

        n=(DEFfile.partDIM+DEFfile.wattDIM+DEFfile.gearDIM+DEFfile.doorDIM+
           len(DEFfile.lites)+1)
        i=0

        for p in range(DEFfile.engnDIM):
            i=i+1
            Window.DrawProgressBar(0.5+i/(float(n*2)), "Importing props ...")
            self.doProp(p)

        # Need to do wings in two passes
        for (name, p) in DEFfile.wings:
            self.doWing1(name, p)

        for (name, p) in DEFfile.wings:
            i=i+1
            Window.DrawProgressBar(0.5+i/(float(n*2)), "Importing wings ...")
            self.doWing2(name, p)
                
        for (name, p) in DEFfile.parts:
            i=i+1
            Window.DrawProgressBar(0.5+i/(float(n*2)), "Importing bodies ...")
            self.doBody(name, p)

        for p in range(DEFfile.gearDIM):
            i=i+1
            Window.DrawProgressBar(0.5+i/(float(n*2)), "Importing gear ...")
            self.doGear(p)

        for p in range(0,-DEFfile.wattDIM,-1):
            i=i+1
            Window.DrawProgressBar(0.5+i/(float(n*2)), "Importing weapons ...")
            self.doBody(None, p)

        for p in range(DEFfile.doorDIM):
            i=i+1
            Window.DrawProgressBar(0.5+i/(float(n*2)), "Importing doors ...")
            self.doDoor(p)
                     
        for (name, part, r, g, b,) in DEFfile.lites:
            i=i+1
            Window.DrawProgressBar(0.5+i/(float(n*2)), "Importing lights ...")
            if eval("self.acf.VIEW_has_%s" % part):
                self.doLight(name, r, g, b,
                             Vertex(eval("self.acf.VIEW_%s_xyz" % part),
                                    self.mm))
        if self.acf.VIEW_has_navlites:
            # uses values computed during wings
            self.doLight("Nav Left",  1.0, 0.0, 0.0,
                         Vertex(-(self.navloc.x+0.1),
                                self.navloc.y, self.navloc.z))
            self.doLight("Nav Right", 0.0, 1.0, 0.0,
                         Vertex(self.navloc.x + 0.1,
                                self.navloc.y, self.navloc.z))
            self.doLight("Nav Pulse", 1.0, 0.0, 0.0,
                         Vertex(self.tailloc.x, self.tailloc.y,
                                self.tailloc.z+0.1))

                
    #------------------------------------------------------------------------
    def doProp(self, p):

        # Arbitrary constant
        twist=pi*(30.0/180.0)
        
        engn=self.acf.engn[p]
        part=self.acf.part[p]
        wing=self.acf.wing[p]
            
        if (p>=self.acf.ENGINE_num_thrustpoints or
            engn.engn_type not in [0,1,2,8] or
            not engn.num_blades or
            not wing.semilen_SEG):
            return
            
        # texture
        if part.part_tex==0:
            imagemkr=ACFimport.LAYER1MKR
            image=self.image
        else:
            imagemkr=ACFimport.LAYER1MKR+ACFimport.IMAGE2MKR
            image=self.image2

        mesh=NMesh.New("Prop %s%s" % ((p+1), imagemkr))
        mm=TranslationMatrix((Vertex(part.part_x,
                                     part.part_y+self.acf.VTOL_vectarmY,
                                     part.part_z+self.acf.VTOL_vectarmZ,
                                     self.mm)+self.cur).Vector(4))
        mm=RotationMatrix(engn.vert_init, 4, 'x')*mm
        mm=RotationMatrix(-engn.side_init, 4, 'z')*mm

        v=[Vertex(0,
                  sin(twist)*
                  wing.Croot*self.F2M/4,
                  -cos(twist)*engn.prop_dir*
                  wing.Croot*self.F2M/4),
           Vertex(0,
                  -sin(twist)*
                  wing.Croot*self.F2M*3/4,
                  cos(twist)*engn.prop_dir*
                  wing.Croot*self.F2M*3/4),
           Vertex(wing.semilen_SEG*self.F2M,
                  0,
                  engn.prop_dir*
                  wing.Ctip*self.F2M*3/4),
           Vertex(wing.semilen_SEG*self.F2M,
                  0,
                  -engn.prop_dir*
                  wing.Ctip*self.F2M/4)]
        
        ruv=[UV(part.top_s1,part.top_t1),
             UV(part.top_s2,part.top_t1),
             UV(part.top_s2,part.top_t2),
             UV(part.top_s1,part.top_t2)]
        luv=[UV(part.bot_s1,part.bot_t2),
             UV(part.bot_s2,part.bot_t2),
             UV(part.bot_s2,part.bot_t1),
             UV(part.bot_s1,part.bot_t1)]
        
        for i in range(int(engn.num_blades)):
            a=(1+i*2)*pi/engn.num_blades
            fv=[]
            for v1 in v:
                fv.append(Vertex(cos(a)*v1.x - sin(a)*v1.z,
                                 v1.y,
                                 sin(a)*v1.x + cos(a)*v1.z))
            self.addFace(mesh, fv, ruv, image)
            self.addFace(mesh,
                         [fv[3], fv[2], fv[1], fv[0]],
                         luv, image)

        self.addMesh(mesh, ACFimport.LAYER1, mm)

    #------------------------------------------------------------------------
    def doWing1(self, name, p):

        part=self.acf.part[p]
        wing=self.acf.wing[p]
        if not (part.part_eq and wing.semilen_SEG):
            return
        
        centre=Vertex(part.part_x, part.part_y, part.part_z, self.mm)+self.cur
        
        tip=centre+Vertex(
            MatMultVec(RotationMatrix(wing.lat_sign*wing.dihed1, 3, 'y'),
                       MatMultVec(RotationMatrix(wing.lat_sign*wing.sweep1, 3, 'z'),
                                  Vector([wing.lat_sign*wing.semilen_SEG*self.F2M,0,0]))))

        # Maybe nav light location
        if tip.x>self.navloc.x:
            self.navloc=tip
        if tip.z>self.tailloc.z:
            self.tailloc=tip

        self.wingc[p]=((centre, tip))
        if self.debug:
            print "%s \t[%s] [%s]" % (name, centre, tip)
        
    #------------------------------------------------------------------------
    def doWing2(self, name, p):

        part=self.acf.part[p]
        wing=self.acf.wing[p]
        if not (part.part_eq and wing.semilen_SEG):
            return
        
        # Arbitrary constants for symmetrical and lifting wings
        sym_width=0.09
        lift_width=0.10
        chord1=0.125
        chord2=0.450
        max_dihed=20.0		# Wings with d greater than this treated as Sym
        tip_fudge=0.2		# wings considered joined if closer

        if self.debug:
            print "%s \t" % name,

        # Is this a wing tip?
        istip=1
        (centre, tip) = self.wingc[p]
        for p2, (c2, t2) in self.wingc.iteritems():
            if (tip.equals(c2, tip_fudge) and
                abs(wing.dihed1-self.acf.wing[p2].dihed1) < max_dihed):
                istip=0
                break
        if self.debug and istip:
            print "Tip",

        # Find root of segment
        rootp=p		# part number of root
        c=centre	# centre of root
        while 1:
            for p2, (c2, t2) in self.wingc.iteritems():
                if (rootp!=p2 and c.equals(t2, tip_fudge) and
                    abs(self.acf.wing[rootp].dihed1-
                        self.acf.wing[p2].dihed1) < max_dihed):
                    rootp=p2
                    c=c2
                    break
            else:
                break
        if self.debug:
            if p==rootp:
                print "Root"
            else:
                print "Root=%s" % rootp

        # texture
        if part.part_tex==0:
            imagemkr=''
            image=self.image
        else:
            imagemkr=ACFimport.IMAGE2MKR
            image=self.image2

        mm=TranslationMatrix(centre.Vector(4))
        mm=RotationMatrix(-wing.lat_sign*wing.dihed1, 4, 'y')*mm
        
        # Don't want to rotate to find wing sweep. So find tip manually.
        tip=Vertex(MatMultVec(RotationMatrix(wing.lat_sign*wing.sweep1,
                                             3, 'z'),
                              Vector([wing.lat_sign*wing.semilen_SEG*self.F2M,
                                      0,0])))

        # Find four points - leading root & tip, trailing tip & root
        v=[Vertex(0.0,    wing.Croot*self.F2M/4,         0.0),
           Vertex(tip.x,  wing.Ctip *self.F2M/4  +tip.y, tip.z),
           Vertex(tip.x, -wing.Ctip *self.F2M*3/4+tip.y, tip.z),
           Vertex(0.0,   -wing.Croot*self.F2M*3/4,       0.0)]

        rv=v
        lv=[v[3], v[2], v[1], v[0]]
        
        if self.debug:
            for q in v:
                print "[%5.1f %5.1f %5.1f]" % (q.x, q.y, q.z),

        # Corresponding texture points
        miny=max(v[0].y,v[1].y)	# leading edge
        maxy=min(v[2].y,v[3].y)	# trailing edge
        
        if wing.is_left:
            rys=(part.top_s2-part.top_s1)/(miny-maxy)
            ruv=[UV(part.top_s1+(miny-v[0].y)*rys, part.top_t1),
                 UV(part.top_s1+(miny-v[1].y)*rys, part.top_t2),
                 UV(part.top_s1+(miny-v[2].y)*rys, part.top_t2),
                 UV(part.top_s1+(miny-v[3].y)*rys, part.top_t1)]
            lys=(part.bot_s2-part.bot_s1)/(miny-maxy)
            luv=[UV(part.bot_s1+(miny-v[3].y)*lys, part.bot_t1),
                 UV(part.bot_s1+(miny-v[2].y)*lys, part.bot_t2),
                 UV(part.bot_s1+(miny-v[1].y)*lys, part.bot_t2),
                 UV(part.bot_s1+(miny-v[0].y)*lys, part.bot_t1)]
        else:
            rys=(part.bot_s2-part.bot_s1)/(miny-maxy)
            ruv=[UV(part.bot_s1+(miny-v[0].y)*rys, part.bot_t1),
                 UV(part.bot_s1+(miny-v[1].y)*rys, part.bot_t2),
                 UV(part.bot_s1+(miny-v[2].y)*rys, part.bot_t2),
                 UV(part.bot_s1+(miny-v[3].y)*rys, part.bot_t1)]
            lys=(part.top_s2-part.top_s1)/(miny-maxy)
            luv=[UV(part.top_s1+(miny-v[3].y)*lys, part.top_t1),
                 UV(part.top_s1+(miny-v[2].y)*lys, part.top_t2),
                 UV(part.top_s1+(miny-v[1].y)*lys, part.top_t2),
                 UV(part.top_s1+(miny-v[0].y)*lys, part.top_t1)]

        # Type of wing to draw
        if (wing.semilen_SEG*self.F2M < ACFimport.THRESH2 and
            istip and p==rootp):
            # Small and not part of a segment - draw as thin
            iscrappy=1
        else:
            iscrappy=0
                        
            # Orientation
            if abs(wing.dihed1) >= max_dihed:
                orient=0	# Verticalish
                rwidth=sym_width/2
                twidth=sym_width/2
            else:
                if ((wing.dihed1+90)*wing.lat_sign < 0):
                    orient=-1	# Left side
                else:
                    orient=1	# Right side
                rwidth=lift_width/2
                twidth=lift_width/2

            w=self.afl(wing.Rafl0)
            if w:
                rwidth=w/2
                twidth=w/2
            w=self.afl(wing.Tafl0)
            if w:
                twidth=w/2

            rwidth=wing.lat_sign*rwidth
            twidth=wing.lat_sign*twidth

        # Layer 1
        mesh=NMesh.New(name+ACFimport.LAYER1MKR+imagemkr)

        if iscrappy:
            # Not worth toggling culling just for this, so repeat the face
            self.addFace(mesh, rv, ruv, image)
            self.addFace(mesh, lv, luv, image)
        else:
            self.addFacePart(mesh, rv, ruv, 0,        chord1,   rwidth, twidth,
                             image)
            self.addFacePart(mesh, rv, ruv, chord1,   chord2,   rwidth, twidth,
                             image)
            self.addFacePart(mesh, rv, ruv, chord2,   1,        rwidth, twidth,
                             image)
            self.addFacePart(mesh, lv, luv, 0,        1-chord2, rwidth, twidth,
                             image)
            self.addFacePart(mesh, lv, luv, 1-chord2, 1-chord1, rwidth, twidth,
                             image)
            self.addFacePart(mesh, lv, luv, 1-chord1, 1,        rwidth, twidth,
                             image)
            if istip:
                # Add end cap
                ctip=rv[2].y-rv[1].y
                ntip=ctip*twidth
                self.addFace(mesh,
                             [rv[1],
                              rv[1]+Vertex(0, ctip*chord1, -ntip),
                              rv[1]+Vertex(0, ctip*chord1,  ntip)],
                             [ruv[1],
                              UV(ruv[1].s+(ruv[2].s-ruv[1].s)*chord1,ruv[1].t),
                              UV(ruv[1].s+(ruv[2].s-ruv[1].s)*chord1,ruv[1].t)],
                             image)
                self.addFace(mesh,
                             [rv[1]+Vertex(0, ctip*chord1,  ntip),
                              rv[1]+Vertex(0, ctip*chord1, -ntip),
                              rv[1]+Vertex(0, ctip*chord2, -ntip),
                              rv[1]+Vertex(0, ctip*chord2,  ntip)],
                             [UV(ruv[1].s+(ruv[2].s-ruv[1].s)*chord1,ruv[1].t),
                              UV(ruv[1].s+(ruv[2].s-ruv[1].s)*chord1,ruv[1].t),
                              UV(ruv[1].s+(ruv[2].s-ruv[1].s)*chord2,ruv[1].t),
                              UV(ruv[1].s+(ruv[2].s-ruv[1].s)*chord2,ruv[1].t)],
                             image)
                self.addFace(mesh,
                             [rv[2],
                              rv[1]+Vertex(0, ctip*chord2,  ntip),
                              rv[1]+Vertex(0, ctip*chord2, -ntip)],
                             [ruv[2],
                              UV(ruv[1].s+(ruv[2].s-ruv[1].s)*chord2,ruv[1].t),
                              UV(ruv[1].s+(ruv[2].s-ruv[1].s)*chord2,ruv[1].t)],
                             image)

        self.addMesh(mesh, ACFimport.LAYER1, mm)

        # Layer 2
        if iscrappy:
            return
        
        mesh=NMesh.New(name+ACFimport.LAYER2MKR+imagemkr)
        if orient!=1:
            self.addFace(mesh, rv, ruv, image)
        if orient!=-1:
            self.addFace(mesh, lv, luv, image)
        self.addMesh(mesh, ACFimport.LAYER2, mm)


        # Layer 3
        if not istip:
            return

        if p==rootp:
            if wing.semilen_SEG*self.F2M < ACFimport.THRESH3:
                return
        else:
            (foo, tip) = self.wingc[p]
            (centre, foo) = self.wingc[rootp]
            tip=tip-centre	# tip relative to root

            if (tip.x*tip.x + tip.y*tip.y + tip.z*tip.z < 
                ACFimport.THRESH3 * ACFimport.THRESH3):
                return

            rv=[Vertex(0.0,    self.acf.wing[rootp].Croot*self.F2M/4,   0.0),
                Vertex(tip.x,  wing.Ctip *self.F2M/4  +tip.y,           tip.z),
                Vertex(tip.x, -wing.Ctip *self.F2M*3/4+tip.y,           tip.z),
                Vertex(0.0,   -self.acf.wing[rootp].Croot*self.F2M*3/4, 0.0)]
            lv=[rv[3], rv[2], rv[1], rv[0]]

            mm=TranslationMatrix(centre.Vector(4))	# no rotation


        mesh=NMesh.New(name+ACFimport.LAYER3MKR+imagemkr)
        if orient!=1:
            self.addFace(mesh, rv, ruv, image)
        if orient!=-1:
            self.addFace(mesh, lv, luv, image)
        self.addMesh(mesh, ACFimport.LAYER3, mm)

    
    #------------------------------------------------------------------------
    def doBody(self, name, p):
        
        is_wpn=(p<=0)

        if is_wpn:
            # Weapon locations are special
            watt=self.acf.watt[-p]
            wpnname=watt.watt_name
            wpn=self.wpn(wpnname)
            if not wpn:
                return
            part=wpn.part
            l=wpnname.lower().rfind('.wpn')
            if l!=-1:
                wpnname=wpnname[:l]
            image=findTex(self.filename, wpnname, ['Weapons'])
            imagemkr=ACFimport.IMAGE2MKR
            name="W%02d %s" % (1-p, wpnname)
            
            mm=TranslationMatrix((Vertex(watt.watt_x,
                                         watt.watt_y,
                                         watt.watt_z,
                                         self.mm)+self.cur).Vector(4))

            if watt.watt_con in range(14,24):
                # Rotation modified by gear angle
                gear=self.acf.gear[watt.watt_con-14]
                mm=RotationMatrix(-watt.watt_psi, 4, 'z')*mm
                mm=RotationMatrix(watt.watt_phi-gear.latE, 4, 'y')*mm
                mm=RotationMatrix(watt.watt_the+gear.lonE-90, 4, 'x')*mm
            else:
                mm=RotationMatrix(-watt.watt_psi, 4, 'z')*mm
                mm=RotationMatrix(watt.watt_phi, 4, 'y')*mm
                mm=RotationMatrix(watt.watt_the, 4, 'x')*mm

            mm=TranslationMatrix(Vertex(-part.part_x,
                                        -part.part_y,
                                        -part.part_z,
                                        self.mm).Vector(4))*mm
        else:
            # Normal bodies
            part=self.acf.part[p]
            if not part.part_eq:
                return
            if part.part_tex==0:
                imagemkr=''
                image=self.image
            else:
                imagemkr=ACFimport.IMAGE2MKR
                image=self.image2
            
            if p in range(DEFfile.partFair1, DEFfile.partFair10+1):
                # Fairings take location from wheels
                gear=self.acf.gear[p-DEFfile.partFair1]
                a=RotationMatrix(gear.latE, 3, 'y')
                a=RotationMatrix(-gear.lonE, 3, 'x')*a
                mm=TranslationMatrix((Vertex(gear.gear_x,
                                             gear.gear_y,
                                             gear.gear_z,
                                             self.mm)+
                                      Vertex(MatMultVec(a,Vector([0,0,-gear.leg_len*self.F2M])))+
                                      self.cur).Vector(4))
            else:
                mm=TranslationMatrix((Vertex(part.part_x,
                                             part.part_y,
                                             part.part_z,
                                             self.mm)+self.cur).Vector(4))

            if part.patt_con in range(14,24):
                # Rotation modified by gear angle
                gear=self.acf.gear[part.patt_con-14]
                mm=RotationMatrix(-part.part_psi, 4, 'z')*mm
                mm=RotationMatrix(part.part_phi-gear.latE, 4, 'y')*mm
                mm=RotationMatrix(part.part_the+gear.lonE-90, 4, 'x')*mm
            else:
                mm=RotationMatrix(-part.part_psi, 4, 'z')*mm
                mm=RotationMatrix(part.part_phi, 4, 'y')*mm
                mm=RotationMatrix(part.part_the, 4, 'x')*mm

            if p in range(DEFfile.partNace1, DEFfile.partNace8+1):
                # Nacelles also affected by engine cant
                engn=self.acf.engn[p-DEFfile.partNace1]
                mm=RotationMatrix(engn.vert_init, 4, 'x')*mm
                mm=RotationMatrix(-engn.side_init, 4, 'z')*mm
        
        if self.debug: print name

        # Get vertex data in 2D array
        v=[]

        # locate the data in the array and skip duplicates
        rdim=int(part.r_dim/2)*2-2	# Must be even
        seq=range(rdim/2)
        seq.extend(range((rdim+2)/2,rdim+1))
            
        for i in range(part.s_dim):
            if (i==12 and
                Vertex(part.geo_xyz[i][0]).equals(Vertex(0.0, 0.0, 0.0))):
                # Special case: Plane-Maker<7.30 leaves these parts as 0
                if self.debug: print "Stopping at 12"
                break
                
            # Special case: Plane-Maker>=7.30 replicates part 11 offset 0.001'
            if i>11:
                for j in seq:
                    if not Vertex(part.geo_xyz[i][j]).equals(
                        Vertex(part.geo_xyz[i-1][j]), 0.001):
                        break
                else:
                    if self.debug: print "Stopping at %s" % i
                    break

            if self.debug: print i
            w=[]
            for j in seq:
                q=Vertex(part.geo_xyz[i][j], self.mm)
                w.append(q)
                if self.debug: print "[%5.1f %5.1f %5.1f]" % (q.x, q.y, q.z),
            if self.debug: print
            
            v.append(w)

        
        sdim=len(v)	# We now have up to 20 segments (maybe 12 or 8 or less)
        rdim=len(v[0])	# with 16 or fewer (but even) vertices/segment


        # Seriously fucked up algorithm for determining textures for
        # half (rdim/2+1) the body from load_plane_geo(), hl_drplane.cpp.
        rsem=rdim/2+1

        y_ctr=0.0
        for r in range(rdim):
            # Hack: Only use the first 12 stations for the fuse centreline
            # to keep the same centreline loc before and after 730, where
            # the number of fuselage stations changed from 12 to 20.
            for s in range (min(sdim,12)):
                y_ctr+=v[s][r].z/(rdim*sdim)

        uv=[]
        for s in range(sdim):
            uv.append([])
            for R in range(rsem):
                # R is the point we are finding the s/t coordinate for
                uv[s].append(UV(0,0))
                point_above_ctr=(v[s][R].z>y_ctr)
                point_below_ctr=not point_above_ctr

                if point_above_ctr:
                    r1=R
                    r2=rsem
                else:
                    r1=0
                    r2=R

                for r in range(r1,r2):	# remember we go to r+1!
                    # r is simply a counter to build up the coordinate for R
                    tlen=hypot(v[s][r+1].x-v[s][r].x, v[s][r+1].z-v[s][r].z)
                    if (point_above_ctr and v[s][r].z>y_ctr and
                        v[s][r+1].z>y_ctr):
                        uv[s][R].t+=tlen
                    if (point_below_ctr and v[s][r].z<y_ctr and
                        v[s][r+1].z<y_ctr):
                        uv[s][R].t-=tlen
                    if (point_above_ctr and v[s][r].z!=v[s][r+1].z and
                        v[s][r].z>=y_ctr and v[s][r+1].z<=y_ctr):
                        uv[s][R].t+=tlen*(v[s][r  ].z-y_ctr)/(v[s][r].z-v[s][r+1].z)
                    if (point_below_ctr and v[s][r].z!=v[s][r+1].z and
                        v[s][r].z>=y_ctr and v[s][r+1].z<=y_ctr):
                        uv[s][R].t-=tlen*(y_ctr-v[s][r+1].z)/(v[s][r].z-v[s][r+1].z)

                if v[s][rsem].z>=y_ctr:
                    uv[s][R].t+=(v[s][rsem].z-y_ctr)
                if v[s][0   ].z<=y_ctr:
                    uv[s][R].t+=(v[s][0   ].z-y_ctr)

        lo_y= 999.0
        lo_z= 999.0
        hi_y=-999.0
        hi_z=-999.0

        # find extreme points for scale
        for s in range(sdim):
            for r in range(rsem):
                if uv[s][r].t>hi_y:
                    hi_y=uv[s][r].t			
                if uv[s][r].t<lo_y:
                    lo_y=uv[s][r].t			
                if v[s][r].y>hi_z:
                    hi_z=v[s][r].y
                if v[s][r].y<lo_z:
                    lo_z=v[s][r].y
                
        # scale all data 0-1
        for s in range(sdim):
            for r in range(rsem):
                uv[s][r].t=(uv[s][r].t-lo_y)/(hi_y-lo_y)

        if (is_wpn or
            ((p in range(DEFfile.partNace1, DEFfile.partNace8+1)) and
             (self.acf.engn[p-DEFfile.partNace1].engn_type in [4,5]))):
            # do LINE-LENGTH for the nacelles and weapons
            line_length_now =0.0
            line_length_tot =0.0
            for s in range(sdim-1):
                line_length_tot+=hypot(v[s+1][0].z-v[s][0].z,
                                       v[s+1][0].y-v[s][0].y)
            for s in range(sdim):
                for r in range(rsem):
                    uv[s][r].s=line_length_now/line_length_tot
                if s<sdim-1:
                    line_length_now+=hypot(v[s+1][0].z-v[s][0].z,
                                           v[s+1][0].y-v[s][0].y)
        else:
            # do long-location
            for s in range(sdim):
                for r in range(rsem):
                    uv[s][r].s=(hi_z-v[s][r].y)/(hi_z-lo_z)

        # Scale
        r=UV(part.top_s1,part.top_t1)
        l=UV(part.bot_s1,part.bot_t1)
        rs=UV(part.top_s2-part.top_s1,part.top_t2-part.top_t1)
        ls=UV(part.bot_s2-part.bot_s1,part.bot_t2-part.bot_t1)
        ruv=[]
        luv=[]
        for i in range(sdim):
            ruv.append([])
            luv.append([])
            for j in range(rsem):
                ruv[i].append(r+rs*uv[i][j])
                luv[i].append(l+ls*uv[i][j])


        # Dodgy LOD heuristics

        # offsets less than this (or neg) make body blunt
        blunt_front=0.1
        
        isblunt=0
        point1=0
        length=v[0][0].y-v[sdim-1][0].y

        for i in range(sdim/2,0,-1):
            if v[i][0].y>=v[i-1][0].y-blunt_front:
                isblunt=1
                point1=i
                break

        if isblunt:
            if self.debug: print "Blunt front %s," % point1,
            body_pt2=0.33
            body_pt3=0.50
        else:
            if self.debug: print "Sharp front,",
            body_pt2=0.30
            body_pt3=0.67
            
        # Find front of cabin
        point2=point1+1
        for i in range(point1,sdim-1):
            if v[i][0].y<=v[0][0].y-length*body_pt2:
                point2=i
                break
        point2=point2-1

        # Find ends of main body
        point3=point2+1
        for i in range(point3,sdim-1):
            if v[i][0].y<=v[0][0].y-length*body_pt3:
                point3=i
                break
        for i in range(point3,sdim-1):
            if v[i][0].y<v[i+1][0].y:
                point3=i
                if self.debug: print "Blunt end %s" % point3
                break
        else:
            if self.debug: print "Sharp end %s" % point3

        # Finally...
        for layer in [ACFimport.LAYER1, ACFimport.LAYER2, ACFimport.LAYER3]:

            # More dodgy LOD heuristics
            if layer==ACFimport.LAYER1:
                # Max detail
                jstep=1
                seq=range(sdim)
                mkr=ACFimport.LAYER1MKR+imagemkr

            elif layer==ACFimport.LAYER2:
                # Don't do small bodies
                if length<ACFimport.THRESH2:
                    break
                elif (p==DEFfile.partFuse or
                      length>ACFimport.THRESH3 or
                      rdim<=8):
                    jstep=2		# octagon
                else:
                    # Make other bodies simple
                    jstep=rdim/4	# squareoid

                if isblunt:
                    seq=[0,point1,point2,point3,sdim-1]
                else:
                    seq=[0,point2,point3,sdim-1]
                mkr=ACFimport.LAYER2MKR+imagemkr
                
            else:     # ACFimport.LAYER3
                # Don't do small bodies
                if length<ACFimport.THRESH3:
                    break
                elif rdim<=8:
                    jstep=2		# octagon
                else:
                    jstep=rdim/4	# squareoid
                if isblunt:
                    seq=[0,point1,point2,point3,sdim-1]
                else:
                    seq=[0,point2,point3,sdim-1]
                mkr=ACFimport.LAYER3MKR+imagemkr

            mesh=NMesh.New(name+mkr)

            # Hack: do body from middle out to help export strip algorithm
            ir=range(len(seq)/2-1,len(seq)-1)
            ir.extend(range(len(seq)/2-2,-1,-1))
            jr=range(int(rdim/4),int(rdim/2)+1-jstep,jstep)
            jr.extend(range(0,int(rdim/4)+1-jstep,jstep))
            jr.extend(range(int(rdim*3/4),rdim+1-jstep,jstep))
            jr.extend(range(int(rdim/2),int(rdim*3/4)+1-jstep,jstep))
            if self.debug: print rdim, jstep, jr

            for i in ir:		# was range(len(seq)-1):
                for j in jr:	# was range(0,n,jstep):
                    fv=[v[seq[i]][j], v[seq[i+1]][j],
                        v[seq[i+1]][(j+jstep)%rdim], v[seq[i]][(j+jstep)%rdim]]
                    if j<rdim/2:
                        fuv=[ruv[seq[i]][j],
                             ruv[seq[i+1]][j],
                             ruv[seq[i+1]][j+jstep],
                             ruv[seq[i]][j+jstep]]
                    else:
                        fuv=[luv[seq[i]][rdim-j],
                             luv[seq[i+1]][rdim-j],
                             luv[seq[i+1]][rdim-jstep-j],
                             luv[seq[i]][rdim-jstep-j]]

                    self.addFace(mesh, fv, fuv, image)
        
            self.addMesh(mesh, layer, mm)


    #------------------------------------------------------------------------
    def doGear(self, p):

        gear=self.acf.gear[p]
        if not gear.gear_type:
            return
        elif gear.gear_type==DEFfile.GR_skid:
            strutratio=1	# skid
        else:
            strutratio=0.2

        name="Gear %s" % (p+1)
        if self.debug: print name
        
        mm=TranslationMatrix((Vertex(gear.gear_x, gear.gear_y, gear.gear_z,
                                     self.mm)+self.cur).Vector(4))
        mm=RotationMatrix(-gear.latE, 4, 'y')*mm
        mm=RotationMatrix(gear.lonE, 4, 'x')*mm

        
        # Strut
        mesh=NMesh.New("%s strut%s" % (name, ACFimport.LAYER1MKR))
        strutradius=strutratio*gear.tire_radius*self.F2M
        strutlen=gear.leg_len*self.F2M

        (sps, spt, sptw, spth) = (1, 893, 14, 128)	# Hard-coded
        s0=sps/1024.0
        t0=(1023-spt)/1024.0
        sw=sptw/1024.0
        t1=t0+spth/1024.0
        
        for i in range(0,8,2):
            a=RotationMatrix(i*45, 3, 'z')
            b=RotationMatrix((i+1)*45, 3, 'z')
            c=RotationMatrix((i+2)*45, 3, 'z')
            v=[]
            v.append(Vertex(MatMultVec(a,Vector([strutradius,0.0,0.0]))))
            v.append(Vertex(MatMultVec(b,Vector([strutradius,0.0,0.0]))))
            v.append(Vertex(MatMultVec(b,Vector([strutradius,0.0,-strutlen]))))
            v.append(Vertex(MatMultVec(a,Vector([strutradius,0.0,-strutlen]))))
            self.addFace(mesh, v,
                         [UV(s0+ i   *sw/8.0,t0), UV(s0+(i+1)*sw/8.0, t0),
                          UV(s0+(i+1)*sw/8.0,t1), UV(s0+ i   *sw/8.0, t1)],
                         self.image)
            v=[]
            v.append(Vertex(MatMultVec(b,Vector([strutradius,0.0,0.0]))))
            v.append(Vertex(MatMultVec(c,Vector([strutradius,0.0,0.0]))))
            v.append(Vertex(MatMultVec(c,Vector([strutradius,0.0,-strutlen]))))
            v.append(Vertex(MatMultVec(b,Vector([strutradius,0.0,-strutlen]))))
            self.addFace(mesh, v,
                         [UV(s0+(i+1)*sw/8.0,t0), UV(s0+(i+2)*sw/8.0, t0),
                          UV(s0+(i+2)*sw/8.0,t1), UV(s0+(i+1)*sw/8.0, t1)],
                         self.image)
            
        self.addMesh(mesh, ACFimport.LAYER1, mm)


        # Tires
        if not gear.tire_swidth:
            return

        # Tire layout - layer 1
        
        w=gear.tire_swidth*self.F2M
        r=gear.tire_radius*self.F2M
        xsep=1.5*w
        ysep=1.2*r

        if gear.gear_type==DEFfile.GR_single:
            # single
            seq=[Vertex(0,0,0)]
        elif gear.gear_type==DEFfile.GR_2lat:
            # 2 lateral
            seq=[Vertex(-xsep, 0, 0),
                 Vertex( xsep, 0, 0)]
        elif gear.gear_type==DEFfile.GR_2long:
            # 2 long
            seq=[Vertex(0, -ysep, 0),
                 Vertex(0,  ysep, 0)]
        elif gear.gear_type==DEFfile.GR_4truck:
            # 4 truck
            seq=[Vertex(-xsep, -ysep, 0),
                 Vertex(-xsep,  ysep, 0),
                 Vertex(+xsep, -ysep, 0),
                 Vertex(+xsep,  ysep, 0)]
        elif gear.gear_type==DEFfile.GR_6truck:
            # 6 truck
            seq=[Vertex(-xsep, -2*r, 0),
                 Vertex(-xsep,  2*r, 0),
                 Vertex(-xsep,  0,   0),
                 Vertex(+xsep,  0,   0),
                 Vertex(+xsep, -2*r, 0),
                 Vertex(+xsep,  2*r, 0)]
        elif gear.gear_type==DEFfile.GR_4lat:
            # 4 lateral
            seq=[Vertex(-xsep*3, 0, 0),
                 Vertex(-xsep,   0, 0),
                 Vertex(+xsep,   0, 0),
                 Vertex(+xsep*3, 0, 0)]
        elif gear.gear_type==DEFfile.GR_2f4a:
            # 2/4 truck
            seq=[Vertex(-xsep,   -ysep, 0),
                 Vertex(-xsep,    ysep, 0),
                 Vertex(+xsep,   -ysep, 0),
                 Vertex(+xsep,    ysep, 0),
                 Vertex(-xsep*3, -ysep, 0),
                 Vertex(+xsep*3, -ysep, 0)]
        elif gear.gear_type==DEFfile.GR_3lat:
            # 3 lateral
            seq=[Vertex(-xsep*2, 0, 0),
                 Vertex(0,       0, 0),
                 Vertex(+xsep+2, 0, 0)]
        else:
            # Dunno
            return

        # Don't want to rotate the tire itself. So find centre manually.
        a=RotationMatrix(gear.latE, 3, 'y')
        a=RotationMatrix(-gear.lonE, 3, 'x')*a
        mm=TranslationMatrix((Vertex(gear.gear_x, gear.gear_y, gear.gear_z,
                                     self.mm)+
                              Vertex(MatMultVec(a,Vector([0,0,-strutlen])))+
                              self.cur).Vector(4))
        mesh=NMesh.New(name+ACFimport.LAYER1MKR)

        if self.acf.HEADER_version<800:	# v7
            wheel=[UV(self.acf.GEAR_wheel_tire_s1[0],
                      self.acf.GEAR_wheel_tire_t1[0]),
                   UV(self.acf.GEAR_wheel_tire_s2[0],
                      self.acf.GEAR_wheel_tire_t1[0]),
                   UV(self.acf.GEAR_wheel_tire_s2[0],
                      self.acf.GEAR_wheel_tire_t2[0]),
                   UV(self.acf.GEAR_wheel_tire_s1[0],
                      self.acf.GEAR_wheel_tire_t2[0])]
            tread=[UV(self.acf.GEAR_wheel_tire_s1[1],
                      self.acf.GEAR_wheel_tire_t1[1]),
                   UV(self.acf.GEAR_wheel_tire_s2[1],
                      self.acf.GEAR_wheel_tire_t1[1]),
                   UV(self.acf.GEAR_wheel_tire_s2[1],
                      self.acf.GEAR_wheel_tire_t2[1]),
                   UV(self.acf.GEAR_wheel_tire_s1[1],
                      self.acf.GEAR_wheel_tire_t2[1])]

            for o in seq:
                for i in range(0,12,2):
                    # Add in pairs in order to mirror textures
                    a=RotationMatrix( i   *30 - 180, 3, 'x')
                    b=RotationMatrix((i+1)*30 - 180, 3, 'x')
                    c=RotationMatrix((i+2)*30 - 180, 3, 'x')

                    # 1st step
                    v=[]
                    v.append(o+Vertex(w,0.0,0.0))	# centre
                    v.append(o+Vertex(MatMultVec(b,Vector([w,0.0,r]))))
                    v.append(o+Vertex(MatMultVec(a,Vector([w,0.0,r]))))
                    self.addFace(mesh, v,
                                 [wheel[0], wheel[2], wheel[3]],
                                 self.image)
                    v=[]
                    v.append(o+Vertex(-w,0.0,0.0))	# centre
                    v.append(o+Vertex(MatMultVec(a,Vector([-w,0.0,r]))))
                    v.append(o+Vertex(MatMultVec(b,Vector([-w,0.0,r]))))
                    self.addFace(mesh, v,
                                 [wheel[0], wheel[2], wheel[3]],
                                 self.image)
                    v=[]
                    v.append(o+Vertex(MatMultVec(a,Vector([w,0.0,r]))))
                    v.append(o+Vertex(MatMultVec(b,Vector([w,0.0,r]))))
                    v.append(o+Vertex(MatMultVec(b,Vector([-w,0.0,r]))))
                    v.append(o+Vertex(MatMultVec(a,Vector([-w,0.0,r]))))
                    self.addFace(mesh, v, tread, self.image)
                    
                    # 2nd step
                    v=[]
                    v.append(o+Vertex(w,0.0,0.0))	# centre
                    v.append(o+Vertex(MatMultVec(c,Vector([w,0.0,r]))))
                    v.append(o+Vertex(MatMultVec(b,Vector([w,0.0,r]))))
                    self.addFace(mesh, v,
                                 [wheel[0], wheel[3], wheel[2]],
                                 self.image)
                    v=[]
                    v.append(o+Vertex(-w,0.0,0.0))	# centre
                    v.append(o+Vertex(MatMultVec(b,Vector([-w,0.0,r]))))
                    v.append(o+Vertex(MatMultVec(c,Vector([-w,0.0,r]))))
                    self.addFace(mesh, v,
                                 [wheel[0], wheel[3], wheel[2]],
                                 self.image)
                    v=[]
                    v.append(o+Vertex(MatMultVec(b,Vector([w,0.0,r]))))
                    v.append(o+Vertex(MatMultVec(c,Vector([w,0.0,r]))))
                    v.append(o+Vertex(MatMultVec(c,Vector([-w,0.0,r]))))
                    v.append(o+Vertex(MatMultVec(b,Vector([-w,0.0,r]))))
                    self.addFace(mesh, v,
                                 [tread[1], tread[0], tread[3], tread[2]],
                                 self.image)

        else:	# v8
            hr=0.6*r	# radius of hub part (hub width is w)
            tw=0.7*w	# width of tire (tread radius is r)
            
            hubc=UV((self.acf.GEAR_wheel_tire_s1[0]+
                     self.acf.GEAR_wheel_tire_s2[0])/2,
                    (self.acf.GEAR_wheel_tire_t1[0]+
                     self.acf.GEAR_wheel_tire_t2[0])/2)
            hubw=UV((self.acf.GEAR_wheel_tire_s2[0]-
                     self.acf.GEAR_wheel_tire_s1[0])/2,
                    (self.acf.GEAR_wheel_tire_t2[0]-
                     self.acf.GEAR_wheel_tire_t1[0])/2)
            treadw=(self.acf.GEAR_wheel_tire_s2[1]-
                    self.acf.GEAR_wheel_tire_s1[1])/12.0
            tread=[UV(self.acf.GEAR_wheel_tire_s1[1],
                      self.acf.GEAR_wheel_tire_t1[1]+
                      (self.acf.GEAR_wheel_tire_t2[1]-
                       self.acf.GEAR_wheel_tire_t1[1])*0.9),
                   UV(self.acf.GEAR_wheel_tire_s1[1]+treadw,
                      self.acf.GEAR_wheel_tire_t1[1]+
                      (self.acf.GEAR_wheel_tire_t2[1]-
                       self.acf.GEAR_wheel_tire_t1[1])*0.9),
                   UV(self.acf.GEAR_wheel_tire_s1[1]+treadw,
                      self.acf.GEAR_wheel_tire_t1[1]+
                      (self.acf.GEAR_wheel_tire_t2[1]-
                       self.acf.GEAR_wheel_tire_t1[1])*0.1),
                   UV(self.acf.GEAR_wheel_tire_s1[1],
                      self.acf.GEAR_wheel_tire_t1[1]+
                      (self.acf.GEAR_wheel_tire_t2[1]-
                       self.acf.GEAR_wheel_tire_t1[1])*0.1)]
            rim1=[UV(self.acf.GEAR_wheel_tire_s1[1],
                     self.acf.GEAR_wheel_tire_t1[1]+
                     (self.acf.GEAR_wheel_tire_t2[1]-
                      self.acf.GEAR_wheel_tire_t1[1])*0.9),
                  UV(self.acf.GEAR_wheel_tire_s1[1]+treadw,
                     self.acf.GEAR_wheel_tire_t1[1]+
                     (self.acf.GEAR_wheel_tire_t2[1]-
                      self.acf.GEAR_wheel_tire_t1[1])*0.9),
                  UV(self.acf.GEAR_wheel_tire_s1[1]+treadw,
                     self.acf.GEAR_wheel_tire_t2[1]),
                  UV(self.acf.GEAR_wheel_tire_s1[1],
                     self.acf.GEAR_wheel_tire_t2[1])]
            rim2=[UV(self.acf.GEAR_wheel_tire_s1[1],
                     self.acf.GEAR_wheel_tire_t1[1]),
                  UV(self.acf.GEAR_wheel_tire_s1[1]+treadw,
                     self.acf.GEAR_wheel_tire_t1[1]),
                  UV(self.acf.GEAR_wheel_tire_s1[1]+treadw,
                     self.acf.GEAR_wheel_tire_t1[1]+
                     (self.acf.GEAR_wheel_tire_t2[1]-
                      self.acf.GEAR_wheel_tire_t1[1])*0.1),
                  UV(self.acf.GEAR_wheel_tire_s1[1],
                     self.acf.GEAR_wheel_tire_t1[1]+
                     (self.acf.GEAR_wheel_tire_t2[1]-
                      self.acf.GEAR_wheel_tire_t1[1])*0.1)]
            
            for o in seq:
                for i in range(12):
                    a=RotationMatrix( i   *30 - 180, 3, 'x')
                    b=RotationMatrix((i+1)*30 - 180, 3, 'x')
                    ua=UV(sin( i   *pi/6), -cos( i   *pi/6))
                    ub=UV(sin((i+1)*pi/6), -cos((i+1)*pi/6))
                    treadi=UV(treadw*((i+6)%12),0)

                    # Hack: do tread first to help export strip algorithm
                    v=[]
                    v.append(o+Vertex(MatMultVec(a,Vector([tw,0.0,r]))))
                    v.append(o+Vertex(MatMultVec(b,Vector([tw,0.0,r]))))
                    v.append(o+Vertex(MatMultVec(b,Vector([-tw,0.0,r]))))
                    v.append(o+Vertex(MatMultVec(a,Vector([-tw,0.0,r]))))
                    self.addFace(mesh, v,
                                 [tread[0]+treadi, tread[1]+treadi,
                                  tread[2]+treadi, tread[3]+treadi],
                                 self.image)

                    v=[]
                    v.append(o+Vertex(w,0.0,0.0))	# centre
                    v.append(o+Vertex(MatMultVec(b,Vector([w,0.0,hr]))))
                    v.append(o+Vertex(MatMultVec(a,Vector([w,0.0,hr]))))
                    uv=[hubc]
                    uv.append(hubc+ub*hubw)
                    uv.append(hubc+ua*hubw)
                    self.addFace(mesh, v, uv, self.image)

                    v=[]
                    v.append(o+Vertex(MatMultVec(a,Vector([w,0.0,hr]))))
                    v.append(o+Vertex(MatMultVec(b,Vector([w,0.0,hr]))))
                    v.append(o+Vertex(MatMultVec(b,Vector([tw,0.0,r]))))
                    v.append(o+Vertex(MatMultVec(a,Vector([tw,0.0,r]))))
                    self.addFace(mesh, v,
                                 [rim1[0]+treadi, rim1[1]+treadi,
                                  rim1[2]+treadi, rim1[3]+treadi],
                                 self.image)

                    v=[]
                    v.append(o+Vertex(-w,0.0,0.0))	# centre
                    v.append(o+Vertex(MatMultVec(a,Vector([-w,0.0,hr]))))
                    v.append(o+Vertex(MatMultVec(b,Vector([-w,0.0,hr]))))
                    uv=[hubc]
                    uv.append(hubc+ua*hubw)
                    uv.append(hubc+ub*hubw)
                    self.addFace(mesh, v, uv, self.image)

                    v=[]
                    v.append(o+Vertex(MatMultVec(a,Vector([-tw,0.0,r]))))
                    v.append(o+Vertex(MatMultVec(b,Vector([-tw,0.0,r]))))
                    v.append(o+Vertex(MatMultVec(b,Vector([-w,0.0,hr]))))
                    v.append(o+Vertex(MatMultVec(a,Vector([-w,0.0,hr]))))
                    self.addFace(mesh, v,
                                 [rim2[0]+treadi, rim2[1]+treadi,
                                  rim2[2]+treadi, rim2[3]+treadi],
                                 self.image)
            
        self.addMesh(mesh, ACFimport.LAYER1, mm)


    #------------------------------------------------------------------------
    def doDoor(self, p):

        door=self.acf.door[p]
        if not door.type in [DEFfile.gear_door_standard,
                             DEFfile.gear_door_attached]:
            return

        name="Door %s" % (p+1)
        
        mm=TranslationMatrix((Vertex(door.xyz,self.mm)+self.cur).Vector(4))
        mm=RotationMatrix(-door.axi_rot, 4, 'z')*mm
        if self.acf.HEADER_version<800:	# v7
            mm=RotationMatrix(-door.ext_ang, 4, 'y')*mm
        else:
            mm=RotationMatrix(door.ext_ang, 4, 'x')*mm
            
        # just use 4 corners
        v=[]
        for j in [door.geo[0][0],door.geo[0][3],door.geo[3][3],door.geo[3][0]]:
            v.append(Vertex(j, self.mm))

        mesh=NMesh.New(name+ACFimport.LAYER1MKR)
        self.addFace(mesh, v,
                     [UV(door.inn_s1,door.inn_t2),
                      UV(door.inn_s1,door.inn_t1),
                      UV(door.inn_s2,door.inn_t1),
                      UV(door.inn_s2,door.inn_t2)], self.image)
        v.reverse()
        self.addFace(mesh, v,
                     [UV(door.out_s2,door.out_t2),
                      UV(door.out_s2,door.out_t1),
                      UV(door.out_s1,door.out_t1),
                      UV(door.out_s1,door.out_t2)], self.image)
        self.addMesh(mesh, ACFimport.LAYER1, mm)


    #------------------------------------------------------------------------
    def doLight(self, name, r, g, b, centre):
        lamp=Lamp.New("Lamp", name)
        lamp.col=[r,g,b]
        lamp.mode |= Lamp.Modes.Sphere	# stop lamp colouring whole object
        lamp.dist = 4.0
        ob = Object.New("Lamp", name)
        ob.link(lamp)
        self.scene.link(ob)
        ob.Layer=ACFimport.LAYER1|ACFimport.LAYER2
        cur=Window.GetCursorPos()
        ob.setLocation(centre.x+cur[0], centre.y+cur[1], centre.z+cur[2])


    #------------------------------------------------------------------------
    def addMesh(self, mesh, layer, mm):
        mesh.mode &= ~(NMesh.Modes.TWOSIDED|NMesh.Modes.AUTOSMOOTH)
        mesh.mode |= NMesh.Modes.NOVNORMALSFLIP
        ob = Object.New("Mesh", mesh.name)
        ob.link(mesh)
        self.scene.link(ob)
        ob.Layer=layer
        #ob.setLocation(centre.x+cur[0], centre.y+cur[1], centre.z+cur[2])
        ob.setMatrix(mm)
        mesh.update(1)


    #------------------------------------------------------------------------
    def addFace(self, mesh, fv, fuv, image, dbl=0):

        # Remove any duplicate vertices
        v=[]
        uv=[]
        for i in range(len(fv)):
            for j in v:
                if j.equals(fv[i]):
                    break
            else:
                v.append(fv[i])
                uv.append(fuv[i])
        if len(v)<3:
            return
    
        face=NMesh.Face()
        face.mode &= ~(NMesh.FaceModes.TWOSIDE|NMesh.FaceModes.TEX|
                       NMesh.FaceModes.TILES)
        face.mode |= NMesh.FaceModes.DYNAMIC
        if dbl:
            face.mode |= NMesh.FaceModes.TWOSIDE
        #face.transp=NMesh.FaceTranspModes.ALPHA
        face.smooth=1
        
        if image:
            for rv in uv:
                face.uv.append((rv.s, rv.t))
                face.mode |= NMesh.FaceModes.TEX
                face.image = image
            mesh.hasFaceUV(1)
    
        for rv in v:
            for nmv in mesh.verts:
                if rv.equals(Vertex(nmv.co[0],
                                    nmv.co[1],
                                    nmv.co[2])):
                    nmv.co[0]=(nmv.co[0]+rv.x)/2
                    nmv.co[1]=(nmv.co[1]+rv.y)/2
                    nmv.co[2]=(nmv.co[2]+rv.z)/2
                    face.v.append(nmv)
                    break
            else:
                nmv=NMesh.Vert(rv.x,rv.y,rv.z)
                mesh.verts.append(nmv)
                face.v.append(nmv)
                            
        mesh.faces.append(face)
    

    #------------------------------------------------------------------------
    def addFacePart(self, mesh, v, uv, c1, c2, rw, tw, image):

        if c1==0 or c1==1:
            nr1=0
            nt1=0
        else:
            nr1=rw
            nt1=tw

        if c2==0 or c2==1:
            nr2=0
            nt2=0
        else:
            nr2=rw
            nt2=tw

        croot=v[3].y-v[0].y
        ctip=v[2].y-v[1].y
        
        # assumes normal.x == 0 for simplicity
        nv=[v[0] + Vertex(0, croot*c1, croot*nr1),
            v[1] + Vertex(0, ctip *c1, ctip *nt1),
            v[1] + Vertex(0, ctip *c2, ctip *nt2),
            v[0] + Vertex(0, croot*c2, croot*nr2)]

        nuv=[UV(uv[0].s+(uv[3].s-uv[0].s)*c1, uv[0].t),
             UV(uv[1].s+(uv[2].s-uv[1].s)*c1, uv[1].t),
             UV(uv[1].s+(uv[2].s-uv[1].s)*c2, uv[1].t),
             UV(uv[0].s+(uv[3].s-uv[0].s)*c2, uv[0].t)]
            
        self.addFace(mesh, nv, nuv, image)


    #------------------------------------------------------------------------
    def afl(self, aflname):
        if not aflname:
            return None
        afldir=self.filename
        for l in range(5):
            q=afldir[:-1].rfind(Blender.sys.dirsep)
            if q==-1:
                return
            afldir=afldir[:q+1]
            try:
                file = open(afldir+'Airfoils'+Blender.sys.dirsep+aflname, 'rU')
            except IOError:
                pass
            else:
                thing=file.readline(1024)
                if not thing in ["A\n", "I\n"]:
                    file.close()
                    continue
                thing=file.readline(1024)
                if thing!="700 version\n":
                    file.close()
                    continue
                thing=file.readline(1024)	# device type code
                thing=file.readline(1024)
                file.close()
                n=thing.split()
                try:
                    return float(n[1])
                except ValueError:
                    pass

        print "Warn:\tCouldn't read airfoil \"%s\"" % aflname
        return None


    #------------------------------------------------------------------------
    def wpn(self, wpnname):
        if not wpnname:
            return None
        wpndir=self.filename
        for l in range(5):
            q=wpndir[:-1].rfind(Blender.sys.dirsep)
            if q==-1:
                return
            wpndir=wpndir[:q+1]
            try:
                filename = wpndir+'Weapons'+Blender.sys.dirsep+wpnname
                w=DEFfile(filename, self.debug, None, None, '', None)
                return w
            except (ParseError, IOError):
                pass

        print "Warn:\tCouldn't read weapon \"%s\"" % wpnname
        return None
        

#------------------------------------------------------------------------
#-- DEFfile --
#------------------------------------------------------------------------
class DEFfile:
    xchr=0
    xint=1
    xflt=2
    xstruct=3
    
    engnDIM=8		# number of Engines
    wingDIM=56		# number of Wings (incl props)
    partDIM=95		# number of Parts (incl wings)
    gearDIM=10		# number of Gear
    wattDIM=24		# number of Weapons
    doorDIM=24		# number of Doors+Speedbrakes

    partFuse=56		# used in LOD calculation
    partNace1=77	# used in texture mapping
    partNace8=84
    partFair1=85
    partFair10=94

    body_sDIM=20	# max number of segments/part
    body_rDIM=18	# max number of vertices/segment

    # gear
    GR_none  =0
    GR_skid  =1
    GR_single=2
    GR_2lat  =3
    GR_2long =4
    GR_4truck=5
    GR_6truck=6
    GR_4lat  =7
    GR_2f4a  =8
    GR_3lat  =9

    # doors
    gear_door_none=0
    gear_door_standard=1
    gear_door_attached=2
    gear_door_closed=3

    lites=[
        # name          base_value   r    g    b
        ("Taxi",        "taxilite", 1.0, 1.0, 1.0),
        ("Tail",        "taillite", 1.0, 1.0, 1.0),
        ("Rot 1 Pulse", "fuserb1",  1.0, 0.0, 0.0),
        ("Rot 2 Pulse", "fuserb2",  1.0, 0.0, 0.0)
        ]

    v7parts={
#v8  v7   s   r tex t_s1 b_s1 t_t1 b_t1 t_s2 b_s2 t_t2 b_t2
 0: ( 0,  0,  0, 0,  16,  16, 262, 262,   0,   0, 389, 389),	# Prop 1
 1: ( 1,  0,  0, 0,  16,  16, 262, 262,   0,   0, 389, 389),	# Prop 2
 2: ( 2,  0,  0, 0,  16,  16, 262, 262,   0,   0, 389, 389),	# Prop 3
 3: ( 3,  0,  0, 0,  16,  16, 262, 262,   0,   0, 389, 389),	# Prop 4
 4: ( 4,  0,  0, 0,  16,  16, 262, 262,   0,   0, 389, 389),	# Prop 5
 5: ( 5,  0,  0, 0,  16,  16, 262, 262,   0,   0, 389, 389),	# Prop 6
 6: ( 6,  0,  0, 0,  16,  16, 262, 262,   0,   0, 389, 389),	# Prop 7
 7: ( 7,  0,  0, 0,  16,  16, 262, 262,   0,   0, 389, 389),	# Prop 8
 8: ( 8,  0,  0, 0, 774, 774,   0,   0,1024,1024, 393, 393),	# Wing 1 Left
 9: ( 9,  0,  0, 0, 774, 774,   0,   0,1024,1024, 393, 393),	# Wing 1 Right
10: (10,  0,  0, 0, 522, 522,   0,   0, 772, 772, 259, 259),	# Wing 2 Left
11: (11,  0,  0, 0, 522, 522,   0,   0, 772, 772, 259, 259),	# Wing 2 Right
12: (12,  0,  0, 0, 522, 522, 262, 262, 646, 646, 393, 393),	# Wing 3 Left
13: (13,  0,  0, 0, 522, 522, 262, 262, 646, 646, 393, 393),	# Wing 3 Right
14: (14,  0,  0, 0, 648, 648, 262, 262, 772, 772, 393, 393),	# Wing 4 Left
15: (15,  0,  0, 0, 648, 648, 262, 262, 772, 772, 393, 393),	# Wing 4 Right
16: (16,  0,  0, 0, 774, 774, 522, 522,1024,1024, 772, 772),	# HStab Left
17: (17,  0,  0, 0, 774, 774, 522, 522,1024,1024, 772, 772),	# HStab Right
18: (18,  0,  0, 0,  18, 270,   0,   0, 268, 520, 259, 259),	# VStab 1
19: (19,  0,  0, 0,  18, 270, 261, 261, 268, 520, 520, 520),	# VStab 2
20: (20,  0,  0, 1,   0,   0, 516, 516, 128, 128,1024,1024),	# Misc Wing 1
21: (21,  0,  0, 1, 127, 127, 516, 516, 256, 256,1024,1024),	# Misc Wing 2
22: (22,  0,  0, 1, 255, 255, 516, 516, 384, 384,1024,1024),	# Misc Wing 3
23: (23,  0,  0, 1, 383, 383, 516, 516, 512, 512,1024,1024),	# Misc Wing 4
24: (24,  0,  0, 1, 511, 511, 516, 516, 640, 640,1024,1024),	# Misc Wing 5
25: (25,  0,  0, 1, 639, 639, 516, 516, 768, 768,1024,1024),	# Misc Wing 6
26: (26,  0,  0, 1, 767, 767, 516, 516, 896, 896,1024,1024),	# Misc Wing 7
27: (27,  0,  0, 1, 895, 895, 516, 516,1024,1024,1024,1024),	# Misc Wing 8
40: (28,  0,  0, 0, 774, 774, 458, 458,1024,1024, 520, 520),	# Pylon 1 Egn 1
41: (29,  0,  0, 0, 774, 774, 458, 458,1024,1024, 520, 520),	# Pylon 1 Egn 2
42: (30,  0,  0, 0, 774, 774, 458, 458,1024,1024, 520, 520),	# Pylon 1 Egn 3
43: (31,  0,  0, 0, 774, 774, 458, 458,1024,1024, 520, 520),	# Pylon 1 Egn 4
44: (32,  0,  0, 0, 774, 774, 458, 458,1024,1024, 520, 520),	# Pylon 1 Egn 5
45: (33,  0,  0, 0, 774, 774, 458, 458,1024,1024, 520, 520),	# Pylon 1 Egn 6
46: (34,  0,  0, 0, 774, 774, 458, 458,1024,1024, 520, 520),	# Pylon 1 Egn 7
47: (35,  0,  0, 0, 774, 774, 458, 458,1024,1024, 520, 520),	# Pylon 1 Egn 8
48: (36,  0,  0, 0, 774, 774, 395, 395,1024,1024, 456, 456),	# Pylon 2 Egn 1
49: (37,  0,  0, 0, 774, 774, 395, 395,1024,1024, 456, 456),	# Pylon 2 Egn 2
50: (38,  0,  0, 0, 774, 774, 395, 395,1024,1024, 456, 456),	# Pylon 2 Egn 3
51: (39,  0,  0, 0, 774, 774, 395, 395,1024,1024, 456, 456),	# Pylon 2 Egn 4
52: (40,  0,  0, 0, 774, 774, 395, 395,1024,1024, 456, 456),	# Pylon 2 Egn 5
53: (41,  0,  0, 0, 774, 774, 395, 395,1024,1024, 456, 456),	# Pylon 2 Egn 6
54: (42,  0,  0, 0, 774, 774, 395, 395,1024,1024, 456, 456),	# Pylon 2 Egn 7
55: (43,  0,  0, 0, 774, 774, 395, 395,1024,1024, 456, 456),	# Pylon 2 Egn 8
56: (44, 20, 18, 0,   0,   0, 774, 522, 772, 772,1024, 772),	# Fuselage
57: (45, 12, 18, 0, 522, 522, 395, 395, 772, 772, 520, 520),	# Misc Body 1
58: (46, 12, 18, 0, 522, 522, 395, 395, 772, 772, 520, 520),	# Misc Body 2
59: (47, 12, 18, 1, 255, 255,   0,   0, 384, 384, 508, 508),	# Misc Body 3
60: (48, 12, 18, 1, 383, 383,   0,   0, 512, 512, 508, 508),	# Misc Body 4
61: (49, 12, 18, 1, 511, 511,   0,   0, 640, 640, 508, 508),	# Misc Body 5
62: (50, 12, 18, 1, 639, 639,   0,   0, 768, 768, 508, 508),	# Misc Body 6
63: (51, 12, 18, 1, 767, 767,   0,   0, 896, 896, 508, 508),	# Misc Body 7
64: (52, 12, 18, 1, 895, 895,   0,   0,1024,1024, 508, 508),	# Misc Body 8
77: (53, 12, 18, 0, 774, 774, 900, 774,1024,1024,1024, 898),	# Nacelle 1
78: (54, 12, 18, 0, 774, 774, 900, 774,1024,1024,1024, 898),	# Nacelle 2
79: (55, 12, 18, 0, 774, 774, 900, 774,1024,1024,1024, 898),	# Nacelle 3
80: (56, 12, 18, 0, 774, 774, 900, 774,1024,1024,1024, 898),	# Nacelle 4
81: (57, 12, 18, 0, 774, 774, 900, 774,1024,1024,1024, 898),	# Nacelle 5
82: (58, 12, 18, 0, 774, 774, 900, 774,1024,1024,1024, 898),	# Nacelle 6
83: (59, 12, 18, 0, 774, 774, 900, 774,1024,1024,1024, 898),	# Nacelle 7
84: (60, 12, 18, 0, 774, 774, 900, 774,1024,1024,1024, 898),	# Nacelle 8
85: (61,  8, 10, 0,   0,   0, 393, 393,  16,  16, 520, 520),	# Fairing 1
86: (62,  8, 10, 0,   0,   0, 393, 393,  16,  16, 520, 520),	# Fairing 2
87: (63,  8, 10, 0,   0,   0, 393, 393,  16,  16, 520, 520),	# Fairing 3
88: (64,  8, 10, 0,   0,   0, 393, 393,  16,  16, 520, 520),	# Fairing 4
89: (65,  8, 10, 0,   0,   0, 393, 393,  16,  16, 520, 520),	# Fairing 5
90: (66,  8, 10, 0,   0,   0, 393, 393,  16,  16, 520, 520),	# Fairing 6
	}

    wings=[
        # name			p
        ("Wing 1 Left",		8),
        ("Wing 1 Right",	9),
        ("Wing 2 Left",		10),
        ("Wing 2 Right",	11),
        ("Wing 3 Left",		12),
        ("Wing 3 Right",	13),
        ("Wing 4 Left",		14),
        ("Wing 4 Right",	15),
        ("HStab Left",		16),
        ("HStab Right",		17),
        ("VStab 1",		18),
        ("VStab 2",		19),
        ("Misc Wing 1",		20),
        ("Misc Wing 2",		21),
        ("Misc Wing 3",		22),
        ("Misc Wing 4",		23),
        ("Misc Wing 5",		24),
        ("Misc Wing 6",		25),
        ("Misc Wing 7",		26),
        ("Misc Wing 8",		27),
        ("Misc Wing 9",		28),
        ("Misc Wing 10",	29),
        ("Misc Wing 11",	30),
        ("Misc Wing 12",	31),
        ("Misc Wing 13",	32),
        ("Misc Wing 14",	33),
        ("Misc Wing 15",	34),
        ("Misc Wing 16",	35),
        ("Misc Wing 17",	36),
        ("Misc Wing 18",	37),
        ("Misc Wing 19",	38),
        ("Misc Wing 20",	39),
        ("Eng 1 Pylon 1",	40),
        ("Eng 2 Pylon 1",	41),
        ("Eng 3 Pylon 1",	42),
        ("Eng 4 Pylon 1",	43),
        ("Eng 5 Pylon 1",	44),
        ("Eng 6 Pylon 1",	45),
        ("Eng 7 Pylon 1",	46),
        ("Eng 8 Pylon 1",	47),
        ("Eng 1 Pylon 2",	48),
        ("Eng 2 Pylon 2",	49),
        ("Eng 3 Pylon 2",	50),
        ("Eng 4 Pylon 2",	51),
        ("Eng 5 Pylon 2",	52),
        ("Eng 6 Pylon 2",	53),
        ("Eng 7 Pylon 2",	54),
        ("Eng 8 Pylon 2",	55),
        ]

    parts=[
        # name 			p
        ("Fuselage",		56),
        ("Misc Body 1",		57),
        ("Misc Body 2",		58),
        ("Misc Body 3",		59),
        ("Misc Body 4",		60),
        ("Misc Body 5",		61),
        ("Misc Body 6",		62),
        ("Misc Body 7",		63),
        ("Misc Body 8",		64),
        ("Misc Body 9",		65),
        ("Misc Body 10",	66),
        ("Misc Body 11",	67),
        ("Misc Body 12",	68),
        ("Misc Body 13",	69),
        ("Misc Body 14",	70),
        ("Misc Body 15",	71),
        ("Misc Body 16",	72),
        ("Misc Body 17",	73),
        ("Misc Body 18",	74),
        ("Misc Body 19",	75),
        ("Misc Body 20",	76),
        ("Nacelle 1",		77),
        ("Nacelle 2",		78),
        ("Nacelle 3",		79),
        ("Nacelle 4",		80),
        ("Nacelle 5",		81),
        ("Nacelle 6",		82),
        ("Nacelle 7",		83),
        ("Nacelle 8",		84),
        ("Fairing 1",		85),
        ("Fairing 2",		86),
        ("Fairing 3",		87),
        ("Fairing 4",		88),
        ("Fairing 5",		89),
        ("Fairing 6",		90),
        ("Fairing 7",		91),
        ("Fairing 8",		92),
        ("Fairing 9",		93),
        ("Fairing 10",		94),
        ]

    #       tex    tw   th
    doors=(1, 631, 14, 128)
        

    #------------------------------------------------------------------------
    # Derived from ACF740.def by Stanislaw Pusep
    #   http://sysd.org/xplane/acftools/ACF740.def
    # and from X-Plane v7 docs
    #   ./Instructions/Manual_Files/X-Plane ACF_format.html
    acf740 = [
#xchr, "HEADER_platform",
#xint, "HEADER_version",
xflt, "HEADER_filler",
xchr, "VIEW_name[500]",
xchr, "VIEW_path[500]",
xchr, "VIEW_tailnum[40]",
xchr, "VIEW_author[500]",
xchr, "VIEW_descrip[500]",
xflt, "VIEW_Vmca_kts",
xflt, "VIEW_Vso_kts",
xflt, "VIEW_Vs_kts",
xflt, "VIEW_Vyse_kts",
xflt, "VIEW_Vfe_kts",
xflt, "VIEW_Vle_kts",
xflt, "VIEW_Vno_kts",
xflt, "VIEW_Vne_kts",
xflt, "VIEW_Mmo",
xflt, "VIEW_Gneg",
xflt, "VIEW_Gpos",
xint, "VIEW_has_navlites",
xflt, "VIEW_pe_xyz[3]",
xint, "VIEW_has_lanlite1",
xflt, "VIEW_lanlite1_xyz[3]",
xint, "VIEW_has_lanlite2",
xflt, "VIEW_lanlite2_xyz[3]",
xint, "VIEW_has_taxilite",
xflt, "VIEW_taxilite_xyz[3]",
xint, "VIEW_has_fuserb1",
xflt, "VIEW_fuserb1_xyz[3]",
xint, "VIEW_has_fuserb2",
xflt, "VIEW_fuserb2_xyz[3]",
xint, "VIEW_has_taillite",
xflt, "VIEW_taillite_xyz[3]",
xint, "VIEW_has_refuel",
xflt, "VIEW_refuel_xyz[3]",
xflt, "VIEW_yawstring_x",
xflt, "VIEW_yawstring_y",
xflt, "VIEW_HUD_ctr_x",
xflt, "VIEW_HUD_ctr_y_OLD",
xflt, "VIEW_HUD_del_x",
xflt, "VIEW_HUD_del_y",
xint, "VIEW_lan_lite_steers",
xflt, "VIEW_lan_lite_power",
xflt, "VIEW_lan_lite_width",
xflt, "VIEW_lan_lite_the_ref",
xflt, "VIEW_stall_warn_aoa",
xflt, "VIEW_tow_hook_Y",
xflt, "VIEW_tow_hook_Z",
xflt, "VIEW_win_hook_Y",
xflt, "VIEW_win_hook_Z",
xint, "VIEW_has_HOOPS_HUD",
xint, "VIEW_cockpit_type",
xint, "VIEW_asi_is_kts",
xint, "VIEW_warn1_EQ",
xint, "VIEW_warn2_EQ",
xint, "VIEW_is_glossy",
xint, "VIEW_draw_geo_frnt_views",
xint, "VIEW_draw_geo_side_views",
xint, "VIEW_ins_type[300]",
xflt, "VIEW_ins_size[300]",
xflt, "VIEW_ins_x[300]",
xflt, "VIEW_ins_y[300]",
xint, "VIEW_cus_rnd_use[50]",
xflt, "VIEW_cus_rnd_lo_val[50]",
xflt, "VIEW_cus_rnd_hi_val[50]",
xflt, "VIEW_cus_rnd_lo_ang[50]",
xflt, "VIEW_cus_rnd_hi_ang[50]",
xint, "VIEW_cus_rnd_mirror[50]",
xint, "VIEW_cus_rnd_label[50]",
xint, "VIEW_cus_dig_use[50]",
xflt, "VIEW_cus_dig_offset[50]",
xflt, "VIEW_cus_dig_scale[50]",
xint, "VIEW_cus_dig_dig[50]",
xint, "VIEW_cus_dig_dec[50]",
xint, "ENGINE_num_engines",
xint, "ENGINE_num_thrustpoints",
xflt, "ENGINE_throt_max_FWD",
xflt, "ENGINE_throt_max_REV",
xflt, "ENGINE_idle_rat[2]",
xint, "ENGINE_linked_prop_EQ",
xint, "ENGINE_beta_prop_EQ",
xint, "ENGINE_auto_feather_EQ",
xint, "ENGINE_rev_thrust_EQ",
xint, "ENGINE_drive_by_wire_EQ",
xflt, "ENGINE_feathered_pitch",
xflt, "ENGINE_reversed_pitch",
xflt, "ENGINE_rotor_mi_rat",
xflt, "ENGINE_tip_weight",
xflt, "ENGINE_tip_mach_des_100",
xflt, "ENGINE_tip_mach_des_50",
xflt, "ENGINE_power_max",
xflt, "ENGINE_crit_alt",
xflt, "ENGINE_MP_max",
xflt, "ENGINE_trq_max_eng",
xflt, "ENGINE_RSC_idlespeed_ENGN",
xflt, "ENGINE_RSC_redline_ENGN",
xflt, "ENGINE_RSC_idlespeed_PROP",
xflt, "ENGINE_RSC_redline_PROP",
xflt, "ENGINE_RSC_mingreen_ENGN",
xflt, "ENGINE_RSC_maxgreen_ENGN",
xflt, "ENGINE_RSC_mingreen_PROP",
xflt, "ENGINE_RSC_maxgreen_PROP",
xint, "AUTO_has_press_controls",
xflt, "ENGINE_throt_time_prop",
xflt, "ENGINE_trans_loss",
xflt, "ENGINE_thrust_max",
xflt, "ENGINE_burner_inc",
xflt, "ENGINE_max_mach_eff",
xflt, "ENGINE_face_jet",
xflt, "ENGINE_throt_time_jet",
xflt, "ENGINE_lift_fan_rat",
xflt, "ENGINE_rock_max_sl",
xflt, "ENGINE_rock_max_opt",
xflt, "ENGINE_rock_max_vac",
xflt, "ENGINE_rock_h_opt",
xflt, "ENGINE_face_rocket",
xint, "PROP_engn_type[8]",
xint, "PROP_prop_type[8]",
xflt, "PROP_engn_mass[8]",
xint, "PROP_prop_clutch_EQ[8]",
xflt, "PROP_prop_gear_rat[8]",
xflt, "PROP_prop_dir[8]",
xflt, "PROP_num_blades[8]",
xflt, "PROP_SFC[8]",
xflt, "PROP_vert_cant_init[8]",
xflt, "PROP_side_cant_init[8]",
xflt, "PROP_min_pitch[8]",
xflt, "PROP_max_pitch[8]",
xflt, "PROP_des_rpm_prp[8]",
xflt, "PROP_des_kts_prp[8]",
xflt, "PROP_des_kts_acf[8]",
xflt, "PROP_prop_mass[8]",
xflt, "PROP_mi_prop_rpm[8]",
xflt, "PROP_mi_engn_rpm[8]",
xflt, "PROP_discarea[8]",
xflt, "PROP_ringarea[8][10]",
xflt, "PROP_bladesweep[8][10]",
xflt, "SYSTEMS_starter_rat",
xflt, "SYSTEMS_battery_rat",
xint, "SYSTEMS_hydraulic_sys",
xint, "SYSTEMS_stickshaker",
xflt, "SYSTEMS_manual_reversion_rat",
xflt, "SYSTEMS_max_press_diff",
xint, "PARTS_part_eq[73]",
xchr, "PARTS_Rafl0[73][40]",
xchr, "PARTS_Rafl1[73][40]",
xchr, "PARTS_Tafl0[73][40]",
xchr, "PARTS_Tafl1[73][40]",
xint, "PARTS_els[73]",
xflt, "PARTS_Xarm[73]",
xflt, "PARTS_Yarm[73]",
xflt, "PARTS_Zarm[73]",
xflt, "PARTS_Croot[73]",
xflt, "PARTS_Ctip[73]",
xflt, "PARTS_semilen_SEG[73]",
xflt, "PARTS_semilen_JND[73]",
xflt, "PARTS_element_len[73]",
xflt, "PARTS_X_body_aero[73]",
xflt, "PARTS_Y_body_aero[73]",
xflt, "PARTS_Z_body_aero[73]",
xflt, "PARTS_dihed1[73]",
xflt, "PARTS_dihed2[73]",
xflt, "PARTS_dihednow[73]",
xint, "PARTS_vardihed[73]",
xint, "CONTROLS_vardihedEQ",
xflt, "PARTS_sweep1[73]",
xflt, "PARTS_sweep2[73]",
xflt, "PARTS_sweepnow[73]",
xint, "PARTS_varsweep[73]",
xint, "CONTROLS_varsweepEQ",
xflt, "PARTS_e[73]",
xflt, "PARTS_AR[73]",
xflt, "PARTS_al_D_al0[73]",
xflt, "PARTS_cl_D_cl0[73]",
xflt, "PARTS_cm_D_cm0[73]",
xflt, "PARTS_delta_fac[73]",
xflt, "PARTS_spec_wash[73]",
xflt, "PARTS_alpha_max[73]",
xflt, "PARTS_slat_effect[73]",
xflt, "PARTS_s[73][10]",
xflt, "PARTS_mac[73][10]",
xflt, "PARTS_incidence[73][10]",
xint, "PARTS_ail1[73][10]",
xflt, "PARTS_ail1_elR[73]",
xflt, "PARTS_ail1_elT[73]",
xflt, "CONTROLS_ail1_cratR",
xflt, "CONTROLS_ail1_cratT",
xflt, "CONTROLS_ail1_up",
xflt, "CONTROLS_ail1_dn",
xint, "PARTS_ail2[73][10]",
xflt, "PARTS_ail2_elR[73]",
xflt, "PARTS_ail2_elT[73]",
xflt, "CONTROLS_ail2_cratR",
xflt, "CONTROLS_ail2_cratT",
xflt, "CONTROLS_ail2_up",
xflt, "CONTROLS_ail2_dn",
xint, "PARTS_elv1[73][10]",
xflt, "PARTS_elv1_elR[73]",
xflt, "PARTS_elv1_elT[73]",
xflt, "CONTROLS_elv1_cratR",
xflt, "CONTROLS_elv1_cratT",
xflt, "CONTROLS_elv1_up",
xflt, "CONTROLS_elv1_dn",
xint, "PARTS_rud1[73][10]",
xflt, "PARTS_rud1_elR[73]",
xflt, "PARTS_rud1_elT[73]",
xflt, "CONTROLS_rud1_cratR",
xflt, "CONTROLS_rud1_cratT",
xflt, "CONTROLS_rud1_lft",
xint, "PARTS_spo1[73][10]",
xflt, "PARTS_spo1_elR[73]",
xflt, "PARTS_spo1_elT[73]",
xflt, "CONTROLS_spo1_cratR",
xflt, "CONTROLS_spo1_cratT",
xflt, "CONTROLS_spo1_up",
xint, "PARTS_yawb[73][10]",
xflt, "PARTS_yawb_elR[73]",
xflt, "PARTS_yawb_elT[73]",
xflt, "CONTROLS_yawb_cratR",
xflt, "CONTROLS_yawb_cratT",
xflt, "CONTROLS_yawb_ud",
xint, "PARTS_sbrk[73][10]",
xflt, "PARTS_sbrk_elR[73]",
xflt, "PARTS_sbrk_elT[73]",
xflt, "CONTROLS_sbrk_cratR",
xflt, "CONTROLS_sbrk_cratT",
xflt, "CONTROLS_sbrk_up",
xint, "CONTROLS_sbrk_EQ",
xint, "PARTS_fla1[73][10]",
xflt, "PARTS_fla1_elR[73]",
xflt, "PARTS_fla1_elT[73]",
xflt, "CONTROLS_fla1_cratR",
xflt, "CONTROLS_fla1_cratT",
xflt, "CONTROLS_fla1_dn[8]",
xint, "CONTROLS_flap_EQ",
xint, "PARTS_slat[73][10]",
xflt, "CONTROLS_slat_inc",
xint, "CONTROLS_slat_EQ",
xint, "PARTS_inc_ail1[73][10]",
xint, "PARTS_inc_ail2[73][10]",
xint, "PARTS_inc_elev[73][10]",
xint, "PARTS_inc_rudd[73][10]",
xint, "PARTS_inc_vect[73][10]",
xint, "PARTS_inc_trim[73][10]",
xint, "CONTROLS_in_downwash[73][73][10]",
xflt, "PARTS_body_r[73]",
xflt, "PARTS_body_X[73][20][18]",
xflt, "PARTS_body_Y[73][20][18]",
xflt, "PARTS_body_Z[73][20][18]",
xint, "PARTS_gear_type[73]",
xflt, "PARTS_gear_latE[73]",
xflt, "PARTS_gear_lonE[73]",
xflt, "PARTS_gear_axiE[73]",
xflt, "PARTS_gear_latR[73]",
xflt, "PARTS_gear_lonR[73]",
xflt, "PARTS_gear_axiR[73]",
xflt, "PARTS_gear_latN[73]",
xflt, "PARTS_gear_lonN[73]",
xflt, "PARTS_gear_axiN[73]",
xflt, "PARTS_gear_xnodef[73]",
xflt, "PARTS_gear_ynodef[73]",
xflt, "PARTS_gear_znodef[73]",
xflt, "PARTS_gear_leglen[73]",
xflt, "PARTS_tire_radius[73]",
xflt, "PARTS_tire_swidth[73]",
xflt, "PARTS_gearcon[73]",
xflt, "PARTS_geardmp[73]",
xflt, "PARTS_gear_deploy[73]",
xflt, "PARTS_gearstatdef[73]",
xflt, "PARTS_dummy[73]",
xint, "PARTS_gear_steers[73]",
xflt, "PARTS_gear_cyctim[73]",
xflt, "BODIES_fuse_cd",
xflt, "CONTROLS_hstb_trim_up",
xflt, "CONTROLS_hstb_trim_dn",
xint, "CONTROLS_flap_type",
xint, "CONTROLS_con_smooth",
xint, "CONTROLS_flap_detents",
xflt, "CONTROLS_flap_deftime",
xflt, "CONTROLS_flap_cl",
xflt, "CONTROLS_flap_cd",
xflt, "CONTROLS_flap_cm",
xflt, "CONTROLS_blown_flap_add_speed",
xflt, "CONTROLS_blown_flap_throt_red",
xflt, "CONTROLS_blown_flap_min_engag",
xint, "CONTROLS_blow_all_controls",
xint, "GEAR_gear_retract",
xflt, "GEAR_nw_steerdeg1",
xflt, "GEAR_nw_steerdeg2",
xflt, "GEAR_nw_cutoff_omega",
xflt, "GEAR_nw_side_k",
xflt, "GEAR_gear_door_size",
xflt, "GEAR_water_rud_Z",
xflt, "GEAR_water_rud_area",
xflt, "GEAR_water_rud_maxdef",
xflt, "GEAR_roll_co",
xflt, "GEAR_brake_co",
xint, "GEAR_gear_door_typ[10]",
xflt, "GEAR_gear_door_loc[10][3]",
xflt, "GEAR_gear_door_geo[10][4][3]",
xflt, "GEAR_gear_door_axi_rot[10]",
xflt, "GEAR_gear_door_ext_ang[10]",
xflt, "GEAR_gear_door_ret_ang[10]",
xflt, "GEAR_gear_door_ang_now[10]",
xflt, "WB_cgY",
xflt, "WB_cgZ",
xflt, "WB_cgZ_fwd",
xflt, "WB_cgZ_aft",
xflt, "WB_m_empty",
xflt, "WB_m_fuel_tot",
xflt, "WB_m_jettison",
xflt, "WB_m_max",
xflt, "WB_m_displaced",
xflt, "WB_Jxx_unitmass",
xflt, "WB_Jyy_unitmass",
xflt, "WB_Jzz_unitmass",
xint, "WB_num_tanks",
xflt, "WB_tank_rat[3]",
xflt, "WB_tank_X[3]",
xflt, "WB_tank_Y[3]",
xflt, "WB_tank_Z[3]",
xint, "WB_jett_is_slung",
xint, "WB_jett_is_water",
xflt, "WB_jett_len",
xflt, "WB_jett_xyz[3]",
xflt, "SPECIAL_flap1_roll",
xflt, "SPECIAL_flap1_ptch",
xflt, "SPECIAL_m_shift",
xflt, "SPECIAL_m_shift_dx",
xflt, "SPECIAL_m_shift_dz",
xflt, "SPECIAL_wing_tilt_ptch",
xflt, "SPECIAL_wing_tilt_roll",
xflt, "SPECIAL_tvec_ptch",
xflt, "SPECIAL_tvec_roll",
xflt, "SPECIAL_tvec_hdng",
xflt, "SPECIAL_jato_Y",
xflt, "SPECIAL_jato_Z",
xflt, "SPECIAL_jato_theta",
xflt, "SPECIAL_jato_thrust",
xflt, "SPECIAL_jato_dur",
xflt, "SPECIAL_jato_sfc",
xflt, "SPECIAL_stab_roll",
xflt, "SPECIAL_stab_hdng",
xflt, "SPECIAL_elev_with_flap_rat",
xflt, "SPECIAL_ail1_pitch",
xflt, "SPECIAL_ail1_flaps",
xflt, "SPECIAL_ail2_pitch",
xflt, "SPECIAL_ail2_flaps",
xflt, "SPECIAL_ail2_vmax",
xflt, "SPECIAL_diff_thro_hdng",
xint, "SPECIAL_phase_ptch_tvect_in_at_90",
xint, "SPECIAL_phase_ptch_tvect_in_at_00",
xint, "SPECIAL_sbrk_on_td_EQ",
xint, "SPECIAL_fbrk_on_td_EQ",
xint, "SPECIAL_sweep_with_flaps_EQ",
xint, "SPECIAL_flaps_with_gear_EQ",
xint, "SPECIAL_slat_with_stall_EQ",
xint, "SPECIAL_anti_ice_EQ",
xint, "SPECIAL_arresting_EQ",
xint, "SPECIAL_revt_on_td_EQ",
xint, "SPECIAL_warn_gear_EQ",
xint, "SPECIAL_warn_lorot_EQ",
xint, "SPECIAL_auto_trim_EQ",
xint, "SPECIAL_flaps_with_vec_EQ",
xflt, "SPECIAL_brake_area",
xflt, "SPECIAL_brake_Y",
xflt, "SPECIAL_brake_Z",
xflt, "SPECIAL_chute_area",
xflt, "SPECIAL_chute_Y",
xflt, "SPECIAL_chute_Z",
xint, "VTOL_vect_EQ",
xint, "VTOL_auto_rpm_with_tvec",
xint, "VTOL_hide_prop_at_90_vect",
xflt, "VTOL_vect_rate",
xflt, "VTOL_vect_min_disc",
xflt, "VTOL_vect_max_disc",
xflt, "VTOL_vectarmY",
xflt, "VTOL_vectarmZ",
xflt, "VTOL_cyclic_def_elev",
xflt, "VTOL_cyclic_def_ailn",
xflt, "VTOL_flap_arm",
xflt, "VTOL_delta3",
xflt, "VTOL_puff_LMN[3]",
xflt, "VTOL_puff_xyz[3]",
xflt, "VTOL_stab_delinc_to_Vne",
xflt, "VTOL_tail_with_coll",
xflt, "VTOL_diff_coll_with_roll",
xflt, "VTOL_diff_coll_with_hdng",
xflt, "VTOL_diff_coll_with_ptch",
xflt, "VTOL_diff_cycl_with_hdng_lon",
xflt, "VTOL_diff_cycl_with_hdng_lat",
xflt, "VTOL_rotor_trim_max_fwd",
xflt, "VTOL_rotor_trim_max_aft",
xflt, "ASTAB_AShiV_old_all",
xflt, "ASTAB_ASloV_old_all",
xflt, "ASTAB_ASlo_max_thedot",
xflt, "ASTAB_ASlo_thedot_k",
xflt, "ASTAB_ASlo_max_psidot",
xflt, "ASTAB_ASlo_psidot_k",
xflt, "ASTAB_ASlo_max_phidot",
xflt, "ASTAB_ASlo_phidot_k",
xflt, "ASTAB_AShi_max_G",
xflt, "ASTAB_AShi_G_k",
xflt, "ASTAB_AShi_Gdot_k",
xflt, "ASTAB_AShi_max_alpha",
xflt, "ASTAB_AShi_alpha_k",
xflt, "ASTAB_AShi_alphadot_k",
xflt, "ASTAB_AShi_max_beta",
xflt, "ASTAB_AShi_beta_k",
xflt, "ASTAB_AShi_betadot_k",
xflt, "ASTAB_AShi_max_phidot",
xflt, "ASTAB_AShi_phidot_k",
xchr, "WEARONS_wpn_name[24][500]",
xflt, "WEARONS_x_wpn_att[24]",
xflt, "WEARONS_y_wpn_att[24]",
xflt, "WEARONS_z_wpn_att[24]",
xflt, "AUTO_est_Vs_msc",
xflt, "AUTO_size_x",
xflt, "AUTO_size_z",
xflt, "AUTO_tire_s_contact",
xflt, "WB_m_displaced_y",
xflt, "AUTO_h_eqlbm",
xflt, "AUTO_the_eqlbm",
xint, "AUTO_gear_steer_EN",
xint, "AUTO_skid_EQ",
xint, "AUTO_dummy3[7]",
xint, "AUTO_has_radar",
xint, "AUTO_has_SC_fd",
xint, "AUTO_has_DC_fd",
xint, "AUTO_has_stallwarn",
xint, "AUTO_has_clutch_switch",
xint, "AUTO_has_pre_rotate",
xint, "AUTO_has_idlespeed",
xint, "AUTO_has_FADEC_switch",
xint, "AUTO_has_litemap_tex_1",
xint, "CONTROLS_tailrotor_EQ",
xint, "CONTROLS_collective_EQ",
xflt, "ENGINE_snd_kias",
xflt, "ENGINE_snd_rpm_prp",
xflt, "ENGINE_snd_rpm_eng",
xflt, "ENGINE_snd_n1",
xflt, "VAR_INCIDENCE_inc2[73]",
xflt, "VAR_INCIDENCE_incnow[73]",
xint, "VAR_INCIDENCE_varinc[73]",
xint, "CONTROLS_varincEQ",
xflt, "SPECIAL_rudd_with_ailn_rat",
xflt, "OVERFLOW_strut_comp[73]",
xint, "OVERFLOW_is_left[73]",
xflt, "OVERFLOW_lat_sign[73]",
xint, "VTOL_jett_is_acf",
xint, "CONTROLS_collective_en",
xint, "CONTROLS_flying_stab_EQ",
xflt, "OVERFLOW_dummy4[7]",
xflt, "SPECIAL_diff_thro_ptch",
xflt, "SPECIAL_diff_thro_roll",
xint, "SPECIAL_phase_roll_tvect_in_at_90",
xint, "SPECIAL_phase_roll_tvect_in_at_00",
xint, "SPECIAL_phase_hdng_tvect_in_at_90",
xint, "SPECIAL_phase_hdng_tvect_in_at_00",
xint, "AUTO_has_asi_set",
xint, "AUTO_has_hdg_set",
xint, "AUTO_has_alt_set",
xflt, "ASTAB_ASlo_the_V",
xflt, "ASTAB_ASlo_psi_V",
xflt, "ASTAB_ASlo_phi_V",
xflt, "ASTAB_AShi_the_V",
xflt, "ASTAB_AShi_psi_V",
xflt, "ASTAB_AShi_phi_V",
xflt, "SPECIAL_spo1_vmax",
xflt, "ENGINE_max_boost_pas",
xflt, "CONTROLS_min_trim_elev",
xflt, "CONTROLS_max_trim_elev",
xflt, "CONTROLS_min_trim_ailn",
xflt, "CONTROLS_max_trim_ailn",
xflt, "CONTROLS_min_trim_rudd",
xflt, "CONTROLS_max_trim_rudd",
xflt, "VIEW_lan_lite_psi_ref",
xint, "AUTO_has_mixture",
xflt, "OVERFLOW_TR[73]",
xint, "AUTO_gear_EQ",
xint, "VIEW_cus_non_lin[50]",
xint, "VIEW_cus_doub_val[50]",
xint, "AUTO_beacon_EQ",
xint, "AUTO_has_kts_mac",
xflt, "CONTROLS_elev_trim_speedrat",
xflt, "CONTROLS_ailn_trim_speedrat",
xflt, "CONTROLS_rudd_trim_speedrat",
xflt, "WB_disp_rat",
xflt, "ENGINE_exhaust_rat",
xint, "ASTAB_lo_speed_is_position",
xflt, "ASTAB_ASlo_max_the",
xflt, "ASTAB_ASlo_the_k",
xflt, "ASTAB_ASlo_max_phi",
xflt, "ASTAB_ASlo_phi_k",
xint, "OVERFLOW_is_ducted[8]",
xflt, "WEAPONS_the_wpn_att[24]",
xflt, "WEAPONS_psi_wpn_att[24]",
xflt, "VIEW_big_panel_pix_default",
xflt, "VIEW_HUD_ctr_y[9]",
xint, "PARTS_spo2[73][10]",
xflt, "PARTS_spo2_elR[73]",
xflt, "PARTS_spo2_elT[73]",
xflt, "CONTROLS_spo2_cratR",
xflt, "CONTROLS_spo2_cratT",
xflt, "CONTROLS_spo2_up",
xflt, "SPECIAL_spo2_vmax",
xflt, "SPECIAL_ail1_vmax",
xflt, "CONTROLS_roll_to_eng_spo1",
xflt, "CONTROLS_roll_to_eng_spo2",
xflt, "OVERFLOW_dummy2[73]",
xflt, "ENGINE_EPR_max",
xint, "SPECIAL_sweep_with_vect_EQ",
xint, "HEADER_old_cus_layers",
xint, "AUTO_has_litemap_tex_2",
xflt, "VTOL_disc_tilt_elev",
xflt, "VTOL_disc_tilt_ailn",
xflt, "VIEW_lan_lite_psi_off",
xflt, "VIEW_lan_lite_the_off",
xflt, "ENGINE_inertia_rat_prop",
xflt, "ENGINE_fuel_intro_time_jet",
xflt, "OVERFLOW_tire_mi[73]",
xflt, "VTOL_vect_min_nace",
xflt, "VTOL_vect_max_nace",
xint, "WB_manual_rad_gyr",
xflt, "ENGINE_max_ITT",
xflt, "ENGINE_max_EGT",
xflt, "ENGINE_fuel_intro_time_prop",
xflt, "ENGINE_spool_time_jet",
xflt, "CONTROLS_takeoff_trim",
xflt, "AUTO_average_mac_acf",
xint, "OTTO_custom_autopilot",
xflt, "OTTO_ott_asi_ratio",
xflt, "OTTO_ott_asi_sec_into_future",
xflt, "OTTO_ott_asi_kts_off_for_full_def",
xflt, "OTTO_ott_phi_ratio",
xflt, "OTTO_ott_phi_sec_into_future",
xflt, "OTTO_ott_phi_deg_off_for_full_def",
xflt, "OTTO_ott_phi_sec_to_tune",
xflt, "OTTO_ott_def_sec_into_future",
xflt, "OTTO_ott_def_dot_off_for_full_def",
xflt, "OTTO_ott_def_sec_to_tune",
xflt, "OTTO_ott_the_ratio",
xflt, "OTTO_ott_the_sec_into_future",
xflt, "OTTO_ott_the_deg_off_for_full_def",
xflt, "OTTO_ott_the_sec_to_tune",
xflt, "OVERFLOW_xflt_overflow[2]",
xflt, "VIEW_cockpit_xyz[3]",
xflt, "WEAPONS_roll_wpn_att[24]",
xflt, "OVERFLOW_xflt_overflow[177]",
xchr, "HEADER_is_hm",
xchr, "HEADER_is_ga",
xchr, "VIEW_ICAO[40]",
xchr, "OVERFLOW_xchr_overflow[2]",
xflt, "OVERFLOW_heading[73]",
xflt, "OVERFLOW_pitch[73]",
xflt, "OVERFLOW_roll[73]",
xflt, "OVERFLOW_xflt_overflow[20]",
    ]

    #------------------------------------------------------------------------
    # Derived from hl_acf_structs.h
    # with help from Michael Ista
    acf810 = [
#xchr, "HEADER_platform",
#xint, "HEADER_version",
xint, "HEADER_is_hm",
xint, "HEADER_is_ga",
xint, "HEADER_old_cus_layers",

xchr, "VIEW_name[500]",
xchr, "VIEW_path[500]",
xchr, "VIEW_tailnum[40]",
xchr, "VIEW_author[500]",
xchr, "VIEW_descrip[500]",
xchr, "VIEW_ICAO[40]",
xflt, "VIEW_Vmca_kts",
xflt, "VIEW_Vso_kts",
xflt, "VIEW_Vs_kts",
xflt, "VIEW_Vyse_kts",
xflt, "VIEW_Vfe_kts",
xflt, "VIEW_Vle_kts",
xflt, "VIEW_Vno_kts",
xflt, "VIEW_Vne_kts",
xflt, "VIEW_Mmo",
xflt, "VIEW_Gneg",
xflt, "VIEW_Gpos",
xint, "VIEW_has_lanlite1",
xflt, "VIEW_lanlite1_xyz[3]",
xint, "VIEW_has_lanlite2",
xflt, "VIEW_lanlite2_xyz[3]",
xint, "VIEW_has_taxilite",
xflt, "VIEW_taxilite_xyz[3]",
xint, "VIEW_has_fuserb1",
xflt, "VIEW_fuserb1_xyz[3]",
xint, "VIEW_has_fuserb2",
xflt, "VIEW_fuserb2_xyz[3]",
xint, "VIEW_has_taillite",
xflt, "VIEW_taillite_xyz[3]",
xint, "VIEW_has_refuel",
xflt, "VIEW_refuel_xyz[3]",
xint, "VIEW_has_navlites",
xflt, "VIEW_pe_xyz[3]",
xint, "VIEW_cockpit_M_inn",
xflt, "VIEW_cockpit_xyz[3]",
xflt, "VIEW_lanliteC_xyz[3]",
xint, "VIEW_plot_OBJ7_cock[3]",
xint, "VIEW_plot_outer_acf[3]",
xint, "VIEW_plot_inner_acf[3]",
xflt, "VIEW_yawstring_x",
xflt, "VIEW_yawstring_y",
xflt, "VIEW_HUD_ctr_x",
xflt, "VIEW_HUD_ctr_y[9]",
xflt, "VIEW_HUD_del_x",
xflt, "VIEW_HUD_del_y",
xflt, "VIEW_big_panel_pix_default",
xflt, "VIEW_stall_warn_aoa",
xint, "VIEW_lan_lite_steers",
xflt, "VIEW_lan_lite_power",
xflt, "VIEW_lan_lite_width",
xflt, "VIEW_lan_lite_psi_ref",
xflt, "VIEW_lan_lite_psi_off",
xflt, "VIEW_lan_lite_the_ref",
xflt, "VIEW_lan_lite_psi_off",
xflt, "VIEW_tow_hook_Y",
xflt, "VIEW_tow_hook_Z",
xflt, "VIEW_win_hook_Y",
xflt, "VIEW_win_hook_Z",
xint, "VIEW_has_HOOPS_HUD",
xint, "VIEW_asi_is_kts",
xint, "VIEW_cockpit_type",
xint, "VIEW_warn1_EQ",
xint, "VIEW_warn2_EQ",
xint, "VIEW_is_glossy",

xint, "VIEW_cus_rnd_use[50]",
xflt, "VIEW_cus_rnd_lo_val[50]",
xflt, "VIEW_cus_rnd_hi_val[50]",
xflt, "VIEW_cus_rnd_lo_ang[50]",
xflt, "VIEW_cus_rnd_hi_ang[50]",
xint, "VIEW_cus_rnd_mirror[50]",
xint, "VIEW_cus_non_lin[50]",
xint, "VIEW_cus_doub_val[50]",
xint, "VIEW_cus_rnd_label[50]",
xint, "VIEW_cus_dig_use[50]",
xflt, "VIEW_cus_dig_offset[50]",
xflt, "VIEW_cus_dig_scale[50]",
xint, "VIEW_cus_dig_dig[50]",
xint, "VIEW_cus_dig_dec[50]",
xint, "VIEW_ins_type[300]",
xflt, "VIEW_ins_size[300]",
xflt, "VIEW_ins_x[300]",
xflt, "VIEW_ins_y[300]",

xint, "ENGINE_num_engines",
xint, "ENGINE_num_thrustpoints",
xflt, "ENGINE_throt_max_FWD",
xflt, "ENGINE_throt_max_REV",
xflt, "ENGINE_idle_rat[2]",
xint, "ENGINE_linked_prop_EQ",
xint, "ENGINE_drive_by_wire_EQ",
xint, "ENGINE_beta_prop_EQ",
xint, "ENGINE_rev_thrust_EQ",
xint, "ENGINE_auto_feather_EQ",
xint, "ENGINE_feather_with_prop_EQ",
xint, "ENGINE_auto_rpm_EQ",
xflt, "ENGINE_feathered_pitch",
xflt, "ENGINE_reversed_pitch",
xflt, "ENGINE_rotor_mi_rat",
xflt, "ENGINE_tip_weight",
xflt, "ENGINE_tip_mach_des_100",
xflt, "ENGINE_tip_mach_des_50",
xflt, "ENGINE_power_max",
xflt, "ENGINE_crit_alt_prop",
xflt, "ENGINE_trans_loss",
xflt, "ENGINE_MP_max",
xflt, "ENGINE_trq_max_eng",
xflt, "ENGINE_max_boost_pas_prop",
xflt, "ENGINE_RSC_idlespeed_ENGN",
xflt, "ENGINE_RSC_redline_ENGN",
xflt, "ENGINE_RSC_idlespeed_PROP",
xflt, "ENGINE_RSC_redline_PROP",
xflt, "ENGINE_RSC_mingreen_ENGN",
xflt, "ENGINE_RSC_maxgreen_ENGN",
xflt, "ENGINE_RSC_mingreen_PROP",
xflt, "ENGINE_RSC_maxgreen_PROP",
xflt, "ENGINE_auto_omega_idle",
xflt, "ENGINE_auto_omega_open",
xflt, "ENGINE_auto_omega_fire",
xflt, "ENGINE_thrust_max",
xflt, "ENGINE_burner_inc",
xflt, "ENGINE_max_mach_eff",
xflt, "ENGINE_crit_alt_jet",
xflt, "ENGINE_face_jet",
xflt, "ENGINE_dummy_was_lift_fan_rat",
xflt, "ENGINE_EPR_max",
xflt, "ENGINE_max_boost_pas_jet",
xflt, "ENGINE_rock_max_sl",
xflt, "ENGINE_rock_max_opt",
xflt, "ENGINE_rock_max_vac",
xflt, "ENGINE_rock_h_opt",
xflt, "ENGINE_face_rocket",
xflt, "ENGINE_fuel_intro_time_prop",
xflt, "ENGINE_throt_time_prop",
xflt, "ENGINE_inertia_rat_prop",
xflt, "ENGINE_fuel_intro_time_jet",
xflt, "ENGINE_throt_time_jet",
xflt, "ENGINE_spool_time_jet",

xflt, "ENGINE_max_ITT",
xflt, "ENGINE_max_EGT",
xflt, "ENGINE_max_CHT",
xflt, "ENGINE_max_OILP",
xflt, "ENGINE_max_OILT",
xflt, "ENGINE_max_FUELP",
xflt, "ENGINE_snd_kias",
xflt, "ENGINE_snd_rpm_prp",
xflt, "ENGINE_snd_rpm_eng",
xflt, "ENGINE_snd_N1",
xflt, "ENGINE_exhaust_os_xyz[3]",
xflt, "ENGINE_exhaust_rat",

xflt, "SYSTEMS_starter_rat",
xflt, "SYSTEMS_battery_rat",
xint, "SYSTEMS_hydraulic_sys",
xint, "SYSTEMS_stickshaker",
xflt, "SYSTEMS_manual_reversion_rat",
xflt, "SYSTEMS_max_press_diff",

xflt, "CONTROLS_ail1_up",
xflt, "CONTROLS_ail1_dn",
xflt, "CONTROLS_ail1_cratR",
xflt, "CONTROLS_ail1_cratT",
xflt, "CONTROLS_ail2_up",
xflt, "CONTROLS_ail2_dn",
xflt, "CONTROLS_ail2_cratR",
xflt, "CONTROLS_ail2_cratT",
xflt, "CONTROLS_spo1_up", 
xflt, "CONTROLS_spo1_cratR",
xflt, "CONTROLS_spo1_cratT",
xflt, "CONTROLS_roll_to_eng_spo1",
xflt, "CONTROLS_spo2_up",
xflt, "CONTROLS_spo2_cratR",
xflt, "CONTROLS_spo2_cratT",
xflt, "CONTROLS_roll_to_eng_spo2",
xflt, "CONTROLS_yawb_ud",
xflt, "CONTROLS_yawb_cratR",
xflt, "CONTROLS_yawb_cratT",
xflt, "CONTROLS_elv1_up",
xflt, "CONTROLS_elv1_dn",
xflt, "CONTROLS_elv1_cratR",
xflt, "CONTROLS_elv1_cratT",
xflt, "CONTROLS_rud1_lft", 
xflt, "CONTROLS_rud1_cratR",
xflt, "CONTROLS_rud1_cratT",
xflt, "CONTROLS_rud2_lft", 
xflt, "CONTROLS_rud2_cratR",
xflt, "CONTROLS_rud2_cratT",
xflt, "CONTROLS_fla1_cratR",
xflt, "CONTROLS_fla1_cratT",
xflt, "CONTROLS_fla2_cratR",
xflt, "CONTROLS_fla2_cratT",
xflt, "CONTROLS_sbrk_cratR",
xflt, "CONTROLS_sbrk_cratT",
xint, "CONTROLS_con_smooth",
xflt, "CONTROLS_sbrk_up",
xflt, "CONTROLS_takeoff_trim",
xflt, "CONTROLS_hstb_trim_up",
xflt, "CONTROLS_hstb_trim_dn",
xflt, "CONTROLS_min_trim_elev",
xflt, "CONTROLS_max_trim_elev",
xflt, "CONTROLS_elev_trim_speedrat",
xflt, "CONTROLS_elev_tab",
xflt, "CONTROLS_min_trim_ailn",
xflt, "CONTROLS_max_trim_ailn",
xflt, "CONTROLS_ailn_trim_speedrat",
xflt, "CONTROLS_ailn_tab",
xflt, "CONTROLS_min_trim_rudd",
xflt, "CONTROLS_max_trim_rudd",
xflt, "CONTROLS_rudd_trim_speedrat",
xflt, "CONTROLS_rudd_tab",
xint, "CONTROLS_flap_detents",
xflt, "CONTROLS_flap_deftime",
xint, "CONTROLS_slat_type",
xflt, "CONTROLS_slat_inc",
xflt, "CONTROLS_slat_dn[10]",
xint, "CONTROLS_fla1_type",
xflt, "CONTROLS_fla1_cl",
xflt, "CONTROLS_fla1_cd",
xflt, "CONTROLS_fla1_cm",
xflt, "CONTROLS_fla1_dn[10]",
xint, "CONTROLS_fla2_type",
xflt, "CONTROLS_fla2_cl",
xflt, "CONTROLS_fla2_cd",
xflt, "CONTROLS_fla2_cm",
xflt, "CONTROLS_fla2_dn[10]",
xflt, "CONTROLS_blown_flap_add_speed",
xflt, "CONTROLS_blown_flap_throt_red",
xflt, "CONTROLS_blown_flap_min_engag",
xint, "CONTROLS_blow_all_controls",
xint, "CONTROLS_flap_EQ",
xint, "CONTROLS_slat_EQ",
xint, "CONTROLS_sbrk_EQ",
xint, "CONTROLS_vardihed_EQ",
xint, "CONTROLS_varsweep_EQ",
xint, "CONTROLS_varinc_EQ",
xint, "CONTROLS_tailrotor_EQ",
xint, "CONTROLS_collective_EQ",
xint, "CONTROLS_collective_en",
xint, "CONTROLS_flying_stab_EQ",
xint, "CONTROLS_in_downwash[56][56][10]",

xint, "GEAR_gear_retract",
xflt, "GEAR_gear_door_size",
xflt, "GEAR_nw_steerdeg1",
xflt, "GEAR_nw_steerdeg2",
xflt, "GEAR_nw_cutoff_omega",
xflt, "GEAR_nw_side_k",
xflt, "GEAR_roll_co",
xflt, "GEAR_brake_co",
xflt, "GEAR_wheel_tire_s1[2]",
xflt, "GEAR_wheel_tire_t1[2]",
xflt, "GEAR_wheel_tire_s2[2]",
xflt, "GEAR_wheel_tire_t2[2]",
xflt, "GEAR_water_rud_Z",
xflt, "GEAR_water_rud_area",
xflt, "GEAR_water_rud_maxdef",
xflt, "GEAR_anchor_xyz[3]",

xflt, "WB_cgY",
xflt, "WB_cgZ",
xflt, "WB_cgZ_fwd",
xflt, "WB_cgZ_aft",
xflt, "WB_m_empty",
xflt, "WB_m_fuel_tot",
xflt, "WB_m_jettison",
xflt, "WB_m_max",
xflt, "WB_m_displaced",
xflt, "WB_Jxx_unitmass",
xflt, "WB_Jyy_unitmass",
xflt, "WB_Jzz_unitmass",
xint, "WB_num_tanks",
xflt, "WB_tank_rat[3]",
xflt, "WB_tank_xyz[3][3]",
xflt, "WB_jett_len",
xint, "WB_jett_is_slung",
xint, "WB_jett_is_water",
xint, "WB_jett_is_acf",
xflt, "WB_jett_xyz[3]",
xint, "WB_manual_rad_gyr",
xflt, "WB_disp_rat",
xflt, "WB_m_displaced_Y",

xint, "VTOL_vect_EQ",
xint, "VTOL_auto_rpm_with_tvec",
xint, "VTOL_hide_prop_at_90_vect",
xflt, "VTOL_vect_min_nace",
xflt, "VTOL_vect_max_nace",
xflt, "VTOL_vect_min_disc",
xflt, "VTOL_vect_max_disc",
xflt, "VTOL_cyclic_def_elev",
xflt, "VTOL_cyclic_def_ailn",
xflt, "VTOL_disc_tilt_elev",
xflt, "VTOL_disc_tilt_ailn",
xflt, "VTOL_vectarmY",
xflt, "VTOL_vectarmZ",
xflt, "VTOL_flap_arm",
xflt, "VTOL_delta3",
xflt, "VTOL_vect_rate",
xflt, "VTOL_stab_delinc_to_Vne",
xflt, "VTOL_tail_with_coll",
xflt, "VTOL_puff_LMN[3]",
xflt, "VTOL_puff_xyz[3]",
xflt, "VTOL_diff_coll_with_roll",
xflt, "VTOL_diff_coll_with_hdng",
xflt, "VTOL_diff_coll_with_ptch",
xflt, "VTOL_diff_cycl_with_hdng_lon",
xflt, "VTOL_diff_cycl_with_hdng_lat",
xflt, "VTOL_rotor_trim_max_fwd",
xflt, "VTOL_rotor_trim_max_aft",

xflt, "SPECIAL_m_shift",
xflt, "SPECIAL_m_shift_dx",
xflt, "SPECIAL_m_shift_dz",
xflt, "SPECIAL_wing_tilt_ptch",
xflt, "SPECIAL_wing_tilt_roll",
xflt, "SPECIAL_jato_Y",
xflt, "SPECIAL_jato_Z",
xflt, "SPECIAL_jato_theta",
xflt, "SPECIAL_jato_thrust",
xflt, "SPECIAL_jato_dur",
xflt, "SPECIAL_jato_sfc",
xflt, "SPECIAL_stab_roll",
xflt, "SPECIAL_rudd_with_ailn_rat",
xflt, "SPECIAL_stab_hdng",
xflt, "SPECIAL_elev_with_flap_rat",
xflt, "SPECIAL_ail1_pitch",
xflt, "SPECIAL_ail1_vmax",
xflt, "SPECIAL_ail2_pitch",
xflt, "SPECIAL_ail2_vmax",
xflt, "SPECIAL_ail1_flaps",
xflt, "SPECIAL_spo1_vmax",
xflt, "SPECIAL_ail2_flaps",
xflt, "SPECIAL_spo2_vmax",
xflt, "SPECIAL_tvec_ptch",
xflt, "SPECIAL_diff_thro_ptch",
xflt, "SPECIAL_tvec_roll",
xflt, "SPECIAL_diff_thro_roll",
xflt, "SPECIAL_tvec_hdng",
xflt, "SPECIAL_diff_thro_hdng",
xint, "SPECIAL_phase_ptch_tvect_in_at_90",
xint, "SPECIAL_phase_ptch_tvect_in_at_00",
xint, "SPECIAL_phase_roll_tvect_in_at_90",
xint, "SPECIAL_phase_roll_tvect_in_at_00",
xint, "SPECIAL_phase_hdng_tvect_in_at_90",
xint, "SPECIAL_phase_hdng_tvect_in_at_00",
xflt, "SPECIAL_flap1_roll",
xflt, "SPECIAL_flap1_ptch",
xint, "SPECIAL_sbrk_on_td_EQ",
xint, "SPECIAL_fbrk_on_td_EQ",
xint, "SPECIAL_revt_on_td_EQ",
xint, "SPECIAL_sweep_with_flaps_EQ",
xint, "SPECIAL_sweep_with_vect_EQ",
xint, "SPECIAL_flaps_with_gear_EQ",
xint, "SPECIAL_flaps_with_vec_EQ",
xint, "SPECIAL_slat_with_stall_EQ",
xint, "SPECIAL_auto_trim_EQ",
xint, "SPECIAL_anti_ice_EQ",
xint, "SPECIAL_arresting_EQ",
xint, "SPECIAL_warn_gear_EQ",
xint, "SPECIAL_warn_lorot_EQ",
xflt, "SPECIAL_chute_area",
xflt, "SPECIAL_chute_Y",
xflt, "SPECIAL_chute_Z",

xint, "ASTAB_lo_speed_is_position",
xflt, "ASTAB_ASlo_the_V",
xflt, "ASTAB_ASlo_psi_V",
xflt, "ASTAB_ASlo_phi_V",
xflt, "ASTAB_AShi_the_V",
xflt, "ASTAB_AShi_psi_V",
xflt, "ASTAB_AShi_phi_V",
xflt, "ASTAB_ASlo_max_thedot",
xflt, "ASTAB_ASlo_thedot_k",
xflt, "ASTAB_ASlo_max_psidot",
xflt, "ASTAB_ASlo_psidot_k",
xflt, "ASTAB_ASlo_max_phidot",
xflt, "ASTAB_ASlo_phidot_k",
xflt, "ASTAB_AShi_max_G",
xflt, "ASTAB_AShi_G_k",
xflt, "ASTAB_AShi_Gdot_k",
xflt, "ASTAB_AShi_max_alpha",
xflt, "ASTAB_AShi_alpha_k",
xflt, "ASTAB_AShi_alphadot_k",
xflt, "ASTAB_AShi_max_beta",
xflt, "ASTAB_AShi_beta_k",
xflt, "ASTAB_AShi_betadot_k",
xflt, "ASTAB_AShi_max_phidot",
xflt, "ASTAB_AShi_phidot_k",
xflt, "ASTAB_ASlo_max_the",
xflt, "ASTAB_ASlo_the_k",
xflt, "ASTAB_ASlo_max_phi",
xflt, "ASTAB_ASlo_phi_k",

xint, "OTTO_custom_autopilot",
xflt, "OTTO_ott_asi_ratio",
xflt, "OTTO_ott_asi_sec_into_future",
xflt, "OTTO_ott_asi_kts_off_for_full_def",
xflt, "OTTO_ott_phi_ratio",
xflt, "OTTO_ott_phi_sec_into_future",
xflt, "OTTO_ott_phi_deg_off_for_full_def",
xflt, "OTTO_ott_phi_sec_to_tune",
xflt, "OTTO_ott_def_sec_into_future",
xflt, "OTTO_ott_def_dot_off_for_full_def",
xflt, "OTTO_ott_def_sec_to_tune",
xflt, "OTTO_ott_the_ratio",
xflt, "OTTO_ott_the_sec_into_future",
xflt, "OTTO_ott_the_deg_off_for_full_def",
xflt, "OTTO_ott_the_sec_to_tune",
xflt, "OTTO_ott_the_deg_per_kt",

xflt, "AUTO_size_x",
xflt, "AUTO_size_z",
xflt, "AUTO_size_tot",
xflt, "AUTO_h_eqlbm",
xflt, "AUTO_the_eqlbm",
xflt, "AUTO_thro_x_ctr",
xflt, "AUTO_prop_x_ctr",
xflt, "AUTO_mixt_x_ctr",
xflt, "AUTO_heat_x_ctr",
xflt, "AUTO_cowl_x_ctr",
xflt, "AUTO_V_ref_ms",
xflt, "AUTO_average_mac_acf",
xflt, "AUTO_tire_s_contact",
xint, "AUTO_beacon_EQ",
xint, "AUTO_skid_EQ",
xint, "AUTO_gear_EQ",
xint, "AUTO_gear_steer_EN",
xint, "AUTO_generator_EQ",
xint, "AUTO_inverter_EQ",
xint, "AUTO_fuelpump_EQ",
xint, "AUTO_battery_EQ",
xint, "AUTO_avionics_EQ",
xint, "AUTO_auto_fea_EQ",
xint, "AUTO_has_hsi",
xint, "AUTO_has_radalt",
xint, "AUTO_has_radar",
xint, "AUTO_has_SC_fd",
xint, "AUTO_has_DC_fd",
xint, "AUTO_has_stallwarn",
xint, "AUTO_has_press_controls",
xint, "AUTO_has_igniter",
xint, "AUTO_has_idlespeed",
xint, "AUTO_has_FADEC_switch",
xint, "AUTO_has_clutch_switch",
xint, "AUTO_has_pre_rotate",
xint, "AUTO_has_mixture",
xint, "AUTO_has_kts_mac",
xint, "AUTO_has_asi_set",
xint, "AUTO_has_hdg_set",
xint, "AUTO_has_vvi_set",
xint, "AUTO_has_alt_set",
xint, "AUTO_has_litemap_tex_1",
xint, "AUTO_has_litemap_tex_2",

xint, "OVERFLOW_plot_OBJ7_cock_exact_fwd",
xint, "OVERFLOW_cockpit_M_out",
xint, "OVERFLOW_has_FMS",
xint, "OVERFLOW_has_APU_switch",
xflt, "OVERFLOW_SFC_max[8]",
xint, "OVERFLOW_hydraulic_eng",
xint, "OVERFLOW_hydraulic_eng_sel",
xchr, "OVERFLOW_ins_specs[300]",
xflt, "OVERFLOW_alta_x_ctr",
xint, "OVERFLOW_has_full_bleed_air",
xflt, "OVERFLOW_dump_altitude",
xflt, "SPECIAL_flap2_roll",
xflt, "SPECIAL_flap2_ptch",
xint, "OVERFLOW_flap1_ptch_above_50",
xint, "OVERFLOW_flap2_ptch_above_50",
xint, "OVERFLOW_flap1_roll_above_50",
xint, "OVERFLOW_flap2_roll_above_50",
xint, "SPECIAL_flap_with_stall_EQ",
xint, "OVERFLOW_has_ignition",
xint, "OVERFLOW_randys_magic_mushroom",
xflt, "OVERFLOW_gear_pumps",
xflt, "OVERFLOW_flap_pumps",
xint, "OVERFLOW_has_tail_lock",
xint, "OVERFLOW_start_on_water",
xflt, "OVERFLOW_rud1_rgt",
xflt, "OVERFLOW_rud2_rgt",
xint, "OVERFLOW_rgt_ruds_assigned",
xflt, "CONTROLS_elv2_up",
xflt, "CONTROLS_elv2_dn",
xflt, "CONTROLS_elv2_cratR",
xflt, "CONTROLS_elv2_cratT",
xflt, "OVERFLOW_cgZ_ref_ft",
xflt, "OVERFLOW_xflt_overflow[4887]",

xstruct, "engn[8]",
xstruct, "wing[56]",
xstruct, "part[95]",
xstruct, "gear[10]",
xstruct, "watt[24]",	# was after sbrk, but is actually here!
xstruct, "door[24]",	# doorstruct used for speeddbrakes and doors!
    ]

    engn8000 = [
xint, "engn_type",
xint, "prop_type",
xflt, "SFC_idle",
xflt, "prop_dir",
xint, "is_ducted",
xflt, "num_blades",
xint, "prop_clutch_EQ",
xflt, "prop_gear_rat",
xflt, "vert_init",
xflt, "side_init",
xflt, "min_pitch",
xflt, "max_pitch",
xflt, "des_rpm_prp",
xflt, "des_kts_prp",
xflt, "des_kts_acf",
xflt, "engn_mass",
xflt, "prop_mass",
xflt, "mi_prop_rpm",
xflt, "mi_engn_rpm",
xflt, "discarea",
xflt, "ringarea[10]",
xflt, "bladesweep[10]",
    ]
    engn810=engn8000

    wing8000 = [
xint, "is_left",
xflt, "lat_sign",
xint, "manual_mac",
xchr, "Rafl0[40]",
xchr, "Rafl1[40]",
xchr, "Tafl0[40]",
xchr, "Tafl1[40]",
xint, "els",
xflt, "Croot",
xflt, "Ctip",
xflt, "semilen_SEG",
xflt, "semilen_JND",	# semilen of the JOINED wing segments
xflt, "average_mac",
xflt, "element_len",
xflt, "chord_piv",
xflt, "dihed1",
xflt, "dihed2",
xflt, "dihednow",
xint, "vardihed",
xflt, "sweep1",
xflt, "sweep2",
xflt, "sweepnow",
xint, "varsweep",
xflt, "inc2",
xflt, "incnow",
xint, "varinc",
xflt, "e",
xflt, "AR",
xflt, "TR",
xflt, "al_D_al0",
xflt, "cl_D_cl0",
xflt, "cm_D_cm0",
xflt, "delta_fac",
xflt, "alpha_max",
xflt, "slat_effect",
xflt, "spec_wash",
xflt, "rev_con",	# was xchr in .h, but seems to be either xint or xflt
xflt, "el_s[10]",
xflt, "mac[10]",
xflt, "incidence[10]",
xint, "inc_ail1[10]",
xint, "inc_ail2[10]",
xint, "inc_elv1[10]",
xint, "inc_rud1[10]",
xint, "inc_rud2[10]",
xint, "inc_vect[10]",
xint, "inc_trim[10]",
xint, "ail1[10]",
xflt, "ail1_elR",
xflt, "ail1_elT",
xint, "ail2[10]",
xflt, "ail2_elR",
xflt, "ail2_elT",
xint, "spo1[10]",
xflt, "spo1_elR",
xflt, "spo1_elT",
xint, "spo2[10]",
xflt, "spo2_elR",
xflt, "spo2_elT",
xint, "yawb[10]",
xflt, "yawb_elR",
xflt, "yawb_elT",
xint, "elv1[10]",
xflt, "elv1_elR",
xflt, "elv1_elT",
xint, "rud1[10]",
xflt, "rud1_elR",
xflt, "rud1_elT",
xint, "rud2[10]",
xflt, "rud2_elR",
xflt, "rud2_elT",
xint, "fla1[10]",
xflt, "fla1_elR",
xflt, "fla1_elT",
xint, "fla2[10]",
xflt, "fla2_elR",
xflt, "fla2_elT",
xint, "slat[10]",
xint, "sbrk[10]",
xflt, "sbrk_elR",
xflt, "sbrk_elT",
xflt, "ca_xyz[20][3]",
xflt, "co_xyz[20][3]",
    ]
    wing810=list(wing8000)
    wing810.extend([
xint, "inc_elv2[10]",
xint, "elv2[10]",
xflt, "elv2_elR",
xflt, "elv2_elT",
xflt, "overflow_dat[100]",
    ])

    part8000 = [
xint, "part_eq",
xflt, "part_x",
xflt, "part_psi",
xflt, "aero_x_os",
xflt, "area_frnt",
xint, "patt_prt",
xflt, "part_y",
xflt, "part_the",
xflt, "aero_y_os",
xflt, "area_side",
xint, "patt_con",
xflt, "part_z",
xflt, "part_phi",
xflt, "aero_z_os",
xflt, "area_nrml",
xflt, "patt_rat",
xflt, "cd",
xflt, "scon",
xflt, "damp",
xint, "part_tex",
xflt, "top_s1",
xflt, "bot_s1",
xflt, "top_t1",
xflt, "bot_t1",
xflt, "top_s2",
xflt, "bot_s2",
xflt, "top_t2",
xflt, "bot_t2",
xflt, "part_r",
xint, "s_dim",
xint, "r_dim",
xflt, "geo_xyz[20][18][3]",
xflt, "nrm_xyz[20][18][3]",
xflt, "st[20][18][2]",
xchr, "locked[20][18]",
    ]
    part800=part8000
    part810=part8000

    gear8000=[
xint, "gear_type",
xint, "steers",
xflt, "scon",
xflt, "damp",
xflt, "leg_len",
xflt, "cyc_time",
xflt, "dep_rat",
xflt, "stat_def",	# the gear TIRE LOCATION IS OFFSET DOWN BY THIS MUCH IN X-PLANE since people ALWAYS enter gear location UNDER STATIC DEFLECTION!
xflt, "strut_comp",
xflt, "tire_radius",
xflt, "tire_swidth",
xflt, "tire_mi",
xflt, "gear_x",
xflt, "latE",	# extended
xflt, "lonE",
xflt, "axiE",
xflt, "x_nodef",
xflt, "gear_y",
xflt, "latR",	# retracted
xflt, "lonR",
xflt, "axiR",
xflt, "y_nodef",
xflt, "gear_z",
xflt, "latN",	# now
xflt, "lonN",
xflt, "axiN",
xflt, "z_nodef",
    ]
    gear810=gear8000

    watt8000=[
xchr, "watt_name[40]",
xint, "watt_prt",
xint, "watt_con",
xflt, "watt_x",
xflt, "watt_psi",
xflt, "watt_y",
xflt, "watt_the",
xflt, "watt_z",
xflt, "watt_phi",
    ]
    watt810=watt8000

    door8000=[
xint, "type",
xflt, "area",
xflt, "xyz[3]",
xflt, "geo[4][4][3]",	# the doors are 4x4, to allow curvature and stuff in 3D
xflt, "nrm[4][4][3]",	# i dont use these yet
xflt, "axi_rot",
xflt, "inn_s1",
xflt, "out_s1",
xflt, "ext_ang",
xflt, "inn_t1",
xflt, "out_t1",
xflt, "ret_ang",
xflt, "inn_s2",
xflt, "out_s2",
xflt, "ang_now",
xflt, "inn_t2",
xflt, "out_t2",
    ]
    door810=door8000

    # Derived from WPN740.def by Stanislaw Pusep
    #   http://sysd.org/xplane/acftools/WPN740.def
    # and from X-Plane v7 docs
    #   ./Instructions/Manual_Files/X-Plane ACF_format.html
    wpn740=[
#xchr, "HEADER_platform",
#xint, "HEADER_version",
xint, "type",
xint, "free_flyer",
xint, "action_mode",
xflt, "x_wpn_att",
xflt, "y_wpn_att",
xflt, "z_wpn_att",
xflt, "cgY",
xflt, "cgZ",
xflt, "las_range",
xflt, "conv_range",
xflt, "bul_rounds_per_sec",
xflt, "bul_rounds",
xflt, "bul_muzzle_speed",
xflt, "bul_area",
xflt, "added_mass",
xflt, "total_weapon_mass_max",
xflt, "fuel_warhead_mass_max",
xint, "warhead_type",
xflt, "mis_drag_co",
xflt, "mis_drag_chute_S",
xflt, "mis_fin_z[4]",
xflt, "mis_fin_cr[4]",
xflt, "mis_fin_ct[4]",
xflt, "mis_fin_semilen[4]",
xflt, "mis_fin_sweep[4]",
xflt, "mis_fin_conrat[4]",
xflt, "mis_fin_steer[4]",
xflt, "mis_fin_dihed[4][2]",
xchr, "mis_afl[4][40]",
xflt, "mis_thrust[3]",
xflt, "mis_duration[3]",
xflt, "mis_cone_width",
xflt, "mis_crat_per_deg_bore",
xflt, "mis_crat_per_degpersec_bore",
xflt, "mis_crat_per_degpersec",
xflt, "gun_del_psi_deg_max",
xflt, "gun_del_the_deg_max",
xflt, "gun_del_psi_deg_now",
xflt, "gun_del_the_deg_now",
xflt, "s_frn",
xflt, "s_sid",
xflt, "s_top",
xflt, "X_body_aero",
xflt, "Y_body_aero",
xflt, "Z_body_aero",
xflt, "Jxx_unitmass",
xflt, "Jyy_unitmass",
xflt, "Jzz_unitmass",
xint, "i",
xint, "j",
xint, "target_index",
xflt, "targ_lat",
xflt, "targ_lon",
xflt, "targ_h",
xflt, "del_psi",
xflt, "del_the",
xflt, "rudd_rat",
xflt, "elev_rat",
xflt, "V_msc",
xflt, "AV_msc",
xflt, "dist_targ",
xflt, "dist_point",
xflt, "time_point",
xflt, "sin_the",
xflt, "cos_the",
xflt, "sin_psi",
xflt, "cos_psi",
xflt, "sin_phi",
xflt, "cos_phi",
xflt, "fx_axis",
xflt, "fy_axis",
xflt, "fz_axis",
xflt, "vx",
xflt, "vy",
xflt, "vz",
xflt, "x",
xflt, "y",
xflt, "z",
xflt, "L",
xflt, "M",
xflt, "N",
xflt, "Prad",
xflt, "Qrad",
xflt, "Rrad",
xflt, "q[4]",
xflt, "the",
xflt, "psi",
xflt, "phi",
xflt, "next_bull_time",
xflt, "total_weapon_mass_now",
xflt, "fuel_warhead_mass_now",
xflt, "impact_time",
xflt, "xflt_overflow[973]",
xint, "xint_overflow[1000]",
xchr, "xchr_overflow[1000]",
xflt, "body_radius",
xflt, "PARTS_body_X[20][18]",
xflt, "PARTS_body_Y[20][18]",
xflt, "PARTS_body_Z[20][18]",
    ]

    #------------------------------------------------------------------------
    # Derived from hl_acf_structs.h
    wpn800=[
#xchr, "HEADER_platform",
#xint, "HEADER_version",
xint, "type",
xint, "free_flyer",
xint, "action_mode",
xflt, "impact_time",
xflt, "next_bull_time",
xflt, "cgY",
xflt, "cgZ",
xflt, "las_rangexflt",
xflt, "conv_range",
xflt, "bul_rounds_per_sec",
xflt, "bul_rounds",
xflt, "bul_muzzle_speed",
xflt, "bul_area",
xint, "warhead_type",
xflt, "added_mass",
xflt, "total_weapon_mass_max",
xflt, "fuel_warhead_mass_max",
xflt, "total_weapon_mass_now",
xflt, "fuel_warhead_mass_now",
xflt, "mis_drag_chute_S",
xflt, "mis_fin_z[4]",
xflt, "mis_fin_cr[4]",
xflt, "mis_fin_ct[4]",
xflt, "mis_fin_semilen[4]",
xflt, "mis_fin_sweep[4]",
xflt, "mis_fin_conrat[4]",
xflt, "mis_fin_steer[4]",
xflt, "mis_fin_dihed[4][2]",
xchr, "mis_afl[4][40]",
xflt, "mis_thrust[3]",
xflt, "mis_duration[3]",
xflt, "mis_cone_width",
xflt, "mis_crat_per_deg_bore",
xflt, "mis_crat_per_degpersec_bore",
xflt, "mis_crat_per_degpersec",
xflt, "gun_del_psi_deg_max",
xflt, "gun_del_the_deg_max",
xflt, "psi_con",
xflt, "the_con",
xflt, "phi_con",
xflt, "psi_acf",
xflt, "the_acf",
xflt, "phi_acf",
xflt, "psi_wrl",
xflt, "the_wrl",
xflt, "phi_wrl",
xflt, "s_frn",
xflt, "s_sid",
xflt, "s_top",
xflt, "Jxx_unitmass",
xflt, "Jyy_unitmass",
xflt, "Jzz_unitmass",
xint, "target_index",
xflt, "targ_lat",
xflt, "targ_lon",
xflt, "targ_h",
xflt, "del_psi",
xflt, "del_the ",
xflt, "rudd_rat",
xflt, "elev_rat",
xflt, "V_msc",
xflt, "AV_msc",
xflt, "dist_targ",
xflt, "dist_point",
xflt, "time_point",
xflt, "sin_the",
xflt, "cos_the",
xflt, "sin_psi",
xflt, "cos_psi",
xflt, "sin_phi",
xflt, "cos_phi",
xflt, "fx_axis",
xflt, "fy_axis",
xflt, "fz_axis",
xflt, "vx",
xflt, "vy",
xflt, "vz",
xflt, "x",
xflt, "y",
xflt, "z",
xflt, "L",
xflt, "M",
xflt, "N",
xflt, "Prad",
xflt, "Qrad",
xflt, "Rrad",
xflt, "q[4]",
xflt, "chute_vector_wrl[3]",

xstruct, "part",

xflt, "xflt_overflow[100]",
    ]


    #------------------------------------------------------------------------
    # slurp the acf file
    def __init__(self, filename, debug,
                 defs=None, fmt=None, prefix='', prg=True):

        # Reading sub-structure?
        if defs:
            self.parse(filename, debug, defs, fmt, prefix, prg)
            return

        acffile=open(filename, "rb")
        if debug>1:
            dmp=open(filename[:filename.rindex('.')]+'.txt', 'wt')
            #dmp=open(filename+'.txt', 'wt')
        else:
            dmp=None

        # HEADER_platform
        self.HEADER_platform=acffile.read(1)
        if self.HEADER_platform=='a':
            fmt='>'
        elif self.HEADER_platform=='i':
            fmt='<'
        else:
            acffile.close()
            raise(ParseError)
        if dmp:
            dmp.write("%6x:\tHEADER_platform:\t%s\n" %(0,self.HEADER_platform))

        # HEADER_version
        (self.HEADER_version,)=unpack(fmt+'i', acffile.read(4))
        if self.HEADER_version in [700,740]:
            defs=DEFfile.acf740
        elif self.HEADER_version in [8000,810]:
            defs=DEFfile.acf810
        elif self.HEADER_version==1:
            defs=DEFfile.wpn740
        elif self.HEADER_version==800:
            defs=DEFfile.wpn800
        else:
            acffile.close()
            raise(ParseError)
        if dmp:
            dmp.write("%6x:\tHEADER_version:\t%s\n" % (1,self.HEADER_version))

        self.parse(acffile, dmp, defs, fmt, prefix, prg)
        if dmp: dmp.close()
        acffile.close()

        if self.HEADER_version>=800:
            return

        # weapon
        if self.HEADER_version==1:
            self.part=(v7wpn(self))
            return

        # Rewrite selected v7 acf variables to v8 format
        
        # engines
        self.engn=[]
        for n in range(DEFfile.engnDIM):
            self.engn.append(v7engn(self, n))

        # wings
        self.wing=[]
        for n in range(DEFfile.wingDIM):
            if DEFfile.v7parts.has_key(n):
                (v7, s_dim, r_dim, tex,
                 top_s1, bot_s1, top_t1, bot_t1,
                 top_s2, bot_s2, top_t2, bot_t2)=DEFfile.v7parts[n]
                self.wing.append(v7wing(self, v7))
            else:
                self.wing.append(v7wing(None))
        
        # parts
        self.part=[]
        for n in range(DEFfile.partDIM):
            if DEFfile.v7parts.has_key(n):
                (v7, s_dim, r_dim, tex,
                 top_s1, bot_s1, top_t1, bot_t1,
                 top_s2, bot_s2, top_t2, bot_t2)=DEFfile.v7parts[n]
                self.part.append(v7part(self, v7, s_dim, r_dim, tex,
                                        top_s1, bot_s1, top_t1, bot_t1,
                                        top_s2, bot_s2, top_t2, bot_t2))
            else:
                self.part.append(v7part(None))

        # gear
        self.gear=[]
        for n in range(67,73):
            self.gear.append(v7gear(self, n))
        for n in range(4):
            self.gear.append(v7gear(None))
            			#wheel,    tread
        self.GEAR_wheel_tire_s1=[ 1/1024.0,  1/1024.0]
        self.GEAR_wheel_tire_t1=[      0.0, 50/1024.0]
        self.GEAR_wheel_tire_s2=[15/1024.0, 15/1024.0]
        self.GEAR_wheel_tire_t2=[50/1024.0, 79/1024.0]
        
        # weapons
        self.watt=[]
        for n in range(DEFfile.wattDIM):
            self.watt.append(v7watt(self, n))

        # doors
        self.door=[]
        for n in range(10):
            self.door.append(v7door(self, n))
        for n in range(10,DEFfile.doorDIM):
            self.door.append(v7door(None))

        # misc
        self.WB_tank_xyz=[]
        for i in range(3):
            self.WB_tank_xyz.append([self.WB_tank_X[i],
                                     self.WB_tank_Y[i],
                                     self.WB_tank_Z[i]])


    def data(self, acffile, dmp, number, size, t, fmt, var):
        v=[]
        for i in range(number):
            if t==DEFfile.xstruct:
                x=DEFfile(acffile, dmp,
                          eval("DEFfile.%s%s" % (var, self.HEADER_version)),
                          fmt, "%s[%s]." % (var, i), 0)
            else:
                ifmt=fmt+'i'
                ffmt=fmt+'f'
                c=acffile.read(size)
                if t==DEFfile.xchr:
                    if size==1:
                        if not c:
                            x=0
                        elif "0123456789".find(c)!=-1:
                            x=int(c)
                        else:
                            x=0
                    elif c.find("\0")!=-1:
                        x=c[:c.index("\0")]	# trim nulls
                    else:
                        x=c
                elif t==DEFfile.xint:
                    (x,)=unpack(ifmt, c)
                elif t==DEFfile.xflt:
                    (x,)=unpack(ffmt, c)
                    #x=round(x,1+Vertex.ROUND)
                else:
                    acffile.close()
                    raise(ParseError)

            if number==1:
                return x
            v.append(x)
        return v


    def parse(self, acffile, dmp, defs, fmt, prefix, prg):
        n=len(defs)
        for i in range(0,n,2):
            if prg:
                Window.DrawProgressBar(i/(float(n*2)), "Reading data ...")
            off=acffile.tell()
            t=defs[i]	# Data type
            
            size=4	# ints and floats
            k=defs[i+1].split("[")
            var=k.pop(0)
            for j in range(len(k)):
                k[j]=int(k[j][:-1])
            if t==DEFfile.xchr:
                if len(k)>0:
                    size=k.pop()
                else:
                    size=1

            v=[]
            if len(k)>0:
                number=k.pop()
                if len(k)>0:
                    for o in range(k[0]):
                        if len(k)>1:
                            assert(len(k)==2)
                            vo=[]
                            for p in range(k[1]):
                                vo.append(self.data(acffile, dmp, number,
                                                    size, t, fmt, var))
                            v.append(vo)
                        else:    
                            v.append(self.data(acffile, dmp, number,
                                               size, t, fmt, var))
                else:
                    v=self.data(acffile, dmp, number, size, t, fmt, var)
            else:
                v=self.data(acffile, dmp, 1, size, t, fmt, var)

            if dmp and t!=DEFfile.xstruct:
                dmp.write("%6x:\t%s%s:\t%s\n" % (off, prefix, var, v))
            exec("self.%s=v" % var)
        
        
#------------------------------------------------------------------------
class v7engn:
    def __init__(self, acf, v7):
        self.engn_type=acf.PROP_engn_type[v7]
        self.num_blades=acf.PROP_num_blades[v7]
        self.vert_init=acf.PROP_vert_cant_init[v7]
        self.side_init=acf.PROP_side_cant_init[v7]
        self.prop_dir=acf.PROP_prop_dir[v7]

class v7wing:
    def __init__(self, acf, v7=0):
        if not acf:
            self.semilen_SEG=0.0
            return
        self.is_left=acf.OVERFLOW_is_left[v7]
        self.lat_sign=acf.OVERFLOW_lat_sign[v7]
        self.Rafl0=acf.PARTS_Rafl0[v7]
        self.Rafl1=acf.PARTS_Rafl1[v7]
        self.Tafl0=acf.PARTS_Tafl0[v7]
        self.Tafl1=acf.PARTS_Tafl1[v7]
        self.els=acf.PARTS_els[v7]
        self.Croot=acf.PARTS_Croot[v7]
        self.Ctip=acf.PARTS_Ctip[v7]
        self.semilen_SEG=acf.PARTS_semilen_SEG[v7]
        self.semilen_JND=acf.PARTS_semilen_JND[v7]
        self.dihed1=acf.PARTS_dihed1[v7]
        self.sweep1=acf.PARTS_sweep1[v7]

class v7part:
    def __init__(self, acf, v7=0, s_dim=0, r_dim=0, tex=0,
                 top_s1=0, bot_s1=0, top_t1=0, bot_t1=0,
                 top_s2=0, bot_s2=0, top_t2=0, bot_t2=0):
        if not acf:
            self.part_eq=0
            return
        self.s_dim=s_dim
        self.r_dim=r_dim
        self.top_s1=top_s1/1024.0
        self.bot_s1=bot_s1/1024.0
        self.top_t1=top_t1/1024.0
        self.bot_t1=bot_t1/1024.0
        self.top_s2=top_s2/1024.0
        self.bot_s2=bot_s2/1024.0
        self.top_t2=top_t2/1024.0
        self.bot_t2=bot_t2/1024.0
        self.patt_con=0
        self.part_tex=tex
        self.part_eq=acf.PARTS_part_eq[v7]
        self.part_x=acf.PARTS_Xarm[v7]
        self.part_y=acf.PARTS_Yarm[v7]
        self.part_z=acf.PARTS_Zarm[v7]
        self.part_psi=acf.OVERFLOW_heading[v7]
        self.part_phi=acf.OVERFLOW_roll[v7]
        self.part_the=acf.OVERFLOW_pitch[v7]
        if s_dim and r_dim:
            self.geo_xyz=[]
            for s in range(DEFfile.body_sDIM):
                v=[]
                for r in range(DEFfile.body_rDIM):
                    v.append([acf.PARTS_body_X[v7][s][r],
                              acf.PARTS_body_Y[v7][s][r],
                              acf.PARTS_body_Z[v7][s][r]])
                self.geo_xyz.append(v)

class v7gear:
    def __init__(self, acf, v7=0):
        if not acf:
            self.gear_type=0
            return
        self.gear_type=acf.PARTS_gear_type[v7]
        self.gear_x=acf.PARTS_Xarm[v7]
        self.gear_y=acf.PARTS_Yarm[v7]
        self.gear_z=acf.PARTS_Zarm[v7]
        self.latE=acf.PARTS_gear_latE[v7]
        self.lonE=acf.PARTS_gear_lonE[v7]
        self.tire_radius=acf.PARTS_tire_radius[v7]
        self.tire_swidth=acf.PARTS_tire_swidth[v7]
        self.leg_len=acf.PARTS_gear_leglen[v7]

class v7watt:
    def __init__(self, acf, v7):
        self.watt_name=acf.WEARONS_wpn_name[v7]
        self.watt_con=0
        self.watt_x=acf.WEARONS_x_wpn_att[v7]
        self.watt_y=acf.WEARONS_y_wpn_att[v7]
        self.watt_z=acf.WEARONS_z_wpn_att[v7]
        self.watt_psi=acf.WEAPONS_psi_wpn_att[v7]
        self.watt_the=acf.WEAPONS_the_wpn_att[v7]
        self.watt_phi=acf.WEAPONS_roll_wpn_att[v7]

class v7wpn:
    def __init__(self, acf):
        if not acf:
            self.part_eq=0
            return
        self.s_dim=DEFfile.body_sDIM
        self.r_dim=DEFfile.body_rDIM
        self.top_s1=0
        self.bot_s1=0
        self.top_t1=0.5
        self.bot_t1=0.0
        self.top_s2=0.508
        self.bot_s2=0.508
        self.top_t2=1.0
        self.bot_t2=0.5
        self.part_eq=1
        self.part_x=acf.x_wpn_att
        self.part_y=acf.y_wpn_att
        self.part_z=acf.z_wpn_att
        self.geo_xyz=[]
        for s in range(DEFfile.body_sDIM):
            v=[]
            for r in range(DEFfile.body_rDIM):
                v.append([acf.PARTS_body_X[s][r],
                          acf.PARTS_body_Y[s][r],
                          acf.PARTS_body_Z[s][r]])
            self.geo_xyz.append(v)

class v7door:
    def __init__(self, acf, v7=None):
        if not acf:
            self.type=DEFfile.gear_door_none
            return
        self.type=acf.GEAR_gear_door_typ[v7]
        self.xyz=[acf.GEAR_gear_door_loc[v7][0],
                  acf.GEAR_gear_door_loc[v7][1],
                  acf.GEAR_gear_door_loc[v7][2]]
        self.axi_rot=acf.GEAR_gear_door_axi_rot[v7]
        self.ext_ang=acf.GEAR_gear_door_ext_ang[v7]
        self.inn_s1=0.0
        self.out_s1=0.0
        self.inn_t1=0.3837890625
        self.out_t1=0.3837890625
        self.inn_s2=0.015625
        self.out_s2=0.015625
        self.inn_t2=0.5078125
        self.out_t2=0.5078125
        self.geo=[[acf.GEAR_gear_door_geo[v7][0],None,None,
                   acf.GEAR_gear_door_geo[v7][1]],
                  None, None,
                  [acf.GEAR_gear_door_geo[v7][3],None,None,
                   acf.GEAR_gear_door_geo[v7][2]]]


#------------------------------------------------------------------------
def file_callback (filename):
    print "Starting ACF import from " + filename
    Window.DrawProgressBar(0, "Opening ...")
    try:
        obj=ACFimport(filename)
    except ParseError:
        Window.DrawProgressBar(1, "Error")
        print("ERROR: This isn't a v7 or v8 X-Plane file!")
        Blender.Draw.PupMenu("ERROR: This isn't a v7 or v8 X-Plane file!")
        return
    obj.doImport()
    Window.DrawProgressBar(1, "Finished")
    print "Finished\n"
    Blender.Redraw()


#------------------------------------------------------------------------
# main routine
#------------------------------------------------------------------------

Blender.Window.FileSelector(file_callback,"IMPORT .ACF")

