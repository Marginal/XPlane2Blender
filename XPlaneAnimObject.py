#!BPY
""" Registration info for Blender menus:
Name: 'X-Plane Animation'
Blender: 243
Group: 'Object'
Tooltip: 'Edit X-Plane animation'
"""
__author__ = "Jonathan Harris"
__email__ = "Jonathan Harris, Jonathan Harris <x-plane:marginal*org*uk>"
__url__ = "XPlane2Blender, http://marginal.org.uk/x-planescenery/"
__version__ = "3.01"
__bpydoc__ = """\
Edit X-Plane animation properties.
"""

#------------------------------------------------------------------------
#
# Copyright (c) 2007 Jonathan Harris
# 
# Mail: <x-plane@marginal.org.uk>
# Web:  http://marginal.org.uk/x-planescenery/
#
# See XPlane2Blender.html for usage.
#
# This software is licensed under a Creative Commons License
#   Attribution-ShareAlike 2.5:
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
#   http://creativecommons.org/licenses/by-sa/2.5/legalcode
#
#
# 2007-12-03 v3.01
#  - New file
#

import Blender
from Blender import BGL, Draw, Object, Scene, Window

from XPlaneUtils import Vertex, getDatarefs

theobject=None

# Globals
lookup={}
hierarchy={}
firstlevel=[]
armature=None
bonecount=0	# number of parent bones 
bones=[]	# all bones in armature
framecount=2
datarefs=[]
indices=[]
vals=[]
loops=[]
hideshow=[]
hideorshow=[]
hideshowindices=[]
hideshowfrom=[]
hideshowto=[]

# Layout
vertical=False
PANELPAD=7
PANELINDENT=8
PANELTOP=8
PANELHEAD=20
PANELWIDTH=304
CONTROLSIZE=19

# Shared buttons. Indices<bonecount are for bones, >=bonecount are for hideshow
dataref_m=[]
dataref_b=[]
indices_b=[]
indices_t=[]

# Value buttons
vals_b=[]
clear_b=None
loops_b=[]

# Hide/Show buttons
hideshow_m=[]
from_b=[]
to_b=[]
up_b=[]
down_b=[]
delete_b=[]
addhs_b=None
cancel_b=None
apply_b=None

# Event IDs
DONTCARE=0
DATAREF_B=1
INDICES_B=2
INDICES_T=3
CLEAR_B=HIDEORSHOW_M=4
LOOPS_B=FROM_B=5
VALS_B=TO_B=6	# VALS must be last
UP_B=7
DOWN_B=8
DELETE_B=9
ADD_B=10
CANCEL_B=11
APPLY_B=12
EVENTMAX=256


def getparents():
    global lookup, hierarchy, firstlevel, armature, bones, theobject

    if Window.EditMode():
        objects=[Scene.GetCurrent().objects.active]
    else:
        objects = Object.GetSelected()
    for theobject in objects:
        parent=theobject.parent
        if not parent or parent.getType()!='Armature':
            Draw.PupMenu('Object "%s" is not a child of a bone.' % theobject.name)
            return None
        bonename=theobject.getParentBoneName()
        if not bonename:
            Draw.PupMenu('Object "%s" is the child of an armature. It should be the child of a bone.' % theobject.name)
            return None
        thisbones=parent.getData().bones
        if bonename in thisbones.keys():
            bone=thisbones[bonename]
        else:
            Draw.PupMenu('Object "%s" has a deleted bone as its parent.' % theobject.name)
            return None
        if armature and (parent!=armature or bone!=bones[0]):
            Draw.PupMenu('You have selected multiple objects with different parents.')
            return None
        else:
            armature=parent
            bones=[bone]

    if not bones: return
    bone=bones[0]
    while bone.parent:
        bones.append(bone.parent)
        bone=bone.parent

    try:
        (lookup, hierarchy)=getDatarefs()
        firstlevel=hierarchy['sim'].keys()
        firstlevel.sort(lambda x,y: -cmp(x.lower(), y.lower()))

    except IOError, e:
        Draw.PupMenu(str(e))
        return None
        
    return True


