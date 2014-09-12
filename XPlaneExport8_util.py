#
# Copyright (c) 2005-2013 Jonathan Harris
#
# This code is licensed under version 2 of the GNU General Public License.
# http://www.gnu.org/licenses/gpl-2.0.html
#
# See ReadMe-XPlane2Blender.html for usage.
#

#
# X-Plane renders polygons in scenery files mostly in the order that it finds
# them - it detects use of alpha and deletes wholly transparent polys, but
# doesn't sort by Z-buffer order.
#
# So we have to sort on export to ensure alpha comes after non-alpha. We also
# sort to minimise attribute state changes, in rough order of expense:
#  - Hard - should be first. Renderer merges hard polys with similar non-hard.
#  - TWOSIDE
#  - Materials
#  - Animations
#  - PANEL - most expensive, put as late as we can
#  - ALPHA - must be last for correctness. Renderer will merge with previous.
#  - NPOLY - negative so polygon offsets come first. Assumed to be on ground
#            so no ordering issues, so can be higher priority than ALPHA.
#  - Lines and lights
#  - Group
#  - Layer
#


import sys
from math import cos, radians
import Blender
from Blender import Armature, Mesh, Lamp, Image, Draw, Window
from Blender.Mathutils import Matrix, RotationMatrix, TranslationMatrix, MatMultVec, Vector, Quaternion, Euler, TriangleNormal
from XPlaneUtils import *
from XPlaneExport import *
from XPlaneExport8_ManipOptionsInterpreter import decode
#import time

datarefs={}
(datarefs,foo)=getDatarefs()

# Default X-Plane (not Blender) material (ambient & specular do jack)
DEFMAT=((1,1,1), (0,0,0), 0)	# diffuse, emission, shiny

#----------------------------------------------------------------------------------------------------------------
# VERTEX DATA TYPES
#----------------------------------------------------------------------------------------------------------------
# These data types store informantion about a single vertex in the model, and typically convert to the string
# representation for an OBJ.
#
# VT: textured vertex, for triangles
# VLINE: colored vertex, for lines
# VLIGHT: RGB light (that is, an old legacy light)
# NLIGHT: a named light
# CLIGHT: a custom light with a dataref and all params
# SMOKE: a smoke puff generator
#
class VT:
    def __init__(self, v, n, uv):
        self.v=v	# Vertex location
        self.n=n	# Vertex normal
        self.uv=uv	# Vertex UV tex coords

    def __str__ (self):
        return "%s\t%6.3f %6.3f %6.3f\t%s" % (self.v, self.n.x, self.n.y,
                                              self.n.z, self.uv)

    def equals (self, b, fudge=Vertex.LIMIT):
        return (self.v.equals(b.v, fudge) and
                self.n.equals(b.n, fudge) and
                self.uv.equals(b.uv))

class VLINE:
    def __init__(self, v, c):
        self.v=v	# Vertex location
        self.c=c	# Vertex color

    def __str__ (self):
        return "%s\t%6.3f %6.3f %6.3f" % (self.v,
                                          round(self.c[0],2),
                                          round(self.c[1],2),
                                          round(self.c[2],2))
    def equals (self, b):
        return (self.v.equals(b.v) and self.c==b.c)

class VLIGHT:
    def __init__(self, v, c):
        self.v=v        # Light location
        self.c=c        # Vertex color

    def __str__ (self):
        return "%s\t%6.3f %6.3f %6.3f" % (self.v,
                                          round(self.c[0],2),
                                          round(self.c[1],2),
                                          round(self.c[2],2))

    def equals (self, b):
        return (self.v.equals(b.v) and self.c==b.c)

class NLIGHT:
    def __init__(self, v, n, p):
        self.v=v    # Light Location
        self.n=n    # Light Name
        self.p=p    # Light Parameters

    def __str__ (self):
        if len(self.p) > 0:
            slash=self.p.find('/')
            if slash == -1:
                return "LIGHT_PARAM\t%s\t%s%s %s" % (self.n, '\t'*(2-len(self.n)/8), self.v, self.p)
            else:
                return "LIGHT_CUSTOM\t%s%s %s" % ('\t'*(2-len(self.n)/8), self.v, self.p)
        else:
            return "LIGHT_NAMED\t%s\t%s%s" % (self.n, '\t'*(2-len(self.n)/8), self.v)

    def equals (self, b):
        return (isinstance(b,NLIGHT) and self.v.equals(b.v) and self.p==b.p and self.n==b.n)

# Custom Spill light
class SLIGHT:
    def __init__(self, v, rgba, s, d, semi, dataref):
        self.v=v    # Light Location
        self.rgba=rgba      # Light Color
        self.s=s        # Cone length
        self.d=d	# Cone direction vector
        self.semi=semi	# cos(Cone angle)
        self.dataref=dataref    # DataRef or None

    def __str__ (self):
        return "LIGHT_SPILL_CUSTOM\t%s\t%.3f %.3f %.3f %.3f %.3f\t%s\t%.3f %s" % (self.v, self.rgba[0], self.rgba[1], self.rgba[2], self.rgba[3], self.s, self.d, self.semi, self.dataref or 'no_ref')

    def equals (self, b):
        return (isinstance(b,SLIGHT) and self.v.equals(b.v) and self.rgba==b.rgba and self.s==b.s and self.d.equals(b.d) and self.semi==b.semi and self.dataref==b.dataref)

class CLIGHT:
    def __init__(self, v, rgba, s, uv1, uv2, d):
        self.v=v        # Light Location
        self.rgba=rgba      # Light Default Color
        self.s=s        # Light Size
        self.uv1=uv1    # Light UV mapping pairs
        self.uv2=uv2
        self.d=d        # Light DAtaref

    def __str__ (self):
        return "LIGHT_CUSTOM\t%s\t%6.3f %6.3f %6.3f %6.3f %9.4f\t%s %s\t%s" % (self.v, self.rgba[0], self.rgba[1], self.rgba[2], self.rgba[3], self.s, self.uv1, self.uv2, self.d)

    def equals (self, b):
        return (isinstance(b,CLIGHT) and self.v.equals(b.v) and self.n==b.n)

class SMOKE:
    def __init__(self, v, n, p):
        self.v=v    # Smoke Puff Location
        self.n=n    # Puff name (obj cmd name for puff: smoke_black or smoke_white)
        self.p=p    # Puff Size

    def __str__ (self):
        return "%s\t%s\t%4.2f" % (self.n, self.v, self.p)

    def equals (self, b):
        return (isinstance(b,SMOKE) and self.v.equals(b.v) and self.n==b.n and self.p==b.p)

