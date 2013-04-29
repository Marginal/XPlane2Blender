
import sys
import time
import Blender
from Blender import Armature, Mesh, Lamp, Image, Draw, Window
from Blender.Mathutils import Matrix, RotationMatrix, TranslationMatrix, MatMultVec, Vector, Quaternion, Euler
from XPlaneUtils import Vertex, UV, MatrixrotationOnly, getDatarefs, PanelRegionHandler, getManipulators, make_short_name
from XPlaneExport import ExportError

import string






def formatManipulator(manipulator):
	""" Return a string representing a manipular structure.
	Keyword arguments:
	manipulator -- the manipulator dictionary

	"""
	if manipulator == None:
		return 'ATTR_manip_none'

	keys = sorted(manipulator.keys())
	manipulator_str = manipulator['99@manipulator-name']
	for key in keys:
		if key == '99@manipulator-name':
			break

		manipulator_str += '\t'
		#print 'key=', key
		data = manipulator[key]

		if type(data).__name__ == 'str':
			manipulator_str += data.strip()

		if type(data).__name__ == 'float':
			manipulator_str += '%6.2f' % data

		if type(data).__name__ == 'int':
			manipulator_str += '%d' % data

	return manipulator_str



def getmanipulator(object):

	manipulator = 'ATTR_manip_none'
	props = object.getAllProperties()

	for prop in props:
		if prop.name == 'manipulator_type':
			manipulator = prop.data

	if manipulator == 'ATTR_manip_none':
		return None

	manipulator_dict,cursorList = getManipulators()
	keys = sorted(manipulator_dict[manipulator].keys())
	for prop in props:
		if prop.name.startswith(manipulator):
			tmp = prop.name.split('_')
			key = tmp[len(tmp)-1]

			for dict_key in keys:
				if dict_key.find(key) > 0:
					key = dict_key
					break

			manipulator_dict[manipulator][key] = prop.data

	manipulator_dict[manipulator]['99@manipulator-name'] = manipulator
	return manipulator_dict[manipulator]


def anim_decode(obj):
	m = getmanipulator(obj)
	if m == None:
		if obj.parent == None:
			return ""
		if obj.getType()=='Mesh':
			return anim_decode(obj.parent)
		return ""

	return formatManipulator(m)



def decode(obj):
	properties = obj.getAllProperties()
	objname = obj.name

	#setup default manipulator attribute values
	manip_iscommand_br	= False
	manip_is_push_tk	= False
	manip_is_toggle_tk	= False
	manip_command_br	= "<command>"
	manip_cursor_br 	= "<cursor>"
	manip_x_br 			= "<x>"
	manip_y_br 			= "<y>"
	manip_z_br 			= "<z>"
	manip_val1_br 		= "<val1>"
	manip_val2_br 		= "<val2>"
	manip_dref_br 		= "<dref>"
	manip_tooltip_br 	= "<tooltip>"
	
	manip_bone_name_br	= "" #--leave this blank by default, if its not blank the code will try and find the bone name
		
	for prop in properties:
		if( prop.name == "mnp_iscommand" ): 	manip_iscommand_br	= prop.data #--expects a boolean value
		if( prop.name == "mnp_command" ):		manip_command_br	= prop.data.strip()
		if( prop.name == "mnp_cursor" ): 		manip_cursor_br 	= prop.data.strip()
		if( prop.name == "mnp_dref" ): 			manip_dref_br 		= prop.data.strip()
		if( prop.name == "mnp_tooltip" ): 		manip_tooltip_br	= prop.data.strip()
		if( prop.name == "mnp_bone" ): 			manip_bone_name_br 	= prop.data.strip()
		if( prop.name == "mnp_v1" ): 			manip_val1_br 		= str(prop.data)
		if( prop.name == "mnp_v2" ): 			manip_val2_br 		= str(prop.data)
		if( prop.name == "mnp_is_push" ):		manip_is_push_tk	= prop.data
		if( prop.name == "mnp_is_toggle" ):		manip_is_toggle_tk	= prop.data

	# BR's weird scheme: if there is NO mnp_bone there is no manip, get out.  But the magic
	# bone names arm_ are place-holders - they're not REAL armatures, it's just a place-holder
	# to make the export work.
	
	if manip_bone_name_br == "":
		return anim_decode(obj)
	
	if( manip_bone_name_br != "" and manip_bone_name_br != "arm_" ):
		obj_manip_armature_br = Blender.Object.Get( manip_bone_name_br )
		if( obj_manip_armature_br != None ):
			obj_manip_armature_data_br = obj_manip_armature_br.getData()
			obj_manip_bone_br = obj_manip_armature_data_br.bones.values()[0]
			
			vec_tail = obj_manip_bone_br.tail['ARMATURESPACE']
			vec_arm = [obj_manip_armature_br.LocX, obj_manip_armature_br.LocY, obj_manip_armature_br.LocZ]
			
			#blender Y = x-plane Z, transpose
			manip_x_br = str( round(vec_tail[0],3) )
			manip_y_br = str( round(vec_tail[2],3) )
			manip_z_br = str( round(-vec_tail[1],3) ) #note: value is inverted.
			
			#self.file.write( str( vec_tail ) + "\n" )
			#self.file.write( str( vec_arm ) + "\n" )
	
	
	
	data = ""
	
		
	if( manip_iscommand_br ):
		#wiki def: ATTR_manip_command <cursor> <command> <tooltip>
		data = ("ATTR_manip_command %s %s %s" 
												%(manip_cursor_br,
												manip_command_br, 
												manip_tooltip_br))
	elif( manip_is_push_tk):
		data = ("ATTR_manip_push %s %s %s %s"
												%(manip_cursor_br,
												manip_val1_br,
												manip_val2_br,
												manip_dref_br))
	elif( manip_is_toggle_tk):
		data = ("ATTR_manip_toggle %s %s %s %s"
												%(manip_cursor_br,
												manip_val1_br,
												manip_val2_br,
												manip_dref_br))
	
	else:
		#wiki def: ATTR_manip_drag_axis <cursor> <x> <y> <z> <value1> < value2> <dataref> <tooltip>
		data = ("ATTR_manip_drag_axis %s %s %s %s %s %s %s %s" 
												%(manip_cursor_br,
												manip_x_br,
												manip_y_br,
												manip_z_br,
												manip_val1_br,
												manip_val2_br, 
												manip_dref_br, 
												manip_tooltip_br))
	
	
	if data.find("<x>") != -1:
		print properties
		raise ExportError("%s: Manipulator '%s' is incomplete but was still exported." % (objname, data))
	
	return data
	 