# populate vals array and loop value
def getvals(dataref, index):
    if dataref in lookup and lookup[dataref]:
        (path, n)=lookup[dataref]
        fullref=path+dataref
    else:
        fullref=dataref        
    vals=[0.0]+[1.0 for i in range(framecount-1)]
    loop=0.0

    props=armature.getAllProperties()
    seq=[dataref]
    if index: seq.append('%s[%d]' % (dataref, index))

    for tmpref in seq:
        for val in range(framecount):
            valstr="%s_v%d" % (tmpref, val+1)
            for prop in props:
                if prop.name.strip()==valstr:
                    if prop.type=='INT':
                        vals[val]=float(prop.data)
                    elif prop.type=='FLOAT':
                        vals[val]=round(prop.data, Vertex.ROUND)
        valstr="%s_loop" % tmpref
        for prop in props:
            if prop.name.strip()==valstr:
                if prop.type=='INT':
                    loop=float(prop.data)
                elif prop.type=='FLOAT':
                    loop=round(prop.data, Vertex.ROUND)
            if prop.name.strip()==dataref and prop.type=='STRING' and prop.data:
                if prop.data.endswith('/'):
                    fullref=prop.data+dataref
                else:
                    fullref=prop.data+'/'+dataref
            
    return (fullref,vals,loop)


def gethideshow():
    props=armature.getAllProperties()

    for prop in props:
        propname=prop.name
        for suffix in ['_hide_v', '_show_v']:
            if not (suffix) in propname: continue
            digit=propname[propname.index(suffix)+7:]
            if not digit.isdigit() or not int(digit)&1: continue
            dataref=propname[:propname.index(suffix)]
            if prop.type=='INT':
                fr=float(prop.data)
            elif prop.type=='FLOAT':
                fr=round(prop.data, Vertex.ROUND)
            else:
                continue

            # look for matching pair
            valstr='%s%s%d' % (dataref, suffix, int(digit)+1)
            for prop in props:
                if prop.name==valstr:
                    if prop.type=='INT':
                        to=float(prop.data)
                        break
                    elif prop.type=='FLOAT':
                        to=round(prop.data, Vertex.ROUND)
                        break
            else:
                continue

            # split off index
            index=None
            l=dataref.find('[')
            if l!=-1:
                i=dataref[l+1:-1]
                if dataref[-1]==']':
                    try:
                        index=int(i)
                    except:
                        pass
                dataref=dataref[:l]

            if dataref in lookup and lookup[dataref]:
                (path, n)=lookup[dataref]
                fullref=path+dataref
            else:
                # look for full name
                fullref=dataref
                seq=[dataref]
                if index: seq.append('%s[%d]' % (dataref, index))
                for tmpref in seq:
                    for prop in props:
                        if prop.name.strip()==dataref and prop.type=='STRING' and prop.data:
                            if prop.data.endswith('/'):
                                fullref=prop.data+dataref
                            else:
                                fullref=prop.data+'/'+dataref

            hideshow.append(fullref)
            if suffix=='_hide_v':
                hideorshow.append(0)
            else:
                hideorshow.append(1)
            hideshowindices.append(index)
            hideshowfrom.append(fr)
            hideshowto.append(to)


def swaphideshow(a,b):
    t=hideshow[a]
    hideshow[a]=hideshow[b]
    hideshow[b]=t
    t=hideorshow[a]
    hideorshow[a]=hideorshow[b]
    hideorshow[b]=t
    t=hideshowindices[a]
    hideshowindices[a]=hideshowindices[b]
    hideshowindices[b]=t
    t=hideshowfrom[a]
    hideshowfrom[a]=hideshowfrom[b]
    hideshowfrom[b]=t
    t=hideshowto[a]
    hideshowto[a]=hideshowto[b]
    hideshowto[b]=t