#----------------------------------------------------------------------------------------------------------------
# STATE SORTED PRIMITIVE
#----------------------------------------------------------------------------------------------------------------
# The prim class is the heart of the obj exporter.  It holds a single "primitive" (that is, one triange/quad,
# line, light, smoke puff, etc. as well as all of the state information that is being applied to it.
#
# 'Style' is an enum that tells us what kind of primtive we have: a tri, line, vlight (indexed RGB lights) or
# named light.
#
# Note: all point-based primitives that are not indexed (named lights, custom lights, smoke puffs) use the
# nlight style, since they are all equivalent: an XYZ location and some more stuff that can be output as a string.
# Since we may end up with new lights (940 has parameterized lights) it's useful to have it be light-weight to
# introduce new lights.
#
# The "index" field (i) contains differing values depending on what we are.
# - points and lines: the prim contains an array of indices within the master vertex table.  E.g. if we might
#   have 50, 51 for a line.  There are two master vertex tables - for points and lines, so the numbering scheme is
#   type specific.  NOTE: if the prim is a quad in blender, we will have six indices for the two tris that it can
#   be decomposed into.
# - for nlight and vlight styles, we will have in index a ptr to another object, referenced directly, e.g.
#   nlight, vlight, etc.
#
# Each primitive contains "offset" and "count" - that is the span of its indices in the master index table.  When
# a primitive is "indexed" we remember these, so that we can easily identify and consolidate "runs" of tris.  Since
# we index and output primitives in the same order, we tend to get large index runs.
#
# For tris and lines, offset/count is as expected.  For vlight, offset is the index number of the vlight among all
# vlights, and count is always 1.  This does have the effect of producing a lot of LIGHTS statements without
# consolidation.  To fix this, we should consolidate "LIGHTS" stages later, not muck around inside this class.
#
# STATE SORTING
#
# Each state attribute sits inside this class.  Primitives can be compared (See below).  The exporter pulls out
# all primitives for the scene and sorts them by state.  When they are output, this produces the minimal set of
# state transitions possible.
#
# Animation index: each primitive has its animation obj attached, but for the purpose of export, it is most
# efficient to take animation in Dept First Search (DFS) order, so that nested animations don't require re-stating
# the parent animation.  Since the exporter finds animations in this order naturally, we simply record per
# primitive the index number of the animation we attached within the master animation list on the exporter.  This
# way we can simply sort by index number (without having to call "index" on our parent clsas) to rapidly get our
# animations organized.
#
# WARNING: this technique assumes that lights and lines have state - technically this is not really true...lights
# and lines can appear anywhere in the OBJ.  So this implementation will put some unnecessary state changes in front
# of lines/lights to assure a "normal" state going into the lights/lines.  This is actually a good thing.  X-Plane
# has historically had tons of bugs with state change and non-tri primitives...for older x-plane this prevents bugs.
# For newer X-Plane (late v9 versions) the OBJ optimizer inside x-plane handles out-of-state primitives correctly
# and probably discards every unnecessary "padded" attribute, producing the true minimal state change needed to
# draw a light.  So this design doesn't harm a new x-plane and probably fixes old bugs.  Note that in 940 a change
# to a light is a full shader + texture change, plus a bunch of other scary things..that is, it is actually quite
# expensive.  So having the exporter output primitive changes as requiring state change (change of style, and maybe
# change of current attributes) is a pretty accurate representation of what really happens.  (E.g. if you have poly_os
# on and you draw  light, x-plane _does_ turn poly_os off temporarily, then turn it back on again!)
#
class Prim:
    # Flags in sort order - lower indices are tweaked more often
    # This group breaks up a batch but does not touch the GPU - they are therefore not _that_ expensive to process and
    # we would prefer to vary them at high frequency...
    HARD=1          # hard, deck and shadow actually don't cause a GPU state change....they just interrupt issuing of tris.
    DECK=2			# So they are significantly cheaper than other stuff.
    NSHADOW=4		# Disable shadow
    DRAW_DISABLE=8	# ATTR_draw_disable for hit-test-only meshes.
    SOLID_CAMERA=16	# ATTR_solid_camera for camera constraint.

    # Starting with this group, we have to change the GPU state, wihch gets expensive.  So we really try to keep this group together!
    TWOSIDE=32		# GPU state change
    PANEL=64        # Should be 2nd last (panel shader change is _not_ cheap!!!)
                    # Blending changes are last since they must be in alpha order.
    # These are in order to get Z/alpha sort right, so non-negotiably important!
    NPOLY=128		# NPOLY = NOT poly-offset.  Since the lower value of the flag sorts out first, we tag "not-poly-os."
    DRAPED=256		# Okay to have it "out of order" - draped is actually not part of the OBJ at all!  But keep "draped" by itself.

    #Alpha modes...
    OPAQUE=0	# Underlying geometry is opaque, so we can use _any_ alpha mode - in theory, we can avoid state change by merging this with neighbors.
    TEST=1      # Test but don't blend - cutoff controlled by "blend cut" in tuple.   Good for trees!
    SHADOWTEST=2# Test for shadows, blend for drawing, cutoff used for shadows, back-to-front sorting to avoid Z halo in non-shadow render.
    BLEND=3     # True blending, no cutoff used.  This means we need back-to-front sorting to avoid Z halo.

    SURFACES=[None, 'water', 'concrete', 'asphalt', 'grass', 'dirt', 'gravel', 'lakebed', 'snow', 'shoulder', 'blastpad']
    STYLE=['Tri','Line','VLight','NLight']

    # surface comes here
    BUCKET1=HARD|DECK|NSHADOW|TWOSIDE		# Why the bit flags?  So we can filter out and compare parts of the status.  High-flag fields are more expensive.
    # material comes here
    # anim comes here
    BUCKET2=PANEL|NPOLY|DRAPED
    # lines and lights drawn here
    LINES  =PANEL|NPOLY		# These are the flags we use for lines/lights.
    LIGHTS =PANEL|NPOLY
    # group comes here
    # layer comes here

    def __init__ (self, object, group, flags, surface, mat, img, anim, aidx,style):
        self.i=[]		# indices for lines & tris, VLIGHT/NLIGHT for lights within master geometry table
        self.geo=[]		# cache of 3 vectors, our normal, our plane eq 'D', and our centroid for this tri.
        self.offset=-1	# range of our indices within the master index table for tris and lines
        self.count=-1
        self.style=style
        self.anim=anim
        self.anim_idx=aidx
        self.flags=flags	# bitmask
        self.alpha=[Prim.OPAQUE,0.0]
        self.region=-1	# image, -1 for no region
        self.surface=surface	# tris: one of Prim.SURFACES
        self.mat=mat		# tris: (diffuse, emission, shiny)
        self.group=group
        self.layer=object.Layer	# This is the set of layers we belong to.
        self.layer_now=-1		# This is the one layer we pay attention to now for sorting or state update.
        self.image=img
        self.lit_level=None
        self.draw_disable=0
        self.solid_camera=0
        self.debug_name = object.name
        self.manip=""

    def cache(self, vt_list):
        if self.style=='Tri':
            v1 = vt_list[self.i[0]]
            v2 = vt_list[self.i[1]]
            v3 = vt_list[self.i[2]]
            vv1 = Vector(v1.v.x,v1.v.y,v1.v.z)
            vv2 = Vector(v2.v.x,v2.v.y,v2.v.z)
            vv3 = Vector(v3.v.x,v3.v.y,v3.v.z)
            n = TriangleNormal(vv1,vv2,vv3)
            self.geo.append(vv1)
            self.geo.append(vv2)
            self.geo.append(vv3)
            self.geo.append(n)
            self.geo.append(-n.dot(vv1))
            self.geo.append((vv1 + vv2 + vv3) / 3.0)

    #----------------------------------------------------------------------------------------------------------------
    # STATE PRIORITIZATION
    #----------------------------------------------------------------------------------------------------------------
    # This tiny piece of code has a huge impact on objects - this is the prioritized list of how we organize state
    # change.  Basically the earlier on the list the state type, the LESS we will change that state.  So for example
    # LOD is first on the list because we can't change LOD, then change back - we must sort to have each LOD on its own.
    # By comparison, hard surface type is at the bottom because it turns out this is a very cheap attribute.  You
    # can read this as saying: the exporter wil sort first by LOD, then by surface.  Thus the surface may be changed many
    # times as it must be reset inside each LOD.
    #
    # So: to see other optimizations, simpyl change the order of this loop.  A few interesting notes:
    # - Primitive type of line/light (self.style) is state, so we can force consoldiation by primitive type.  This might
    #   pay off in some cases - testing is needed!
    # - Animation (by index) is state, so we can choose to prioritize other change over animation.  The exporter will
    #   put the animation in twice to minimize other state change.

    def __cmp__ (self,other):
        if self.layer_now != other.layer_now:				# LOD - highest prio, must be on outside
            return cmp(self.layer_now,other.layer_now)
        elif self.group != other.group:				# respect groups, then
            return cmp_grp(self.group,other.group)
        elif self.lit_level != other.lit_level:
            return cmp(self.lit_level,other.lit_level)
        elif (self.alpha != other.alpha):
            return cmp(self.alpha,other.alpha)
        elif (self.flags&Prim.BUCKET2) != (other.flags&Prim.BUCKET2):
            return cmp((self.flags&Prim.BUCKET2),(other.flags&Prim.BUCKET2))
        elif self.anim_idx != other.anim_idx:				# don't dupe animation...well except for panels.
            return cmp(self.anim_idx,other.anim_idx)
        elif self.mat != other.mat:
            return cmp_mat(self.mat,other.mat)
        elif (self.flags&Prim.BUCKET1) != (other.flags&Prim.BUCKET1):
            return cmp((self.flags&Prim.BUCKET1),(other.flags&Prim.BUCKET1))
        elif self.region != other.region:				# cockpit tex and materials mean shader change, as do some of the flags
            return cmp(self.region,other.region)
        elif self.style != other.style:
            return cmp(self.style,other.style)
        elif self.image != other.image:
            return cmp(self.image,other.image)
        elif self.manip != other.manip:
            return cmp(self.manip,other.manip)
        elif self.surface != other.surface:
            return cmp(self.surface,other.surface)
        elif self.style == 'Tri':
            if self.alpha[0] > Prim.    TEST:
                #print self.i, other.i
                r = order_tris(self.geo,other.geo)    # back to front order
                #if r == -1:
                #    print self.i, other.i
                #elif r == 1:
                #    print other.i, self.i
                #else:
                #    print "tie"
                return r
            else:
                return order_tris(other.geo,self.geo)    # front to back - if opaque, this reduces fill rate!
        else:
            return 0

def cmp_mat(a, b):
    if a == DEFMAT:
        return -1
    elif b == DEFMAT:
        return 1
    else:
        return cmp(a,b)

def cmp_grp(a, b):
    if a == None:
        return -1
    elif b == None:
        return 1
    else:
        return cmp(a.name, b.name)

def order_tris__(a, b):
    print a
    print b

    a0=cmp(b[3].dot(a[0])+b[4],0)
    a1=cmp(b[3].dot(a[1])+b[4],0)
    a2=cmp(b[3].dot(a[2])+b[4],0)
    b0=cmp(a[3].dot(b[0])+a[4],0)
    b1=cmp(a[3].dot(b[1])+a[4],0)
    b2=cmp(a[3].dot(b[2])+a[4],0)
    print a0, a1, a2, b0, b1, b2
    a_pos = a0 > 0 or a1 > 0 or a2 > 0
    a_neg = a0 < 0 or a1 < 0 or a2 < 0
    b_pos = b0 > 0 or b1 > 0 or b2 > 0
    b_neg = b0 < 0 or b1 < 0 or b2 < 0
    a_split = a_pos and a_neg
    b_split = b_pos and b_neg
    aa = a0 + a1 + a2
    bb = b0 + b1 + b2
    print aa, bb, a_split, b_split
    if a_split and b_split:
        print "dual split!!"
        return 0
    if a_split: return 1
    if b_split: return -1
    if aa < 0 and bb < 0:
        print "toplogical ambig"
        return 0
    if a_neg: return 1
    if b_neg: return -1

    return 0

def order_tris(a, b):
    a0=cmp(b[3].dot(a[0])+b[4],0)
    a1=cmp(b[3].dot(a[1])+b[4],0)
    a2=cmp(b[3].dot(a[2])+b[4],0)
    b0=cmp(a[3].dot(b[0])+a[4],0)
    b1=cmp(a[3].dot(b[1])+a[4],0)
    b2=cmp(a[3].dot(b[2])+a[4],0)
    a=a0+a1+a2
    b=b0+b1+b2
    if a == -3:		return 1
    elif a == 3:	return -1
    if b == -3:		return -1
    elif b == 3:	return 1

    if a == -2:		return 1
    elif a == 2:	return -1
    if b == -2:		return -1
    elif b == 2:	return 1

    else:			return 0

def safe_image_for_face(m,f):
    if not m.faceUV:
        return None
    if (f.mode &Mesh.FaceModes.TEX) != 0:
        return f.image
    else:
        return None

#------------------------------------------------------------------------
#-- OBJexport --
#------------------------------------------------------------------------
class OBJexport8:

    #------------------------------------------------------------------------
    def __init__(self, filename):
        #--- public you can change these ---
        self.verbose=0	# level of verbosity in console 0-none, 1-some, 2-most
        self.debug=0	# extra debug info in console
        self.local_export=0
        self.use_mat=1

        #--- class private don't touch ---
        self.file=None
        self.filename=filename
        self.prefix=''
        self.iscockpit=(filename.lower().endswith("_cockpit.obj") or
                        filename.lower().endswith("_cockpit_inn.obj") or
                        filename.lower().endswith("_cockpit_out.obj"))
        self.ispanelok=self.iscockpit	# Flag to allow ATTR_cockpit - allowed in ACF-attached objs in v10
        self.layermask=1
        self.texture=None
        self.regions={}		# (x,y,width,height) by image
        self.drawgroup=None
        self.slung=0
        self.linewidth=0.101
        self.nprim=0		# Number of X-Plane primitives exported
        self.log=[]
        self.v9=False		# Used v9 features
        self.v10=False		# Used v10 features
        self.additive_lod=0
        self.instanced=0
        self.global_alpha=[Prim.BLEND,0.0]
        self.global_nshadow=False
        #
        # Attribute tracking variables.  This is the last state that we wrote into the OBJ file.
        # UpdateAttr compares these to what it needs and writes only the changes.
        #
        self.hardness=0
        self.surface=None
        self.lit_level=None
        self.mat=DEFMAT
        self.twoside=False
        self.npoly=True
        self.panel=False
        self.region=-1
        self.alpha=self.global_alpha
        self.nshadow=self.global_nshadow
        self.layer=0
        self.group=None
        self.lod=None		# list of lod limits
        self.anim=Anim(self, None)
        self.manip=""
        self.image=None
        #
        # Index list tracking.  When we accumulate triangles or lines, we simply track what range
        # we have written here.  When we write more, we simply extend the region (if the regions are
        # contiguous.  This lets us consolidate 25000 tris into one TRIS.  -1,-1 is used to indicate
        # that we don't have an "open" list.
        self.tri_offset=-1
        self.tri_count=-1
        self.tri_ins=""
        self.line_offset=-1
        self.line_count=-1
        self.line_ins=""

        #
        # Global vertex lists
        #
        self.vt=[]
        self.vline=[]
        self.vlights=[]							# Actual vlight objs get put here as well as inside the prim, because they are indexed.
        self.prims=[]							# Master primitive lists

        #
        # Global list of all known animations, materials, groups.  We need groups because we have to search top-down to find objs.
        # We need animations to convert anim to index for sorting.  Ben say: I think we do NOT need a global material list anymore.
        #
        self.anims=[Anim(self, None)]
