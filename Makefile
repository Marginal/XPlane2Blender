TARGET=XPlane2Blender.zip

FILES=install.cmd install.command DataRefs.txt ReadMe-XPlane2Blender.html XPlaneAG.py XPlaneAnimObject.py XPlaneAnnotate.py XPlaneExport.py XPlaneExport7.py XPlaneExport8.py XPlaneExport8_ManipOptionsInterpreter.py XPlaneExport8_util.py XPlaneExportCSL.py XPlaneFacade.py XPlaneHelp.py XPlaneImport.py XPlaneImportMDL.py XPlaneImportPlane.py XPlaneImport_util.py XPlaneLib.py XPlaneMacros.py XPlaneMultiObj.py XPlanePanelRegions.py XPlaneUtils.py uvFixupACF.py uvResize.py

all:	$(TARGET)

clean:
	rm $(TARGET)

$(TARGET):	$(FILES)
	rm -f $(TARGET)
	zip -MM $(TARGET) $+