# apply settings
def apply(evt,val):
    global bonecount

    editmode=Window.EditMode()
    if editmode: Window.EditMode(0)
    armobj=armature.getData()
    armobj.makeEditable()
    armbones=armobj.bones

    # rescan object's parents - hope that the user hasn't reparented
    bone=armbones[theobject.getParentBoneName()]
    editbones=[bone]
    while bone.parent:
        editbones.append(bone.parent)
        bone=bone.parent
    bonecount=min(bonecount, len(editbones))	# in case user has reparented
    
    # Rename bones - see armature_bone_rename in editarmature.c
    oldnames=[bone.name for bone in editbones]
    othernames=armbones.keys()
    for name in oldnames: othernames.remove(name)
    newnames=[]

    action=armature.getAction()
    for boneno in range(bonecount):
        # rename this Action's channels to prevent error on dupes
        if oldnames[boneno] in action.getChannelNames():
            action.renameChannel(oldnames[boneno], 'TmpChannel%d' % boneno)
    
    for boneno in range(bonecount-1,-1,-1):
        # do in reverse order in case of duplicate names
        name=datarefs[boneno].split('/')[-1]
        if indices[boneno]!=None: name='%s[%d]' % (name, indices[boneno])
        # Have to manually avoid duplicate names
        i=0
        base=name
        while True:
            if name in othernames:
                i+=1
                name='%s.%03d' % (base, i)
            else:
                break

        editbones[boneno].name=name
        othernames.append(name)
        newnames.insert(0, name)

        # Update this Action's channels
        oldchannel='TmpChannel%d' % boneno
        if oldchannel in action.getChannelNames():
            action.renameChannel(oldchannel, name)
        # Update any other Actions' channels?

    armobj.update()	# apply new bone names

    # Reparent children - have to do this after new bone names are applied
    for obj in Scene.GetCurrent().objects:
        if obj.parent==armature and obj.parentbonename in oldnames:
            obj.parentbonename=newnames[oldnames.index(obj.parentbonename)]
        
    # Now do properties
    props={}

    # First do dataref paths
    for dataref in datarefs+hideshow:
        ref=dataref.split('/')
        if ref[-1] not in lookup or not lookup[ref[-1]]:
            # not a standard dataref
            props[ref[-1]]='/'.join(ref[:-1])

    # values
    for boneno in range(len(datarefs)):
        name=datarefs[boneno].split('/')[-1]
        if indices[boneno]!=None: name='%s[%d]' % (name, indices[boneno])
        for frameno in range(framecount):
            if not ((frameno==0 and vals[boneno][frameno]==0) or
                    (frameno==(framecount-1) and vals[boneno][frameno]==1)):
                props['%s_v%d' % (name, frameno+1)]=vals[boneno][frameno]
        if loops[boneno]:
            props[name+'_loop']=loops[boneno]

    # Apply
    armature.removeAllProperties()
    keys=props.keys()
    keys.sort()
    for key in keys:
        armature.addProperty(key, props[key])

    # Hide/Show - order is significant
    h=1
    s=1
    for hs in range(len(hideshow)):
        name=hideshow[hs].split('/')[-1]
        if hideshowindices[hs]!=None: name='%s[%d]' % (name, hideshowindices[hs])
        if hideorshow[hs]:
            armature.addProperty('%s_show_v%d' % (name, s), hideshowfrom[hs])
            armature.addProperty('%s_show_v%d' % (name, s+1), hideshowto[hs])
            s+=2
        else:
            armature.addProperty('%s_hide_v%d' % (name, s), hideshowfrom[hs])
            armature.addProperty('%s_hide_v%d' % (name, s+1), hideshowto[hs])
            h+=2

    Draw.Exit()
    if editmode: Window.EditMode(1)
    Window.RedrawAll()	# in case bone names have changed
    return


# the function to handle input events
def event (evt, val):
    global vertical

    if evt == Draw.ESCKEY and not val:
        Draw.Exit()                 # exit when user releases ESC
    elif evt == Draw.RIGHTMOUSE and val:
        r=Draw.PupMenu('Panel Alignment%t|Horizontal|Vertical')
        if r==1:
            vertical=False
        elif r==2:
            vertical=True
        else:
            return
        Draw.Redraw()