#       self.mats=[DEFMAT]	# list of (diffuse, emission, shiny)
        if Blender.Get('version')>=242:	# new in 2.42
            self.groups=Blender.Group.Get()
            self.groups.sort(lambda x,y: cmp(x.name.lower(), y.name.lower()))
        else:
            self.groups=[]

        #
        # When we have a mesh on an armiture, it might be that the same mesh is used multiple times.  This lets us
        # look for duplicates and reuse them.
        #
        self.animcands=[]	# indices into tris of candidates for reuse

    #------------------------------------------------------------------------
    def openFile(self, objects, outer_empty, prefix):
        print 'Starting OBJ export to ' + self.filename
        self.prefix=prefix
        self.file = open(self.filename, 'w')
        self.texture=getTexture(self,objects,False,8)
        self.texture_draped=getTexture(self,objects,False,8,True)
        print "starting %d objects." % len(objects)

        mp = outer_empty
        print "master parent is %s" % mp.name
        mtv = mp.getMatrix('worldspace')
        itv = Matrix()
        itv.identity()
        if itv != mtv:
            print "We need local origin for bulk export."
            self.local_export=1

    def export(self, scene):
        theObjects = scene.objects

        print 'Starting OBJ export to ' + self.filename
        if not checkFile(self.filename):
            return

        Window.WaitCursor(1)
        Window.DrawProgressBar(0, 'Examining textures')
        print 'search for main tex'
        self.texture=getTexture(self,theObjects,False,8)
        print 'search for draped tex'
        self.texture_draped=getTexture(self,theObjects,False,8,True)

        #clock=time.clock()	# Processor time
        frame=Blender.Get('curframe')

        self.file = open(self.filename, 'w')
        self.writeHeader ()
        self.writeObjects (theObjects)
        checkLayers (self, theObjects)
        if self.v10:
            print 'Warn:\tThis object requires X-Plane v10'
            self.log.append(('This object requires X-Plane v10', None))
        elif self.regions or self.v9:
            print 'Warn:\tThis object requires X-Plane v9'
            self.log.append(('This object requires X-Plane v9', None))

        Blender.Set('curframe', frame)
        #scene.update(1)
        #scene.makeCurrent()	# see Blender bug #4696
        Window.DrawProgressBar(1, 'Finished')
        Window.WaitCursor(0)
        #print "%s CPU time" % (time.clock()-clock)
        print "Finished - exported %s primitives\n" % self.nprim
        if self.log:
            r=Draw.PupMenu(("Exported %s primitives%%t|" % self.nprim)+'|'.join([a[0] for a in self.log]))
            if r>0: raise ExportError(None, self.log[r-1][1])
        else:
            Draw.PupMenu("Exported %s primitives%%t|OK" % self.nprim)

    #------------------------------------------------------------------------
    def writeHeader (self):
        if 'blender.app' in Blender.sys.progname:
            systype='A'
        else:
            systype='I'
        self.file.write("%s\n800\nOBJ\n\n" % systype)
        if self.texture:
            self.file.write("TEXTURE\t\t%s%s\n" % (self.prefix,self.texture))
            core = get_core_texture(self.texture)
            if tex_exists(core+"_NML.png"): self.file.write("TEXTURE_NORMAL\t%s%s_NML.png\nGLOBAL_specular\t1.0\n" % (self.prefix,core))
            elif tex_exists(core+"_NML.dds"): self.file.write("TEXTURE_NORMAL\t%s%s_NML.dds\nGLOBAL_specular\t1.0\n" % (self.prefix,core))
            if tex_exists(core+"_LIT.png"): self.file.write("TEXTURE_LIT\t%s%s_LIT.png\n" % (self.prefix,core))
            elif tex_exists(core+"_LIT.dds"): self.file.write("TEXTURE_LIT\t%s%s_LIT.dds\n" % (self.prefix,core))

        else:	# X-Plane barfs if no texture specified
            self.file.write("TEXTURE\t\n")
        if self.texture_draped:
            self.file.write("TEXTURE_DRAPED\t\t%s%s\n" % (self.prefix,self.texture_draped))
            core = get_core_texture(self.texture_draped)
            if tex_exists(core+"_NML.png"): self.file.write("TEXTURE_DRAPED_NORMAL\t%s%s_NML.png\n" % (self.prefix,core))
            elif tex_exists(core+"_NML.dds"): self.file.write("TEXTURE_DRAPED_NORMAL\t%s%s_NML.dds\n" % (self.prefix,core))
        for img in self.regions.keys():
            (n,x,y,width,height)=self.regions[img]
            self.file.write("COCKPIT_REGION\t%4d %4d %4d %4d\n" % (x,y,x+width,y+height))

        # if we have a cockpit, ALWAYS write GLOBAL_cockpit_lit.
        # v9: it is ignored
        # v10 with regions: this allows alpha, 99.9% of the time this won't harm anything.
        # v10 without regions: this gets correct lighting - without correct lighting, v10 planes look like ASS.
        if self.ispanelok:
            self.file.write("GLOBAL_cockpit_lit\n")


    #------------------------------------------------------------------------
    def writeAttr (self, str):
        if self.instanced:
            raise ExportError("You have requested instanced export of the object %s, but this object contains a non-instancable attribute:|%s" % (self.filename, str))
        else:
            self.file.write(str)

    #------------------------------------------------------------------------
    #------------------------------------------------------------------------
    # MASTER OUTPUT FUNCTION
    #------------------------------------------------------------------------
    #------------------------------------------------------------------------
    def writeObjects (self, theObjects):

        #------------------------------------------------------------------------
        # GLOBAL PROPERTY SUCK_UP
        #------------------------------------------------------------------------
        # STEP 0 - go find any global properties floating around and write them out.
        global_prop_list = [ 'GLOBAL_no_blend', 'GLOBAL_specular', 'SLOPE_LIMIT', 'TILTED', 'GLOBAL_shadow_blend', 'ATTR_LOD_draped', 'GLOBAL_tint', 'ATTR_layer_group', 'ATTR_layer_group_draped', 'REQUIRE_WET', 'REQUIRE_DRY' ];
        for a in global_prop_list:
            src_o=find_prop_list(theObjects, a)
            if src_o != None:
                if a == 'GLOBAL_no_blend':
                    self.global_alpha = [Prim.TEST, round(float(get_prop(src_o, a, 0.5)),2)];
                elif a == 'GLOBAL_shadow_blend':
                    self.global_alpha = [Prim.SHADOWTEST, round(float(get_prop(src_o, a, 0.5)),2)];
                #elif a == 'GLOBAL_no_shadow':
                #    self.global_nshadow=True
                else:
                    self.file.write("%s %s\n" % (a,get_prop(src_o, a, 'XXX')))

        a_obj=find_prop_list(theObjects, 'additive_lod')
        if a_obj != None:
            self.additive_lod=int(get_prop(a_obj,'additive_lod',self.additive_lod))

        a_obj=find_prop_list(theObjects, 'instanced')
        if a_obj != None:
            self.instanced=int(get_prop(a_obj,'instanced',self.additive_lod))

        if self.layermask==1:
            lseq=[1]
        else:
            lseq=[1,2,4]

        # Speed optimisation
        if self.iscockpit:
            surfaces=[None]
        else:
            surfaces=Prim.SURFACES
        regionimages=[None]+self.regions.keys()
        h=PanelRegionHandler()

        #------------------------------------------------------------------------
        # SCENE EXPLORATION
        #------------------------------------------------------------------------
        # Step 1 - we go through all of the blender objects we are exporting and
        # "sort" them - that is, dump their individual primitives (faces, lines,
        # etc) into the master primitive bucket.  When we are done, everything
        # we care about is in our export obj somewhere.

        # Build global vertex lists
        nobj=len(theObjects)
        for o in range (nobj-1,-1,-1):
            object=theObjects[o]
            if not object.Layer&self.layermask or h.isHandlerObj(object):
                continue
            Window.DrawProgressBar(float(nobj-o)*0.4/nobj,
                                   "Exporting %d%% ..." % ((nobj-o)*40/nobj))
            objType=object.getType()
            if objType == 'Mesh':
                if isLine(object, self.linewidth):
                    self.sortLine(object)
                elif isLight(object):
                    self.sortLamp(object)
                else:
                    self.sortMesh(object)
            #elif objType in ['Curve','Surf']:
            #    self.sortMesh(object)
            elif objType=='Lamp':
                self.sortLamp(object)
            elif objType=='Armature':
                pass    # dealt with separately
            elif objType == 'Empty':
                for prop in object.getAllProperties():
                    if prop.type in ['INT', 'FLOAT'] and prop.name.strip().startswith('group_'):
                        self.drawgroup=(prop.name.strip()[6:], int(prop.data))
                        if not self.drawgroup[0] in ['terrain', 'beaches', 'shoulders', 'taxiways', 'runways', 'markings', 'airports', 'footprints', 'roads', 'objects', 'light_objects', 'cars']:
                            raise ExportError('Invalid drawing group "%s" in "%s"' % (self.drawgroup[0], object.name), [object])
                    elif prop.type in ['INT', 'FLOAT'] and prop.name.strip()=='slung_load_weight':
                        self.slung=prop.data
            #elif objType not in ['Camera','Lattice']:
            #    print 'Warn:\tIgnoring %s "%s"' % (objType.lower(),object.name)
            #    self.log.append(('Ignoring %s "%s"' % (objType.lower(), object.name),[object]))

        #------------------------------------------------------------------------
        # STATE SORT
        #------------------------------------------------------------------------
        # First set layer_now to something sane.  The lowest included bit
        # would be best, but for now just grouping all layer 1 memberships as
        # "just 1" is good enough to get the critical effect: not reordering
        # layer 1 items by their other-layer membership.
        for p in self.prims:
            p.cache(self.vt)
            if p.layer & 1:
                p.layer_now = 1
            else:
                p.layer_now = p.layer

        # This is what munges the OBJ order.  Prims contains everything we want
        # to output, tagged with state.  Now we will have it in the order we want
        # to write the file.
        self.prims.sort()

        # Post-sort opacity optimization: when a face is officially "opaque" the author
        # is declaring that they don't _care_ what alpha we use, because the face doesn't
        # intersect the alpha part of the UV map.  So we can do fun stuff like front-to-back
        # ordering, etc.  Buuuut...in the case where we have an opaque section followed by an
        # alpha-test section, naively the exporter would output a "default" (e.g. blended) mesh
        # for opaque (sicne opaque doesn't actively change the blending mode) followed by an
        # ATTR_no_blend.
        #
        # We can do slightly better though by applying the attr_no_blend to BOTH the opaque
        # and the blended part - the opaque part is "don't care" anyway, so there's no harm and
        # what we've done is to effectively consolidate batches.

        first_interesting_alpha=None
        first_interesting_alpha_name=""
        for p in self.prims:
            if p.alpha[0] != Prim.OPAQUE and (p.flags & Prim.DRAPED) == 0:
                first_interesting_alpha = p.alpha
                first_interesting_alpha_name = p.debug_name
                break
        if first_interesting_alpha != None:
            cur_alpha=first_interesting_alpha
            for p in self.prims:
                if (p.flags & Prim.DRAPED) == 0:
                    if p.alpha[0] == Prim.OPAQUE:
                        p.alpha = cur_alpha
                    else:
                        cur_alpha = p.alpha
                        if cur_alpha != first_interesting_alpha:
                            if self.instanced:
                                 raise ExportError("Object %s:|You have requested instancing but you are using multiple blending modes.|There is a conflict between %s and %s." % (self.filename, first_interesting_alpha_name, p.debug_name))
            if self.instanced:
                if self.global_alpha != first_interesting_alpha and self.global_alpha[0] != Prim.BLEND:
                    raise ExportError("Object %s:|The alpha specified by your buttons do not match your global blending attributes."% self.filename)
                # if we wanted to warn about ununsed global attributes for blending we'd do it here!
                self.global_alpha = first_interesting_alpha

        if self.instanced:
            for p in self.prims:
                if p.style == 'Tri':
                    if (p.flags & Prim.DRAPED) == 0:
                        if p.flags & Prim.NSHADOW:
                            self.global_nshadow=True
                            break

        if self.global_alpha[0] == Prim.TEST:
            self.file.write("GLOBAL_no_blend %.2f\n" % self.global_alpha[1])
        elif self.global_alpha[0] == Prim.SHADOWTEST:
            self.file.write("GLOBAL_shadow_blend %.2f\n" % self.global_alpha[1])
        if self.global_nshadow:
            self.file.write("GLOBAL_no_shadow\n")

        #------------------------------------------------------------------------
        # BUILD INDICES
        #------------------------------------------------------------------------
        # Now we will go throguh all of the primitives and build the master index
        # list.  The primitives already have their vertex reservations (E.g. the
        # number of "VT", etc.  We must do at least two pases over the geometry
        # to get lines after lights. (Q: does x-plane really care?)  We could
        # do lights with lines for more speed.

        indices=[]
        progress=0.0
        for tri in self.prims:
            if tri.style=='Tri':
                tri.offset=len(indices)
                indices.append(tri.i[0])
                indices.append(tri.i[1])
                indices.append(tri.i[2])
                if len(tri.i)==4:    # quad
                    indices.append(tri.i[0])
                    indices.append(tri.i[2])
                    indices.append(tri.i[3])
                tri.count=len(indices)-tri.offset
        for line in self.prims:
            if line.style=='Line':
                line.offset=len(indices)
                indices.append(line.i[0])
                indices.append(line.i[1])
                line.count=len(indices)-line.offset

        # Lights
        for light in self.prims:
            if light.style=='VLight':
                light.offset=len(self.vlights)
                self.vlights.append(light)
                light.count=1

        #------------------------------------------------------------------------
        # WRITE OUT ALL HEADERS, INDEX TABLES, AND OTHER META DATA
        #------------------------------------------------------------------------
        self.nprim=len(self.vt)+len(self.vline)+len(self.vlights)
        self.file.write("POINT_COUNTS\t%d %d %d %d\n\n" % (len(self.vt),
                                                           len(self.vline),
                                                           len(self.vlights),
                                                           len(indices)))
        Window.DrawProgressBar(0.8, 'Exporting 80% ...')
        for vt in self.vt:
            self.file.write("VT\t%s\n" % vt)
        if self.vt:
            self.file.write("\n")

        for vline in self.vline:
            self.file.write("VLINE\t%s\n" % vline)
        if self.vline:
            self.file.write("\n")

        for light in self.vlights:
            self.file.write("VLIGHT\t%s\n" % light.i)
        if self.vlights:
            self.file.write("\n")

        Window.DrawProgressBar(0.9, 'Exporting 90% ...')
        n=len(indices)
        for i in range(0, n-9, 10):
            self.file.write("IDX10\t"+' '.join([str(j) for j in indices[i:i+10]])+"\n")
        for i in range(n-(n%10), n):
            self.file.write("IDX\t%d\n" % indices[i])

        if self.slung:
            self.file.write("\nslung_load_weight\t%s\n" % self.slung)
        if self.drawgroup:
            self.file.write("\nATTR_layer_group\t%s\t%d\n" % (
                self.drawgroup[0], self.drawgroup[1]))

        #------------------------------------------------------------------------
        # WRITE OUT COMMAND TABLE
        #------------------------------------------------------------------------
        # The command table is written by writing out each primitive.  We update
        # ATTRs between each one to sync state.  99% of the time, that means no
        # state change because we sorted.
        #
        # We must treat each style in a single loop or else we will be implicitly
        # pulling out all the lines from tris, etc. which will mean LODs
        # get duplicated (which is illegal!)

        for l in lseq:
            for prim in self.prims:
                if prim.layer & l:
                    if l > 1 and self.additive_lod == 0:
                        prim.flags = prim.flags & ~(Prim.HARD|Prim.DECK)
                    prim.layer_now = l                  # Update layer_now to the layer we "focus" on now, so update_attr knows what we are doing.
                    if prim.style=='Tri':
                        self.updateAttr(prim)
                        self.accum_tri(prim.anim.ins(),prim.offset,prim.count)
                    elif prim.style=='Line':
                        self.updateAttr(prim)
                        self.accum_line(prim.anim.ins(),prim.offset,prim.count)
                    elif prim.style=='VLight':
                        self.updateAttr(prim)
                        self.file.write("%sLIGHTS\t%d %d\n" %
                                         (prim.anim.ins(),prim.offset,prim.count))
                    elif prim.style=='NLight':
                        self.updateAttr(prim)
                        self.file.write("%s%s\n" %
                                            (prim.anim.ins(), prim.i))

        # Close triangles in the final layer
        self.flush_prim()
        # Close animations in final layer
        while not self.anim.equals(Anim(self, None)):
            self.anim=self.anim.anim
            self.file.write("%sANIM_end\n" % self.anim.ins())
        self.file.close()

#        if not n==len(offsets)==len(counts):
#           raise ExportError('Bug - indices out of sync')

    #------------------------------------------------------------------------
    # SORTING LAMPS
    #------------------------------------------------------------------------
    def sortLamp(self, object):

        (anim, mm, aidx)=self.makeAnim(object)

        if object.getType()=='Mesh':
            # This is actually a custom light - material has HALO set
            mesh=object.getData(mesh=True)
            mats=mesh.materials
            material=mats[0]    # may not have any faces - assume 1st material
            rgba=[material.R, material.G, material.B, material.alpha]
            mtex=material.getTextures()[0]
            if mtex:
                uv1=UV(mtex.tex.crop[0], mtex.tex.crop[1])
                uv2=UV(mtex.tex.crop[2], mtex.tex.crop[3])
            else:
                uv1=UV(0,0)
                uv2=UV(1,1)

            # get RGBA and name properties
            dataref='NULL'
            for prop in object.getAllProperties():
                if prop.name in ['R','G','B','A']:
                    if prop.type in ['INT', 'FLOAT']:
                        rgba[['R','G','B','A'].index(prop.name)]=float(prop.data)
                    else:
                        raise ExportError('Unsupported data type for property "%s" in custom light "%s"' % (prop.name, object.name), [object])
                elif prop.name=='name':
                    if prop.type!='STRING': raise ExportError('Unsupported data type for dataref in custom light "%s"' % object.name, [object])
                    ref=prop.data.strip()
                    if ref in datarefs and datarefs[ref]:
                        (path, n)=datarefs[ref]
                        dataref=path
                        if n!=9: raise ExportError('Dataref %s can\'t be used for custom lights' % dataref, [object])
                    else:
                        dataref=getcustomdataref(object, object, 'custom light', [ref])

            for v in mesh.verts:
                light=Prim(object, self.findgroup(object), Prim.LIGHTS, False, DEFMAT, None, anim, aidx,'NLight')
                light.i=CLIGHT(Vertex(v.co[0], v.co[1], v.co[2], mm),
                               rgba, material.haloSize,
                               uv1, uv2, dataref)
                self.prims.append(light)
            return

        light=Prim(object, self.findgroup(object), Prim.LIGHTS, False, DEFMAT, None, anim, aidx,'VLight')

        lamp=object.getData()
        name=object.name
        special=0

        if lamp.getType() != Lamp.Types.Lamp and lamp.getType() != Lamp.Types.Spot:
            print 'Info:\tIgnoring Area, Sun or Hemi lamp "%s"' % name
            self.log.append(('Ignoring Area, Sun or Hemi lamp "%s"' % name, [object]))
            return

        if self.verbose:
            print 'Info:\tExporting Light "%s"' % name

        if '.' in name: name=name[:name.index('.')]
        lname=name.lower().split()
        c=[0,0,0]
        if lamp.getType() == Lamp.Types.Spot:	# custom spill
            dataref = None
            for prop in object.getAllProperties():
                if prop.name.lower()=='dataref': dataref=str(prop.data).strip()
            light.i=SLIGHT(Vertex(0,0,0, mm), [lamp.R, lamp.G, lamp.B, lamp.energy/10], lamp.dist, Vertex(0,0,-1, MatrixrotationOnly(mm, object)), cos(radians(lamp.spotSize)), dataref)
            light.style='NLight'
            self.prims.append(light)
            self.v10=True
            return
        elif 'pulse' in lname:
            c[0]=c[1]=c[2]=9.9
            special=1
        elif 'strobe' in lname:
            c[0]=c[1]=c[2]=9.8
            special=1
        elif 'traffic' in lname:
            c[0]=c[1]=c[2]=9.7
            special=1
        elif 'flash' in lname:
            c[0]=-lamp.col[0]
            c[1]=-lamp.col[1]
            c[2]=-lamp.col[2]
        elif 'lamp' in lname:
            c[0]=lamp.col[0]
            c[1]=lamp.col[1]
            c[2]=lamp.col[2]
        elif name in ['smoke_black', 'smoke_white']:
            light.i=SMOKE(Vertex(0,0,0, mm), name, lamp.energy)
            light.style='NLight'
            self.prims.append(light)
            return
        else:    # named light
            params=''
            for prop in object.getAllProperties():
                if prop.name.lower()=='name': name=str(prop.data).strip()
                if prop.name.lower()=='params': params=str(prop.data).strip()
            light.i=NLIGHT(Vertex(0,0,0, mm), name,params)
            light.style='NLight'
            self.prims.append(light)
            return

        light.i=VLIGHT(Vertex(0,0,0, mm), c)
        self.prims.append(light)


    #------------------------------------------------------------------------
    # SORTING LINES
    #------------------------------------------------------------------------
    def sortLine(self, object):
        if self.verbose:
            print 'Info:\tExporting Line "%s"' % object.name

        (anim, mm, aidx)=self.makeAnim(object)
        line=Prim(object, self.findgroup(object), Prim.LINES, False, DEFMAT, None, anim, aidx,'Line')

        mesh=object.getData()
        face=mesh.faces[0]

        v=[]
        for i in range(4):
            v.append(Vertex(face.v[i][0],face.v[i][1],face.v[i][2], mm))
        if (v[0].equals(v[1],self.linewidth) and
            v[2].equals(v[3],self.linewidth)):
            i=0
        else:
            i=1
        v1=Vertex((v[i].x+v[i+1].x)/2,
                  (v[i].y+v[i+1].y)/2,
                  (v[i].z+v[i+1].z)/2)
        v2=Vertex((v[i+2].x+v[(i+3)%4].x)/2,
                  (v[i+2].y+v[(i+3)%4].y)/2,
                  (v[i+2].z+v[(i+3)%4].z)/2)

        if len(mesh.materials)>face.mat and mesh.materials[face.mat]:
            c=[mesh.materials[face.mat].R,
               mesh.materials[face.mat].G,
               mesh.materials[face.mat].B,]
        else:
            c=[0.5,0.5,0.5]

        for v in [v1,v2]:
            vline=VLINE(v, c)

            for j in range(len(self.vline)):
                q=self.vline[j]
                if vline.equals(q):
                    line.i.append(j)
                    break
            else:
                j=len(self.vline)
                self.vline.append(vline)
                line.i.append(j)

        self.prims.append(line)


    #------------------------------------------------------------------------
    # SORTING MESHES
    #------------------------------------------------------------------------
    def sortMesh(self, object):

        mesh=object.getData(mesh=True)
        mats=mesh.materials

        if object.getType()!='Mesh' or object.modifiers:
            # use dummy mesh with modifiers applied instead
            mesh=Mesh.New()
            mesh.getFromObject(object)

        (anim, mm, aidx)=self.makeAnim(object)
        hasanim=not anim.equals(Anim(self, None))
        nm=MatrixrotationOnly(mm, object)
        # Vertex order, taking into account negative scaling
        if object.SizeX*object.SizeY*object.SizeZ<0:
            seq=[[],[],[],[0,1,2],[0,1,2,3]]
        else:
            seq=[[],[],[],[2,1,0],[3,2,1,0]]

        if self.verbose:
            print 'Info:\tExporting Mesh "%s"' % object.name

        if self.debug:
            print 'Mesh "%s" %s faces' % (object.name, len(mesh.faces))

        group=self.findgroup(object)
        hardness=Prim.HARD
        surface=None
        lit_level=None
        up_nrm=False
        draw_disable=False
        solid_camera=False

        if has_prop(object,'lit_level'):
            lit_level=get_prop(object,'lit_level','').strip()
        if has_prop(object,'ATTR_light_level'):
            lit_level=get_prop(object,'ATTR_light_level','').strip()
            if len(lit_level.split()) == 1:
                v1 = get_prop(object,'ATTR_light_level_v1','0.0')
                v2 = get_prop(object,'ATTR_light_level_v2','1.0')
                lit_level=v1+' '+v2+' '+lit_level

        if has_prop(object,'ATTR_draw_disable'):
            draw_disable=True

        if has_prop(object,'ATTR_solid_camera'):
            if not self.iscockpit:
                raise ExportError('ATTR_solid_camera is illegal in a non-cockpit object: "%s"' % (object.name),[object])
            solid_camera=True

        if not self.iscockpit:
            if has_prop(object,'surface'):
                surface=get_prop(object,'surface','').strip().lower()
                if not surface in Prim.SURFACES:
                    raise ExportError('Invalid surface "%s" for face in mesh "%s"' % (surface, object.name), [object])
            if has_prop(object,'deck') and int(get_prop(object,'deck','0')):
                hardness=Prim.DECK
        if has_prop(object,'up_norm') and int(get_prop(object,'up_norm','0')):
            up_nrm=True


        # Optimisation: Children of animations might be dupes. This test only
        # looks for exact duplicates, but this can reduce vertex count by ~10%.
        twosideerr=[]
        harderr=[]
        degenerr=[]
        mode=Mesh.FaceModes.DYNAMIC
        if hasanim:
            animcands=list(self.animcands)    # List of candidate tris
            trino=0
            fudge=Vertex.LIMIT*10        # Be more lenient
            for f in mesh.faces:
                if mesh.faceUV: mode=f.mode
                n=len(f.v)
                if not n in [3,4]:
                    pass
                elif not (mode & Mesh.FaceModes.INVISIBLE):
                    for i in seq[n]:
                        nmv=f.verts[i]
                        vertex=Vertex(nmv.co[0], nmv.co[1], nmv.co[2], mm)
                        if up_nrm:
                            norm=Vertex(0,0,1,mm)
                        elif not f.smooth:
                            norm=Vertex(f.no, nm)
                        else:
                            norm=Vertex(nmv.no, nm)
                        if mode & Mesh.FaceModes.TEX:
                            uv=UV(f.uv[i][0], f.uv[i][1])
                        else:    # File format requires something - using (0,0)
                            uv=UV(0,0)
                        vt=VT(vertex, norm, uv)

                        j=0
                        while j<len(animcands):
                            if not vt.equals(self.vt[self.prims[animcands[j]+trino].i[seq[n][i]]], fudge):
                                animcands.pop(j)    # no longer a candidate
                            else:
                                j=j+1

                    if not len(animcands):
                        break    # exhausted candidates
                    trino+=1
            else:
                # Success - re-use tris starting at self.vt[animcands[0]]
                trino=0
                for f in mesh.faces:
                    if mesh.faceUV: mode=f.mode
                    n=len(f.v)
                    if not n in [3,4]:
                        degenerr.append(f)
                    elif not (mode & Mesh.FaceModes.INVISIBLE):
                        if f.mat<len(mats) and mats[f.mat]:
                            material=mats[f.mat]
                            # diffuse, emission, shiny
                            mat=((material.R, material.G, material.B),
                                 (material.mirR*material.emit,
                                  material.mirG*material.emit,
                                  material.mirB*material.emit), material.spec)