# the function to handle Draw Button events
def bevent (evt):
    global framecount

    boneno=evt/EVENTMAX
    event=evt-boneno*EVENTMAX
    if boneno>=bonecount:
        # hide/show
        hs=boneno-bonecount
        if event==DATAREF_B:
            hideshow[hs]=dataref_b[boneno].val
            ref=hideshow[hs].split('/')
            if len(ref)==1:
                # lookup
                if hideshow[hs] in lookup and lookup[hideshow[hs]]:
                    (path, n)=lookup[hideshow[hs]]
                    hideshow[hs]=path+hideshow[hs]
        elif event==INDICES_B:
            hideshowindices[hs]=indices_b[boneno].val
        elif event==INDICES_T:
            if indices_t[boneno].val and hideshowindices[hs]==None:
                hideshowindices[hs]=0
            elif not indices_t[boneno].val:
                hideshowindices[hs]=None
        elif event==HIDEORSHOW_M:
            hideorshow[hs]=hideshow_m[hs].val
        elif event==FROM_B:
            hideshowfrom[hs]=from_b[hs].val
        elif event==TO_B:
            hideshowto[hs]=to_b[hs].val
        elif event==DELETE_B:
            hideshow.pop(hs)
            hideorshow.pop(hs)
            hideshowindices.pop(hs)
            hideshowfrom.pop(hs)
            hideshowto.pop(hs)
        elif event==UP_B and hs:
            swaphideshow(hs-1, hs)
        elif event==DOWN_B and hs<len(hideshow)-1:
            swaphideshow(hs, hs+1)
        elif event==ADD_B:
            hideshow.append('')
            hideorshow.append(0)
            hideshowindices.append(None)
            hideshowfrom.append(0.0)
            hideshowto.append(1.0)
        elif event==CANCEL_B:
            Draw.Exit()
        else:
            return	# eh?
    else:
        if event==DATAREF_B:
            datarefs[boneno]=dataref_b[boneno].val
            ref=datarefs[boneno].split('/')
            if len(ref)==1:
                # lookup
                if datarefs[boneno] in lookup and lookup[datarefs[boneno]]:
                    (path, n)=lookup[datarefs[boneno]]
                    datarefs[boneno]=path+datarefs[boneno]
        elif event==INDICES_B:
            indices[boneno]=indices_b[boneno].val
        elif event==INDICES_T:
            if indices_t[boneno].val and indices[boneno]==None:
                indices[boneno]=0
            elif not indices_t[boneno].val:
                indices[boneno]=None
        elif event==CLEAR_B:
            framecount-=1
        elif event==LOOPS_B:
            loops[boneno]=loops_b[boneno].val
            for i in range(len(bones)):
                if datarefs[i]==datarefs[boneno] and indices[i]==indices[boneno]:
                    loops[i]=loops[boneno]
                    for j in range(framecount):
                        vals[i][j]=vals[boneno][j]
        elif event>=VALS_B:
            vals[boneno][event-VALS_B]=vals_b[boneno][event-VALS_B].val
            for i in range(len(bones)):
                if datarefs[i]==datarefs[boneno] and indices[i]==indices[boneno]:
                    loops[i]=loops[boneno]
                    for j in range(framecount):
                        vals[i][j]=vals[boneno][j]
        else:
            return	# eh?
    Draw.Redraw()


def datarefmenucallback(event, val):
    if val==-1: return
    rows=Window.GetScreenSize()[1]/20-1		# 16 point plus space
    boneno=event/EVENTMAX
    ref=['sim',firstlevel[val-1]]
    this=hierarchy['sim'][firstlevel[val-1]]
    while True:
        keys=this.keys()
        keys.sort(lambda x,y: cmp(x.lower(), y.lower()))
        opts=[]
        for i in range(len(keys)):
            key=keys[i]
            if isinstance(this[key], dict):
                opts.append('%s/...%%x%d' % (key,i))
            elif this[key]:	# not illegal
                opts.append('%s%%x%d' % (key,i))
        val=Draw.PupMenu('/'.join(ref)+'/%t'+'|'.join(opts), rows)
        if val==-1: return
        ref.append(keys[val])
        this=this[keys[val]]
        if not isinstance(this, dict):
            if boneno>=bonecount:
                hideshow[boneno-bonecount]='/'.join(ref)                
            else:
                datarefs[boneno]='/'.join(ref)
            Draw.Redraw()
            return