#                            if not mat in self.mats: self.mats.append(mat)
                        else:
                            mat=DEFMAT
                        face=Prim(object, group, 0, None, mat, safe_image_for_face(mesh,f), anim, aidx,'Tri')
                        face.manip = decode(object)

                        if mode & Mesh.FaceModes.TEX:
                            if len(f.uv)!=n:
                                raise ExportError('Missing UV in mesh "%s"' % object.name, [object])
                            if f.transp == Mesh.FaceTranspModes.ALPHA:
                                if has_prop(object,'ATTR_shadow_blend'):
                                    face.alpha=[Prim.SHADOWTEST,round(float(get_prop(object,'ATTR_shadow_blend',0.5)),2)]
                                elif has_prop(object,'GLOBAL_shadow_blend'):
                                    face.alpha=[Prim.SHADOWTEST,round(float(get_prop(object,'GLOBAL_shadow_blend',0.5)),2)]
                                else:
                                    face.alpha=[Prim.BLEND,0.0]
                            if f.transp == Mesh.FaceTranspModes.CLIP:
                                if has_prop(object,'ATTR_no_blend'):
                                    face.alpha=[Prim.TEST,round(float(get_prop(object,'ATTR_no_blend',0.5)),2)]
                                elif has_prop(object,'GLOBAL_no_blend'):
                                    face.alpha=[Prim.TEST,round(float(get_prop(object,'GLOBAL_no_blend',0.5)),2)]
                                else:
                                    face.alpha=[Prim.TEST,0.5]

                        if mode & Mesh.FaceModes.TWOSIDE:
                            face.flags|=Prim.TWOSIDE
                            twosideerr.append(f)

                        if not mode&(Mesh.FaceModes.TILES|Mesh.FaceModes.LIGHT) or self.iscockpit:
                            face.flags|=Prim.NPOLY
                        elif has_prop(object,'ATTR_draped'):
                            face.flags|=(Prim.DRAPED|Prim.NPOLY)

                        if self.ispanelok and mode&Mesh.FaceModes.TEX:
                            if f.image in self.regions:
                                face.flags=(face.flags|Prim.PANEL)&~Prim.ALPHA
                                face.region=self.regions.keys().index(f.image)
                            elif f.image and 'panel.' in f.image.name.lower():
                                face.flags|=Prim.PANEL

                        if not self.iscockpit and (self.additive_lod or (object.Layer&1)) and not mode&Mesh.FaceModes.DYNAMIC:
                            face.flags|=hardness
                            face.surface=surface
                            harderr.append(f)
                        if mode&Mesh.FaceModes.SHADOW:
                            face.flags|=Prim.NSHADOW

                        face.lit_level = lit_level
                        if draw_disable:
                            face.flags|=Prim.DRAW_DISABLE
                        if solid_camera:
                            face.flags|=Prim.SOLID_CAMERA

                        # Special case: if panel-textured faces have _no_ manipulator, auto-apply the panel manipulator.
                        # use the fake name ATTR_manip_panel to mark what we're doing, since X-plane doesn't have a real attribute
                        # command for manipulators.
                        if face.flags&Prim.PANEL and face.manip == "":
                            face.manip="ATTR_manip_panel"

                        for i in range(n):
                            face.i.append(self.prims[animcands[0]+trino].i[i])

                        self.prims.append(face)
                        trino+=1

                if degenerr and self.verbose:
                    print 'Info:\tIgnoring %s degenerate face(s) in mesh "%s"' % (len(degenerr), object.name)
                    self.log.append(('Ignoring %s degenerate face(s) in mesh "%s"' % (len(degenerr), object.name), (object, mesh, degenerr)))
                if harderr:
                    print 'Info:\tFound %s hard face(s) in mesh "%s"' % (len(harderr), object.name)
                    self.log.append(('Found %s hard face(s) in mesh "%s"' % (len(harderr), object.name), (object, mesh, harderr)))
                if twosideerr:
                    print 'Info:\tFound %s two-sided face(s) in mesh "%s"' % (len(twosideerr), object.name)
                    self.log.append(('Found %s two-sided face(s) in mesh "%s"' % (len(twosideerr), object.name), (object, mesh, twosideerr)))
                return

        # Either no animation, or no matching animation
        starttri=len(self.prims)
        # Optimisation: Build list of faces and vertices
        vti = [[] for i in range(len(mesh.verts))]    # indices into vt

        for f in mesh.faces:
            if mesh.faceUV: mode=f.mode
            n=len(f.v)
            if not n in [3,4]:
                degenerr.append(f)
            elif not (mode & Mesh.FaceModes.INVISIBLE):
                if f.mat<len(mats) and mats[f.mat]:
                    material=mats[f.mat]
                    # diffuse, emission, shiny
                    mat=((material.R, material.G, material.B),
                         (material.mirR*material.emit,
                          material.mirG*material.emit,
                          material.mirB*material.emit), material.spec)
#                    if not mat in self.mats: self.mats.append(mat)
                else:
                    mat=DEFMAT
                face=Prim(object, group, 0, None, mat, safe_image_for_face(mesh,f), anim, aidx,'Tri')
                face.manip = decode(object)

                if mode & Mesh.FaceModes.TEX:
                    if len(f.uv)!=n:
                        raise ExportError('Missing UV for face in mesh "%s"' % object.name, (object, mesh, [f]))
                    if f.transp == Mesh.FaceTranspModes.ALPHA:
                        if has_prop(object,'ATTR_shadow_blend'):
                            face.alpha=[Prim.SHADOWTEST,round(float(get_prop(object,'ATTR_shadow_blend',0.5)),2)]
                        elif has_prop(object,'GLOBAL_shadow_blend'):
                            face.alpha=[Prim.SHADOWTEST,round(float(get_prop(object,'GLOBAL_shadow_blend',0.5)),2)]
                        else:
                            face.alpha=[Prim.BLEND,0.0]
                    if f.transp == Mesh.FaceTranspModes.CLIP:
                        if has_prop(object,'ATTR_no_blend'):
                            face.alpha=[Prim.TEST,round(float(get_prop(object,'ATTR_no_blend',0.5)),2)]
                        elif has_prop(object,'GLOBAL_no_blend'):
                            face.alpha=[Prim.TEST,round(float(get_prop(object,'GLOBAL_no_blend',0.5)),2)]
                        else:
                            face.alpha=[Prim.TEST,0.5]

                if mode & Mesh.FaceModes.TWOSIDE:
                    face.flags|=Prim.TWOSIDE
                    twosideerr.append(f)

                if not mode&(Mesh.FaceModes.TILES|Mesh.FaceModes.LIGHT) or self.iscockpit:
                    face.flags|=Prim.NPOLY
                elif has_prop(object,'ATTR_draped'):
                    face.flags|=(Prim.DRAPED|Prim.NPOLY)

                if self.ispanelok and mode&Mesh.FaceModes.TEX:
                    if f.image in self.regions:
                        face.flags=(face.flags|Prim.PANEL)&~Prim.ALPHA
                        face.region=self.regions.keys().index(f.image)
                    elif f.image and 'panel.' in f.image.name.lower():
                        face.flags|=Prim.PANEL

                if not self.iscockpit and (self.additive_lod or (object.Layer&1)) and not mode&Mesh.FaceModes.DYNAMIC:
                    face.flags|=hardness
                    face.surface=surface
                    harderr.append(f)

                if mode&Mesh.FaceModes.SHADOW:
                    face.flags|=Prim.NSHADOW


                if face.flags&Prim.PANEL and face.manip == "":
                    face.manip="ATTR_manip_panel"

                face.lit_level = lit_level
                if draw_disable:
                    face.flags|=Prim.DRAW_DISABLE
                if solid_camera:
                    face.flags|=Prim.SOLID_CAMERA

                for i in seq[n]:
                    nmv=f.verts[i]
                    vertex=Vertex(nmv.co[0], nmv.co[1], nmv.co[2], mm)
                    if up_nrm:
                        norm=Vertex(0,0,1,mm)
                    elif not f.smooth:
                        norm=Vertex(f.no, nm)
                    else:
                        norm=Vertex(nmv.no, nm)
                    if mode & Mesh.FaceModes.TEX:
                        uv=UV(f.uv[i][0], f.uv[i][1])
                    else:    # File format requires something - using (0,0)
                        uv=UV(0,0)
                    vt=VT(vertex, norm, uv)

                    # Does one already exist?
                    # Ben says: why would we ever have more than one of our export VT's
                    # for one mesh vertex?  Simple: each face an have its own UV coord but
                    # vertices are shared in Blender.  So mostly the 'doubling' of vertices will

                    #for j in range(len(self.vt)):    # Search all meshes
                    for j in vti[nmv.index]:        # Search this vertex
                        q=self.vt[j]
                        if vt.equals(q):
                            q.uv= (q.uv+ vt.uv)/2
                            face.i.append(j)
                            break
                    else:
                        j=len(self.vt)
                        self.vt.append(vt)
                        face.i.append(j)
                        vti[nmv.index].append(j)

                self.prims.append(face)

                #if self.debug: print face

        if hasanim:
            # Save tris for matching next
            self.animcands.append(starttri)

        if degenerr and self.verbose:
            print 'Info:\tIgnoring %s degenerate face(s) in mesh "%s"' % (len(degenerr), object.name)
            self.log.append(('Ignoring %s degenerate face(s) in mesh "%s"' % (len(degenerr), object.name), (object, mesh, degenerr)))
        if harderr:
            print 'Info:\tFound %s hard face(s) in mesh "%s"' % (len(harderr), object.name)
            self.log.append(('Found %s hard face(s) in mesh "%s"' % (len(harderr), object.name), (object, mesh, harderr)))
        if twosideerr:
            print 'Info:\tFound %s two-sided face(s) in mesh "%s"' % (len(twosideerr), object.name)
            self.log.append(('Found %s two-sided face(s) in mesh "%s"' % (len(twosideerr), object.name), (object, mesh, twosideerr)))


    #------------------------------------------------------------------------
    # Return name of group that this object belongs to
    def findgroup(self, ob):
        for group in self.groups:
            if ob in group.objects:
                return group
        return None

    #------------------------------------------------------------------------
    # Return (Anim object, Transformation for object relative to world/parent, index of anim in master list)
    def makeAnim(self, child):

        #return (Anim(None), mm)	# test - return frame 1 position

        anim=Anim(self, child)

        # Add parent anims first
        al=[]
        a=anim
        while not a.equals(Anim(self, None)):
            al.insert(0, a)
            a=a.anim

        Blender.Set('curframe', 1)
        #scene=Blender.Scene.GetCurrent()
        #scene.update(1)
        #scene.makeCurrent()	# see Blender bug #4696

        #mm=Matrix(child.getMatrix('localspace')) doesn't work in 2.40alpha
        if self.local_export:
            if child.getParent() == 'None':
                mm=Matrix()
                mm.identity()
            else:
                mm=child.getMatrix('localspace')
        else:
            mm=child.getMatrix('worldspace')

        for a in al:
            # Hack!
            # We need the position of the child in bone space - ie
            # rest position relative to bone root.
            # child.getMatrix('localspace') doesn't return this in 2.40.
            # So un-apply animation from child's worldspace in frame 1:
            #  - get child in worldspace in frame 1 (mm)
            #  - translate so centre of rotation is at origin (-bone root)
            #  - unrotate (-pose rotation)

            if self.debug:
                print "pre\t%s" % mm.rotationPart().toEuler()
                print "\t%s" % mm.translationPart()

            # anim is in X-Plane space. But we need Blender space. Yuck.
            if a.t:
                mm=Matrix(mm[0],mm[1],mm[2],
                          mm[3]-Vector([a.t[0].x, -a.t[0].z, a.t[0].y, 0]))

            if a.r and a.a[0]:
                tr=RotationMatrix(a.a[0], 4, 'r',
                                  -Vector([a.r[0].x, -a.r[0].z, a.r[0].y]))
                mm=mm*tr
                if self.debug:
                    print "rot\t%s" % tr.rotationPart().toEuler()

            if self.debug:
                print "post\t%s" % mm.rotationPart().toEuler()
                print "\t%s" % mm.translationPart()

            # Add Anim, but avoid dups
            for b in self.anims:
                if a.equals(b):
                    anim=b
                    break
            else:
                self.anims.append(a)
                anim=a	# The anim we just made is the last one in the list

        if anim.equals(Anim(self,None)):
            return (anim, mm, -1)
        else:
            return (anim, mm, self.anims.index(anim))


    #------------------------------------------------------------------------
    # PRIMITIVE FLUSHING UTILS
    #------------------------------------------------------------------------
    # These utils manage the output of TRIS and LINES commands, accumulating
    # index range and writing the minimal number of TRIS/LINES
    def flush_prim(self):
        if self.tri_offset != -1:
            self.file.write("%sTRIS\t%d %d\n" %
                (self.tri_ins,self.tri_offset,self.tri_count))
        if self.line_offset != -1:
            self.writeAttr("%sLINES\t%d %d\n" %
                (self.line_ins,self.line_offset,self.line_count))
        self.tri_offset=-1
        self.tri_count=-1
        self.line_offset=-1
        self.line_count=-1

    def accum_tri(self,ins,offset, count):
        if (self.tri_offset+self.tri_count) != offset or self.line_offset != -1:
            self.flush_prim()
            self.tri_offset=offset
            self.tri_count=count
            self.tri_ins=ins
        else:
            self.tri_count+=count
            self.tri_ins=ins

    def accum_line(self,ins,offset, count):
        if (self.line_offset+self.line_count) != offset or self.tri_offset != -1:
            self.flush_prim()
            self.line_offset=offset
            self.line_count=count
            self.line_ins=ins
        else:
            self.line_count+=count
            self.line_ins=ins

    #------------------------------------------------------------------------
    # STATE UPDATE CODE
    #------------------------------------------------------------------------
    # This routine writes the ATTRibutes to the OBJ file based on attributes
    # changing.
    def updateAttr(self, prim):
        layer=prim.layer_now
        group=prim.group
        anim=prim.anim
        region=-1
        surface=None
        mat=None
        hardness=None
        twoside=None
        npoly=None
        draped=None
        panel=None
        alpha=None
        image=None
        nshadow=None
        lit_level=None
        solid_camera=None
        draw_disable=None
        manip=""

        if prim.style=='Tri':
            region=prim.region
            surface=prim.surface
            if self.use_mat:
                mat=prim.mat
            hardness=prim.flags&(Prim.HARD|Prim.DECK)
            twoside=prim.flags&(Prim.TWOSIDE)
            npoly=prim.flags&(Prim.NPOLY)
            draped=prim.flags&(Prim.DRAPED)
            if not draped:
                nshadow=prim.flags&(Prim.NSHADOW)
            panel=prim.flags&(Prim.PANEL)
            alpha=prim.alpha
            image=prim.image
            lit_level=prim.lit_level
            manip=prim.manip
            solid_camera=prim.flags&(Prim.SOLID_CAMERA)
            draw_disable=prim.flags&(Prim.DRAW_DISABLE)
            if draw_disable:
                twoside=None
                npoly=None
                alpha=None
                image=None
                lit_level=None

        # Write in sort order for readability
        if layer!=self.layer:
            # Reset all attributes
            self.flush_prim()
            while not self.anim.equals(Anim(self, None)):
                self.anim=self.anim.anim
                self.writeAttr("%sANIM_end\n" % self.anim.ins())

            self.nshadow=self.global_nshadow
            self.surface=None
            self.mat=DEFMAT
            self.twoside=False
            self.npoly=True
            self.draped=False
            self.panel=False
            self.region=-1
            self.alpha=self.global_alpha
            self.group=None
            self.hardness=False
            self.surface=None
            self.lit_level=None
            self.manip=""
            self.solid_camera=0
            self.draw_disable=0

            if self.layermask==1:
                self.file.write("\n")
            else:
                if self.additive_lod or self.lod[layer/2] == 0:
                    self.file.write("\nATTR_LOD\t0 %d\n" % (self.lod[layer/2+1]))
                else:
                    self.writeAttr("\nATTR_LOD\t%d %d\n" % (self.lod[layer/2], self.lod[layer/2+1]))
            self.layer=layer

        if not anim.equals(self.anim):
            olda=[]
            newa=[]
            a=self.anim
            while not a.equals(Anim(self, None)):
                olda.insert(0, a)
                a=a.anim
            a=anim
            while not a.equals(Anim(self, None)):
                newa.insert(0, a)
                a=a.anim
            for i in range(len(olda)-1,-1,-1):
                if i>=len(newa) or not newa[i].equals(olda[i]):
                    olda.pop()
                    self.anim=self.anim.anim
                    self.flush_prim()
                    self.writeAttr("%sANIM_end\n" % self.anim.ins())
        else:
            newa=olda=[]

        if self.group!=group:
            self.flush_prim()
            if group==None:
                self.file.write("%s####No_group\n" % self.anim.ins())
            else:
                self.file.write("%s####_group\t%s\n" %(self.anim.ins(),group.name))
            self.group=group

        if npoly!=None:
            if self.npoly and not npoly:
                self.flush_prim()
                self.writeAttr("%sATTR_poly_os\t2\n" % self.anim.ins())
            elif npoly and not self.npoly:
                self.flush_prim()
                self.writeAttr("%sATTR_poly_os\t0\n" % self.anim.ins())

            if draped and not self.draped:
                self.flush_prim()
                self.file.write("%sATTR_draped\n" % self.anim.ins())
            elif self.draped and not draped:
                self.flush_prim()
                self.file.write("%sATTR_no_draped\n" % self.anim.ins())

            self.npoly=npoly
            self.draped=draped

        # alpha is implicit - doesn't appear in output file
        if alpha!=None and not self.draped:							# DO NOT RESYNC ALPHA FOR DRAPED - DRAPED IS EXEMPT!
            if self.alpha != alpha and alpha[0] != Prim.OPAQUE:
                self.flush_prim()
                if alpha[0] == Prim.TEST:
                    self.writeAttr ("%sATTR_no_blend %.2f\n" % (self.anim.ins(),alpha[1]))
                elif alpha[0] == Prim.BLEND:
                    self.writeAttr("%sATTR_blend\n" % self.anim.ins())
                elif alpha[0] == Prim.SHADOWTEST:
                    self.writeAttr("%sATTR_shadow_blend %.2f\n" % (self.anim.ins(),alpha[1]))
                self.alpha=alpha

        # Flush panel changes first, since a panel texture change carries an implicit manipulator change
        # in the OBJ8 syntax.  We'll mark the new implicit manip type in our self.manip field to stay in
        # sync with what _X-Plane_ thinks is going on.
        if panel!=None:
            if self.panel and not panel:
                self.flush_prim()
                self.writeAttr("%sATTR_no_cockpit\n" % self.anim.ins())
                self.manip = ""
            elif region!=self.region:
                self.flush_prim()
                self.writeAttr("%sATTR_cockpit_region\t%d\n" % (self.anim.ins(), region))
                self.manip = "ATTR_manip_panel"
            elif panel and not self.panel:
                self.flush_prim()
                self.writeAttr("%sATTR_cockpit\n" % self.anim.ins())
                self.manip = "ATTR_manip_panel"
            self.panel=panel
            self.region=region

        if manip != self.manip:
            self.flush_prim()
            if manip == "":
                self.writeAttr("%sATTR_manip_none\n" % self.anim.ins())
            elif manip == "ATTR_manip_panel":
                # Now if we are out of manip sync _and_ this face wants panel, it means that
                # we were previously in panel texture mode and the last face took us off to
                # some custom manipulator.  This can happen because manipulators change at high
                # frequency (since they don't push any GL state).  We need to reissue the panel
                # texture attribute, which will be optimized into just a manip-change by X-Plane.
                if panel != Prim.PANEL:
                    print panel, region, manip
                    raise ExportError("Panel manipulator used incorrectly - internal error!")
                self.writeAttr("%s#Change manipulator back to panel manip.\n" % (self.anim.ins()))
                if region > -1:
                    self.writeAttr("%sATTR_cockpit_region\t%d\n" % (self.anim.ins(), region))
                else:
                    self.writeAttr("%sATTR_cockpit\n" % self.anim.ins())
            else:
                self.writeAttr("%s%s\n" % (self.anim.ins(),manip))
            self.manip = manip

        for i in newa[len(olda):]:
            self.flush_prim()
            self.writeAttr("%sANIM_begin\n" % self.anim.ins())
            self.anim=i
            for (sh, d, v1, v2) in self.anim.showhide:
                self.writeAttr("%sANIM_%s\t%s %s\t%s\n" % (
                    self.anim.ins(), sh, v1, v2, d))

            if len(self.anim.t)==0 or (len(self.anim.t)==1 and self.anim.t[0].equals(Vertex(0,0,0))):
                pass
            elif len(self.anim.t)==1:
                # not moving - save a potential accessor callback
                self.writeAttr("%sANIM_trans\t%s\t%s\t%s %s\t%s\n" % (
                    self.anim.ins(), self.anim.t[0], self.anim.t[0],
                    0, 0, 'no_ref'))
            elif len(self.anim.t)>2 or self.anim.loop:
                self.writeAttr("%sANIM_trans_begin\t%s\n" % (
                    self.anim.ins(), self.anim.dataref))
                for j in range(len(self.anim.t)):
                    self.writeAttr("%s\tANIM_trans_key\t%s\t%s\n" % (
                        self.anim.ins(), self.anim.v[j], self.anim.t[j]))
                if self.anim.loop:
                    self.writeAttr("%s\tANIM_keyframe_loop\t%s\n" % (
                        self.anim.ins(), self.anim.loop))
                self.writeAttr("%sANIM_trans_end\n" % self.anim.ins())
            else:	# v8.x style
                self.writeAttr("%sANIM_trans\t%s\t%s\t%s %s\t%s\n" % (
                    self.anim.ins(), self.anim.t[0], self.anim.t[1],
                    self.anim.v[0], self.anim.v[1], self.anim.dataref))

            if len(self.anim.r)==0:
                pass
            elif len(self.anim.r)==1 and len(self.anim.a)==2 and not self.anim.loop:	# v8.x style
                self.writeAttr("%sANIM_rotate\t%s\t%6.2f %6.2f\t%s %s\t%s\n"%(
                    self.anim.ins(), self.anim.r[0],
                    self.anim.a[0], self.anim.a[1],
                    self.anim.v[0], self.anim.v[1], self.anim.dataref))
            elif len(self.anim.r)==2 and not self.anim.loop:	# v8.x style
                self.writeAttr("%sANIM_rotate\t%s\t%6.2f %6.2f\t%s %s\t%s\n"%(
                    self.anim.ins(), self.anim.r[0],
                    self.anim.a[0], 0,
                    self.anim.v[0], self.anim.v[1], self.anim.dataref))
                self.writeAttr("%sANIM_rotate\t%s\t%6.2f %6.2f\t%s %s\t%s\n"%(
                    self.anim.ins(), self.anim.r[1],
                    0, self.anim.a[1],
                    self.anim.v[0], self.anim.v[1], self.anim.dataref))
            elif len(self.anim.r)==1:		# v9.x style, one axis
                self.writeAttr("%sANIM_rotate_begin\t%s\t%s\n"%(
                    self.anim.ins(), self.anim.r[0], self.anim.dataref))
                for j in range(len(self.anim.a)):
                    self.writeAttr("%s\tANIM_rotate_key\t%s\t%6.2f\n" % (
                        self.anim.ins(), self.anim.v[j], self.anim.a[j]))
                if self.anim.loop:
                    self.writeAttr("%s\tANIM_keyframe_loop\t%s\n" % (
                        self.anim.ins(), self.anim.loop))
                self.writeAttr("%sANIM_rotate_end\n" % self.anim.ins())
            else:				# v9.x style, multiple axes
                for axis in [[0,0,1],[0,1,0],[1,0,0]]:
                    self.writeAttr("%sANIM_rotate_begin\t%d %d %d\t%s\n"%(
                        self.anim.ins(), axis[0], axis[1], axis[2], self.anim.dataref))
                    for j in range(len(self.anim.r)):
                        self.writeAttr("%s\tANIM_rotate_key\t%s\t%6.2f\n" % (
                            self.anim.ins(), self.anim.v[j], Quaternion(self.anim.r[j].toVector(3), self.anim.a[j]).toEuler()[axis.index(1)]))
                    if self.anim.loop:
                        self.writeAttr("%s\tANIM_keyframe_loop\t%s\n" % (
                            self.anim.ins(), self.anim.loop))
                    self.writeAttr("%sANIM_rotate_end\n" % self.anim.ins())

        if mat!=None:
            if self.mat!=mat and mat==DEFMAT:
                self.flush_prim()
                self.writeAttr("%sATTR_reset\n" % self.anim.ins())
            else:
                # diffuse, emission, shiny
                if self.mat[0]!=mat[0]:
                    self.flush_prim()
                    self.writeAttr("%sATTR_diffuse_rgb\t%6.3f %6.3f %6.3f\n" % (self.anim.ins(), mat[0][0], mat[0][1], mat[0][2]))
                if self.mat[1]!=mat[1]:
                    self.flush_prim()
                    self.writeAttr("%sATTR_emission_rgb\t%6.3f %6.3f %6.3f\n" % (self.anim.ins(), mat[1][0], mat[1][1], mat[1][2]))
                if self.mat[2]!=mat[2]:
                    self.flush_prim()
                    self.writeAttr("%sATTR_shiny_rat\t%6.3f\n" % (self.anim.ins(), mat[2]))
            self.mat=mat

        if twoside!=None:
            if self.twoside and not twoside:
                self.flush_prim()
                self.writeAttr("%sATTR_cull\n" % self.anim.ins())
            elif twoside and not self.twoside:
                self.flush_prim()
                self.writeAttr("%sATTR_no_cull\n" % self.anim.ins())
            self.twoside=twoside

        if hardness!=None:
            if self.hardness and not hardness:
                self.flush_prim()
                self.file.write("%sATTR_no_hard\n" % self.anim.ins())
                self.surface=None
            elif self.hardness!=hardness or self.surface!=surface:
                if surface:
                    thing='\t'+surface
                else:
                    thing=''
                if hardness==Prim.DECK:
                    if surface:
                        self.flush_prim()
                        self.file.write("%sATTR_hard_deck\t%s\n" % (self.anim.ins(), surface))
                    else:
                        self.flush_prim()
                        self.file.write("%sATTR_hard_deck\n" % self.anim.ins())
                elif hardness:
                    if surface:
                        self.flush_prim()
                        self.file.write("%sATTR_hard\t%s\n" % (self.anim.ins(), surface))
                    else:
                        self.flush_prim()
                        self.file.write("%sATTR_hard\n" % self.anim.ins())
                self.surface=surface
            self.hardness=hardness

        if nshadow!=None:
            if self.nshadow and not nshadow:
                self.flush_prim()
                self.writeAttr("%sATTR_shadow\n" % self.anim.ins())
            elif nshadow and not self.nshadow:
                self.flush_prim()
                self.writeAttr("%sATTR_no_shadow\n" % self.anim.ins())
            self.nshadow = nshadow
        if image != self.image:
            self.flush_prim()
            # if image != None:
            #     self.file.write("# Image: %s\n" % image.filename)
            # else:
            #     self.file.write("# Image: None\n")
            self.image=image
        if lit_level != self.lit_level:
            self.flush_prim()
            if lit_level != None:
                self.writeAttr("%sATTR_light_level %s\n" % (self.anim.ins(),lit_level))
            else:
                self.writeAttr("%sATTR_light_level_reset\n" % self.anim.ins())
            self.lit_level=lit_level

        if draw_disable != None:
            if draw_disable != self.draw_disable:
                self.flush_prim()
                if draw_disable:
                    self.writeAttr("%sATTR_draw_disable\n" % self.anim.ins())
                else:
                    self.writeAttr("%sATTR_draw_enable\n" % self.anim.ins())
                self.draw_disable = draw_disable

        if solid_camera != None:
            if solid_camera != self.solid_camera:
                self.flush_prim()
                if solid_camera:
                    self.writeAttr("%sATTR_solid_camera\n" % self.anim.ins())
                else:
                    self.writeAttr("%sATTR_no_solid_camera\n" % self.anim.ins())
                self.solid_camera = solid_camera