# the function to draw the screen
def gui():
    global dataref_m, dataref_b, indices_b, indices_t, vals_b, clear_b, loops_b
    global hideshow_m, from_b, to_b, up_b, down_b, delete_b, addhs_b
    global cancel_b, apply_b

    dataref_m=[]
    dataref_b=[]
    indices_b=[]
    indices_t=[]
    vals_b=[]
    clear_b=None
    loops_b=[]
    hideshow_m=[]
    from_b=[]
    to_b=[]
    up_b=[]
    down_b=[]
    delete_b=[]
    addhs_b=None
    cancel_b=None
    apply_b=None

    # Default theme
    text   =[  0,   0,   0, 255]
    text_hi=[255, 255, 255, 255]
    header =[165, 165, 165, 255]
    panel  =[255, 255, 255,  40]
    back   =[180, 180, 180, 255]
    error  =[255,  80,  80, 255]	# where's the theme value for this?

    # Actual theme
    if Blender.Get('version') >= 235:
        theme=Blender.Window.Theme.Get()
        if theme:
            theme=theme[0]
            space=theme.get('buts')
            text=theme.get('ui').text
            text_hi=space.text_hi
            header=space.header
            header=[max(header[0]-30, 0),	# 30 appears to be hard coded
                    max(header[1]-30, 0),
                    max(header[2]-30, 0),
                    header[3]]
            panel=space.panel
            back=space.back

    size=BGL.Buffer(BGL.GL_FLOAT, 4)
    BGL.glGetFloatv(BGL.GL_SCISSOR_BOX, size)
    size=size.list
    x=int(size[2])
    y=int(size[3])

    BGL.glEnable(BGL.GL_BLEND)
    BGL.glBlendFunc(BGL.GL_SRC_ALPHA, BGL.GL_ONE_MINUS_SRC_ALPHA)
    BGL.glClearColor(float(back[0])/255, float(back[1])/255, float(back[2])/255, 1)
    BGL.glClear(BGL.GL_COLOR_BUFFER_BIT)

    for boneno in range(bonecount):
        eventbase=boneno*EVENTMAX
        if vertical:
            xoff=PANELPAD+PANELINDENT
            yoff=y-(170+(CONTROLSIZE-1)*framecount)*boneno
        else:
            xoff=PANELPAD+boneno*(PANELWIDTH+PANELPAD)+PANELINDENT
            yoff=y
        BGL.glColor4ub(*header)
        BGL.glRectd(xoff-PANELINDENT, yoff-PANELTOP, xoff-PANELINDENT+PANELWIDTH, yoff-PANELTOP-PANELHEAD)
        BGL.glColor4ub(*panel)
        BGL.glRectd(xoff-PANELINDENT, yoff-PANELTOP-PANELHEAD, xoff-PANELINDENT+PANELWIDTH, yoff-170-(CONTROLSIZE-1)*framecount)

        txt='parent bone'
        if boneno: txt='grand'+txt
        txt='great-'*(boneno-1)+txt
        txt=txt[0].upper()+txt[1:]
        BGL.glColor4ub(*text_hi)
        BGL.glRasterPos2d(xoff, yoff-23)
        Draw.Text(txt)

        Draw.Label("Dataref:", xoff-4, yoff-54, 100, CONTROLSIZE)
        BGL.glColor4ub(*error)	# For errors
        (valid,mbutton,bbutton,ibutton,tbutton)=drawdataref(datarefs, indices, eventbase, boneno, xoff-4, yoff-80)
        dataref_m.append(mbutton)
        dataref_b.append(bbutton)
        indices_b.append(ibutton)
        indices_t.append(tbutton)

        vals_b.append([])
        if valid:
            # is a valid or custom dataref
            Draw.Label("Dataref values:", xoff-4, yoff-132, 150, CONTROLSIZE)
            for i in range(framecount):
                Draw.Label("Frame #%d:" % (i+1), xoff-4+CONTROLSIZE, yoff-152-(CONTROLSIZE-1)*i, 100, CONTROLSIZE)
                if i>1:
                    v9='v9: '
                else:
                    v9=''
                vals_b[-1].append(Draw.Number('', i+VALS_B+eventbase, xoff+104, yoff-152-(CONTROLSIZE-1)*i, 80, CONTROLSIZE, vals[boneno][i], -999999, 999999, v9+'The dataref value that corresponds to the pose in frame %d' % (i+1)))
            # How do you delete a keyframe in Python?
            #if boneno==0 and framecount>2:
            #    clear_b=Draw.Button('Delete', CLEAR_B+eventbase, xoff+208, yoff-158-26*i, 80, CONTROLSIZE, 'Clear all poses for all bones from frame %d' % framecount)
            Draw.Label("Loop:", xoff-4+CONTROLSIZE, yoff-160-(CONTROLSIZE-1)*framecount, 100, CONTROLSIZE)
            loops_b.append(Draw.Number('', LOOPS_B+eventbase, xoff+104, yoff-160-(CONTROLSIZE-1)*framecount, 80, CONTROLSIZE, loops[boneno], -999999, 999999, 'v9: The animation will loop back to frame 1 when the dataref value exceeds this number. Enter 0 for no loop.'))
        else:
            loops_b.append(None)

    if vertical:
        xoff=PANELPAD+PANELINDENT
        yoff=y-(170+(CONTROLSIZE-1)*framecount)*bonecount
    else:
        xoff=PANELPAD+bonecount*(PANELWIDTH+PANELPAD)+PANELINDENT
        yoff=y
    BGL.glColor4ub(*header)
    BGL.glRectd(xoff-PANELINDENT, yoff-PANELTOP, xoff-PANELINDENT+PANELWIDTH, yoff-PANELTOP-PANELHEAD)
    BGL.glColor4ub(*panel)
    BGL.glRectd(xoff-PANELINDENT, yoff-PANELTOP-PANELHEAD, xoff-PANELINDENT+PANELWIDTH, yoff-64-len(hideshow)*82)

    BGL.glColor4ub(*text_hi)
    BGL.glRasterPos2d(xoff, yoff-23)
    Draw.Text("Hide/Show for all children of %s" % armature.name)

    for hs in range(len(hideshow)):
        eventbase=(bonecount+hs)*EVENTMAX
        BGL.glColor4ub(*panel)
        BGL.glRectd(xoff-4, yoff-PANELTOP-PANELHEAD-4-hs*82, xoff-13+PANELWIDTH, yoff-PANELTOP-101-hs*82)
        BGL.glColor4ub(*error)	# For errors
        (valid,mbutton,bbutton,ibutton,tbutton)=drawdataref(hideshow, hideshowindices, eventbase, hs, xoff-4, yoff-54-hs*82)
        dataref_m.append(mbutton)
        dataref_b.append(bbutton)
        indices_b.append(ibutton)
        indices_t.append(tbutton)
        if hs:
            up_b.append(Draw.Button('^', UP_B+eventbase, xoff+217, yoff-80-hs*82, CONTROLSIZE, CONTROLSIZE, 'Move this Hide or Show entry up'))
        else:
            up_b.append(None)
        if hs!=len(hideshow)-1:
            down_b.append(Draw.Button('v', DOWN_B+eventbase, xoff+237, yoff-80-hs*82, CONTROLSIZE, CONTROLSIZE, 'Move this Hide or Show entry down'))
        else:
            down_b.append(None)
        delete_b.append(Draw.Button('X', DELETE_B+eventbase, xoff+267, yoff-80-hs*82, CONTROLSIZE, CONTROLSIZE, 'Delete this Hide or Show entry'))
        if valid:
            # is a valid or custom dataref
            hideshow_m.append(Draw.Menu('Hide%x0|Show%x1', HIDEORSHOW_M+eventbase, xoff, yoff-106-hs*82, 62, CONTROLSIZE, hideorshow[hs], 'Choose Hide or Show'))
            Draw.Label("when", xoff+63, yoff-106-hs*82, 60, CONTROLSIZE)
            from_b.append(Draw.Number('', FROM_B+eventbase, xoff+104, yoff-106-hs*82, 80, CONTROLSIZE, hideshowfrom[hs], -999999, 999999, 'The dataref value above which the animation will be hidden or shown'))
            Draw.Label("to", xoff+187, yoff-106-hs*82, 60, CONTROLSIZE)
            to_b.append(Draw.Number('', TO_B+eventbase, xoff+207, yoff-106-hs*82, 80, CONTROLSIZE, hideshowto[hs], -999999, 999999, 'The dataref value below which the animation will be hidden or shown'))
        else:
            hideshow_m.append(None)
            from_b.append(None)
            to_b.append(None)
    addhs_b=Draw.Button('Add New', ADD_B+bonecount*EVENTMAX, xoff+217, yoff-54-len(hideshow)*82, 70, CONTROLSIZE, 'Add a new Hide or Show entry')

    if vertical:
        xoff=PANELPAD
        yoff=y-(170+(CONTROLSIZE-1)*framecount)*bonecount -64-len(hideshow)*82
    else:
        xoff=PANELPAD+(bonecount+1)*(PANELWIDTH+PANELPAD)
        yoff=y
    apply_b=Draw.Button('Apply', APPLY_B+bonecount*EVENTMAX, xoff, yoff-PANELTOP-CONTROLSIZE*2, 80, CONTROLSIZE*2, 'Apply these settings', apply)
    if vertical:
        cancel_b=Draw.Button('Cancel', CANCEL_B+bonecount*EVENTMAX, xoff+80+PANELPAD, yoff-PANELTOP-CONTROLSIZE*2, 80, CONTROLSIZE*2, 'Retain existing settings')
    else:
        cancel_b=Draw.Button('Cancel', CANCEL_B+bonecount*EVENTMAX, xoff, yoff-PANELTOP-CONTROLSIZE*4-PANELPAD, 80, CONTROLSIZE*2, 'Retain existing settings')



def drawdataref(datarefs, indices, eventbase, boneno, x, y):

    dataref=datarefs[boneno]
    valid=True

    mbutton=Draw.Menu('sim/%t|'+'/...|'.join(firstlevel)+'/...', DONTCARE+eventbase, x+4, y, CONTROLSIZE, CONTROLSIZE, -1, 'Pick the dataref from a list', datarefmenucallback)
    bbutton=Draw.String('', DATAREF_B+eventbase, x+4+CONTROLSIZE, y, PANELWIDTH-2*PANELINDENT-CONTROLSIZE, CONTROLSIZE, dataref, 100, 'Full name of the dataref used to animate this object')
    
    ibutton=None
    tbutton=None
    ref=dataref.split('/')
    if len(ref)<=1 or ref[0]=='sim':
        try:
            thing=hierarchy
            for i in range(len(ref)):
                thing=thing[ref[i]]
            n=thing+0	# check is a leaf - ie numeric
            if not n:
                BGL.glRasterPos2d(x+4, y-21)
                Draw.Text("This dataref can't be used for animation")
                valid=False
            elif n==1:
                indices[boneno]=None
            else:
                if indices[boneno]==None or indices[boneno]>=n:
                    indices[boneno]=0
                Draw.Label("Part number:", x, y-26, 120, CONTROLSIZE)
                ibutton=Draw.Number('', INDICES_B+eventbase, x+108, y-26, 50, CONTROLSIZE, indices[boneno], 0, n-1, 'The part number / array index')
        except:
            BGL.glRasterPos2d(x+4, y-21)
            Draw.Text("This is not a valid dataref")
            valid=False
    else:
        if indices[boneno]!=None:
            val=1
        else:
            val=0
        tbutton=Draw.Toggle('Part number', INDICES_T+eventbase, x+4, y-26, 104, CONTROLSIZE, val, 'Whether this is an array dataref')
        if val:
            ibutton=Draw.Number('', INDICES_B+eventbase, x+108, y-26, 50, CONTROLSIZE, indices[boneno], 0, 729, 'The part number / array index')

    return (valid, mbutton,bbutton,ibutton,tbutton)



if __name__=='__main__' and getparents():
    vertical=(Window.GetAreaSize()[1]>Window.GetAreaSize()[0])
    action=armature.getAction()
    if action:
        f=action.getFrameNumbers()
        f.sort()
        for framecount in range(len(f)):
            if f[framecount]!=framecount+1:
                break
        else:
            framecount+=1
        if framecount<2: framecount=2

    bonecount=len(bones)
    # Get values for other bones in armature too
    for bone in armature.getData().bones.values():
        if bone not in bones:
            bones.append(bone)
    
    for bone in bones:
        dataref=bone.name.split('.')[0]

        # split off index
        index=None
        l=dataref.find('[')
        if l!=-1:
            i=dataref[l+1:-1]
            if dataref[-1]==']':
                try:
                    index=int(i)
                except:
                    pass
            dataref=dataref[:l]

        (dataref,v,l)=getvals(dataref, index)
        datarefs.append(dataref)
        indices.append(index)
        vals.append(v)
        loops.append(l)

    gethideshow()
    
    #print armature, bones, bonecount, framecount, datarefs, indices, vals, loops
    #print hideshow, hideorshow, hideshowindices, hideshowfrom, hideshowto

    Draw.Register (gui, event, bevent)