#------------------------------------------------------------------------
class Anim:
    def __init__(self, expobj, child, bone=None):
        self.dataref=None	# None if null
        self.r=[]	# 0, 1, 2 or n-1 rotation vectors
        self.a=[]	# rotation angles, 0 or n-1 rotation angles
        self.t=[]	# translation, 0, 1 or n-1 translations
        self.v=[0,1]	# dataref value
        self.loop=0	# loop value (XPlane 9)
        self.showhide=[]	# show/hide values (show/hide, name, v1, v2)
        self.anim=None	# parent Anim

        if not child:
            return	# null

        object=child.parent	# child is lamp/mesh. object is parent armature
        if not object or object.getType()!='Armature':
            return

        if Blender.Get('version')<240:
            raise ExportError('Blender version 2.40 or later required for animation')

        #if object.parent:
        #    raise ExportError('Armature "%s" has a parent; this is not supported. Use multiple bones within a single armature to represent complex animations.' % object.name, [object])

        if not bone:
            bonename=child.getParentBoneName()
            if not bonename: raise ExportError('%s "%s" has an armature as its parent. Make "%s" the child of a bone' % (child.getType(), child.name, child.name), [child])
            bones=object.getData().bones
            if bonename in bones.keys():
                bone=bones[bonename]
            else:
                raise ExportError('%s "%s" has a deleted bone "%s" as its parent. Either make "%s" the child of an existing bone, or clear its parent' % (child.getType(), child.name, bonename, child.name), [child])

        if bone.parent:
            #print "bp", child, bone.parent
            self.anim=Anim(expobj, child, bone.parent)
        elif object.parent and object.parent.getType()=='Armature':
            # child's parent armature is itself parented to an armature
            bonename=object.getParentBoneName()
            if not bonename: raise ExportError('Bone "%s" has an armature as its parent. Make "%s" the child of another bone' % (bone.name, bone.name), [child])
            bones=object.parent.getData().bones
            if bonename in bones.keys():
                parentbone=bones[bonename]
            else:
                raise ExportError('%s "%s" has a deleted bone "%s" as its parent. Either make "%s" the child of an existing bone, or clear its parent' % (child.getType(), child.name, bonename, child.name), [child])
            #print "ob", object, parentbone
            self.anim=Anim(expobj, object, parentbone)
        else:
            self.anim=Anim(expobj, None)

        if not bone.parent:
            # Hide/show values if eldest bone in its armature
            vals={}
            for prop in object.getAllProperties():
                propname=prop.name.strip()
                for suffix in ['_hide_v', '_show_v']:
                    if not (suffix) in propname: continue
                    digit=propname[propname.index(suffix)+7:]
                    if not digit.isdigit() or not int(digit)&1: continue
                    (ref, v, loop)=self.getdataref(object, child, propname[:propname.index(suffix)], suffix[:-2], int(digit), 2)
                    if not None in v:
                        self.showhide.append((suffix[1:5],ref,v[0],v[1]))

        # find last frame
        framecount=0	# zero based
        action=object.getAction()
        if action and bone.name in action.getChannelNames():
            ipo=action.getChannelIpo(bone.name)
            for icu in ipo:
                for bez in icu.bezierPoints:
                    f=bez.pt[0]
                    if f>int(f):
                        framecount=max(framecount,int(f)+1) # like math.ceil()
                    else:
                        framecount=max(framecount,int(f))

        if framecount<2:
            print 'Warn:\tYou haven\'t created animation keys in frames 1 and 2 for bone "%s" in armature "%s". Skipping this bone.' % (bone.name, object.name)
            expobj.log.append(('Ignoring bone "%s" in armature "%s" - you haven\'t created animation keys in frames 1 and 2' % (bone.name, object.name), [child]))

            if self.showhide:
                # Create a dummy animation to hold hide/show values
                self.dataref='no_ref'	# mustn't eval to False
                self.t=[Vertex(0,0,0)]
            elif bone.parent:
                foo=Anim(expobj, child, bone.parent)
                self.dataref=foo.dataref
                self.r=foo.r
                self.a=foo.a
                self.t=foo.t
                self.v=foo.v
                self.loop=foo.loop
                self.showhide=foo.showhide
                self.anim=foo.anim
            else:
                self.dataref=None	# is null
            return
        elif framecount>2:
            expobj.v9=True

        (self.dataref, self.v, self.loop)=self.getdataref(object, child, bone.name, '', 1, framecount)
        if None in self.v:
            raise ExportError('Armature "%s" is missing a %s_v%d property' % (object.name, self.dataref.split('/')[-1], 1+self.v.index(None)), [child])

        scene=Blender.Scene.GetCurrent()

        if 0:	# debug
            for frame in range(1,framecount+1):
                Blender.Set('curframe', frame)
                #scene.update(1)
                #scene.makeCurrent()	# see Blender bug #4696
                print "Frame\t%s" % frame
                print child
                print "local\t%s" % child.getMatrix('localspace').rotationPart().toEuler()
                print "\t%s" % child.getMatrix('localspace').translationPart()
                print "world\t%s" % child.getMatrix('worldspace').rotationPart().toEuler()
                print "\t%s" % child.getMatrix('worldspace').translationPart()
                print object
                print "local\t%s" % object.getMatrix('localspace').rotationPart().toEuler()
                print "\t%s" % object.getMatrix('localspace').translationPart()
                print "world\t%s" % object.getMatrix('worldspace').rotationPart().toEuler()
                print "\t%s" % object.getMatrix('worldspace').translationPart()
                print bone
                print "bone\t%s" % bone.matrix['BONESPACE'].rotationPart().toEuler()
                #crashes print "\t%s" % bone.matrix['BONESPACE'].translationPart()
                print "arm\t%s" % bone.matrix['ARMATURESPACE'].rotationPart().toEuler()
                print "\t%s" % bone.matrix['ARMATURESPACE'].translationPart()
                print "head\t%s" % bone.head
                print "tail\t%s" % bone.tail
                print "roll\t%s" % bone.roll
                print ipo
                q = Quaternion([ipo.getCurveCurval('QuatW'),
                                ipo.getCurveCurval('QuatX'),
                                ipo.getCurveCurval('QuatY'),
                                ipo.getCurveCurval('QuatZ')])
                print "ipo\t%s" % q.toEuler()
                print "\t%s %s" % (q.angle, q.axis)
                print "\t%s" % Vector([ipo.getCurveCurval('LocX'),
                                       ipo.getCurveCurval('LocY'),
                                       ipo.getCurveCurval('LocZ')])
            print

        # Useful info in Blender 2.40:
        # child.getMatrix('localspace') - rot & trans rel to arm pre pose
        # child.getMatrix('worldspace') - rot & trans post pose
        # armature.getMatrix('local/worldspace') - abs position pre pose
        # bone.getRestMatrix('bonespace') - broken
        # bone.getRestMatrix('worldspace') - rot & trans rel to arm pre pose
        # bone.head - broken
        # bone.tail - posn of tail rel to armature pre pose
        # ipo - bone position rel to rest posn post pose
        #
        # In X-Plane:
        # Transformations are relative to unrotated position and cumulative
        # Rotations are relative to each other (ie cumulative)

        # Need to unset resting position of parent armature
        object.getData().restPosition=False
        # But grandparent armature (if any) need to be resting, since
        # getMatrix('localspace') doesn't account for rotation due to pose
        a=object.parent
        while a and a.getType() == 'Armature':
            a.getData().restPosition=True
            a=a.parent

        moved=False
        for frame in range(1,framecount+1):
            Blender.Set('curframe', frame)
            #scene.update(1)
            #scene.makeCurrent()	# see Blender bug #4696
            mm=object.getMatrix('worldspace')
            # mm.rotationPart() scaled to be unit size for rotation axis
            rm=MatrixrotationOnly(mm, object)

            if (not (bone.parent and Armature.CONNECTED in bone.options) and
                ipo.getCurve('LocX') and
                ipo.getCurve('LocY') and
                ipo.getCurve('LocZ')):
                t = Vector([ipo.getCurveCurval('LocX'),
                            ipo.getCurveCurval('LocY'),
                            ipo.getCurveCurval('LocZ')])
            else:
                t = Vector(0,0,0)

            t=Vertex(t*bone.matrix['ARMATURESPACE'].rotationPart()+
                     bone.matrix['ARMATURESPACE'].translationPart(),mm)
            # Child offset should be relative to parent
            anim=self.anim
            while not anim.equals(Anim(expobj, None)):
                t=t-anim.t[0]	# mesh location is relative to first frame
                anim=anim.anim
            self.t.append(t)
            if not t.equals(self.t[0]):
                moved=True

            if (ipo.getCurve('QuatW') and
                ipo.getCurve('QuatX') and
                ipo.getCurve('QuatY') and
                ipo.getCurve('QuatZ')):
                q=Quaternion([ipo.getCurveCurval('QuatW'),
                              ipo.getCurveCurval('QuatX'),
                              ipo.getCurveCurval('QuatY'),
                              ipo.getCurveCurval('QuatZ')])
                # In bone space
                qr=Vertex(q.axis*bone.matrix['ARMATURESPACE'].rotationPart(), rm)	# rotation axis
                a = round(q.angle, Vertex.ROUND)	# rotation angle
                if a==0:
                    self.r.append(None)	# axis doesn't matter if no rotation
                    self.a.append(0)
                else:
                    self.r.append(qr)
                    self.a.append(a)
            else:
                self.r.append(None)
                self.a.append(0)

        # Collapse translations if not moving
        if not moved:
            self.t=[self.t[0]]

        # Collapse rotation axes if coplanar
        coplanar=True
        r=None	# first axis
        for i in range(len(self.a)):
            if self.r[i]:
                if not r:
                    r=self.r[i]
                elif r.equals(-self.r[i]):
                    self.r[i]=-self.r[i]
                    self.a[i]=-self.a[i]
                elif not r.equals(self.r[i]):
                    coplanar=False
                    break
        if coplanar:
            if r:
                self.r=[r]
            else:
                self.r=[]
                self.a=[]
        else:
            for i in range(len(self.a)):
                if not self.r[i]:
                    self.r[i]=Vertex(0,1,0)	# arbitrary

        a=object.parent
        while a and a.getType() == 'Armature':
            a.getData().restPosition=False
            a=a.parent


    #------------------------------------------------------------------------
    # This routine reconstructs the full dataref name, key frame table (dataref
    # side) and loop value in a tuple.  This is NOT particularly easy to do
    # given how the properties are stored.  On input we take:
    # object - the armature that contains our bones.
    # child - the mesh we are animating
    # name - the bone name
    # suffix -
    # first, count
    def getdataref(self, object, child, name, suffix, first, count):
        if not suffix:
            thing='bone in armature'
            vals=[1 for i in range(count)]
            vals[0]=0
        else:
            thing='property in armature'
            vals=[None for i in range(count)]

        l=name.find('.')
        if l!=-1: name=name[:l]
        name=name.strip()
        # split name into ref & idx
        l=name.find('[')
        if l!=-1 and not name in datarefs:
            ref=name[:l].strip()
            idx=name[l+1:-1]
            if name[-1]!=']' or not idx or not idx.isdigit():
                raise ExportError('Malformed dataref index "%s" in bone "%s" in armature "%s"' % (name[l:], name, object.name), [child])
            idx_str="["+idx+"]"
            idx=int(idx)
            seq=[ref, name]
        else:
            ref=name
            idx_str=""
            idx=None
            seq=[ref]

        props=object.getAllProperties()

        if ref in datarefs and datarefs[ref]:
            (path, n)=datarefs[ref]
            dataref=path+idx_str
            if n==0:
                raise ExportError('Dataref %s can\'t be used for animation' % path+ref, [child])
            elif n==1 and idx!=None:
                raise ExportError('Dataref %s is not an array. Rename the %s to "%s"' % (path+ref, thing, ref), [child])
            elif n!=1 and idx==None:
                raise ExportError('Dataref %s is an array. Rename the %s to "%s[0]" to use the first value, etc' % (path+ref, thing, ref), [child])
            elif n!=1 and idx>=n:
                raise ExportError('Dataref %s has usable values from [0] to [%d]; but you specified [%d]' % (path+ref, n-1, idx), [child])
        else:
            dataref=getcustomdataref(object, child, thing, seq)

        seq.append(make_short_name(dataref))

        # dataref values vn and loop
        loop=0
        for tmpref in seq:
            for val in range(first,first+count):
                valstr="%s%s_v%d" % (tmpref, suffix, val)
                for prop in object.getAllProperties():
                    if prop.name.strip()==valstr:
                        if prop.type=='INT':
                            vals[val-first]=prop.data
                        elif prop.type=='FLOAT':
                            vals[val-first]=round(prop.data, Vertex.ROUND)
                        else:
                            raise ExportError('Unsupported data type for "%s" in armature "%s"' % (valstr, object.name), [child])
            valstr="%s%s_loop" % (tmpref, suffix)
            for prop in object.getAllProperties():
                if prop.name.strip()==valstr:
                    if prop.type=='INT':
                        loop=prop.data
                    elif prop.type=='FLOAT':
                        loop=round(prop.data, Vertex.ROUND)
                    else:
                        raise ExportError('Unsupported data type for "%s" in armature "%s"' % (valstr, object.name), [child])

        return (dataref, vals, loop)


    #------------------------------------------------------------------------
    def __str__ (self):
        if self.dataref:
            return "%x %s r=%s a=%s t=%s v=%s p=(%s)" % (id(self), self.dataref, self.r, self.a, self.t, self.v, self.anim)
        else:
            return "None"

    #------------------------------------------------------------------------
    def equals (self, b):
        if self is b:
            return True
        if not self.dataref:	# null
            return not b.dataref
        if (self.dataref!=b.dataref or
            len(self.r)!=len(b.r) or
            len(self.a)!=len(b.a) or
            len(self.t)!=len(b.t) or
            self.v!=b.v or
            not self.anim.equals(b.anim)):
            return False
        if self.showhide!=b.showhide:
            return False
        for i in range(len(self.r)):
            if not self.r[i].equals(b.r[i]):
                return False
        for i in range(len(self.t)):
            if not self.t[i].equals(b.t[i]):
                return False
        for i in range(len(self.a)):
            if abs(self.a[i]-b.a[i])>Vertex.LIMIT:
                return False
        return True

    #------------------------------------------------------------------------
    def ins(self):
        t=''
        anim=self
        while not anim.equals(Anim(self, None)):
            t=t+"\t"
            anim=anim.anim
        return t


#------------------------------------------------------------------------
def getcustomdataref(object, child, thing, names):
    dataref=None
    props=object.getAllProperties()
    for tmpref in names:
        for prop in props:
            if prop.name.strip()==tmpref:
                # custom dataref
                if prop.type=='STRING':
                    path=prop.data.strip()
                    if path and path[-1]!='/': path=path+'/'
                    dataref=path+names[-1]
                else:
                    raise ExportError('Unsupported data type for full name of custom dataref "%s" in armature "%s"' % (names[0], object.name), [child])
                break
    if not dataref:
        if names[0] in datarefs:
            if object==child:	# not animation
                raise ExportError('Dataref %s is ambiguous. Add a new string property named %s with the path name of the dataref that you want to use' % (names[0], names[0]), [object])
            else:		# animation
                raise ExportError('Dataref %s is ambiguous. Specify the full name in the X-Plane Animation dialog' % names[0], [child])
        else:
            raise ExportError('Unrecognised dataref "%s" for %s "%s"' % (names[0], thing, object.name), [child])
    return dataref
