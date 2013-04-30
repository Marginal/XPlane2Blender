@rem Installation script for Windows NT/2000/XP/Win7
@echo off

echo Installing Blender scripts . . .

cd /d "%~dp0"

set DIRS=
if defined HOME set DIRS=%DIRS% "%HOME%\.blender\scripts"

rem Try to locate Blender
set FTYPE=
for /f "tokens=2 delims==" %%I in ('assoc .blend') do set FTYPE=%%I
if not defined FTYPE goto noassoc
set BDIR=
for /f "tokens=2* delims==" %%I in ('ftype %FTYPE%') do set BDIR=%%~dpI
if defined BDIR set DIRS=%DIRS% "%BDIR%.blender\scripts"
:noassoc

set DIRS=%DIRS% "%ProgramFiles%\Blender Foundation\Blender\.blender\scripts" "%ProgramFiles(x86)%\Blender Foundation\Blender\.blender\scripts" "%APPDATA%\Blender Foundation\Blender\.blender\scripts"

rem Find target script directory
for %%D in (%DIRS%) do if exist "%%~D\" (set DESTDIR=%%~D& goto delold)

:destfail
echo.
echo Failed to find the correct location for the scripts !!!
goto end

:delold
rem Remove old files
set FILES=..\Bpymenus helpXPlane.py uvCopyPaste.py uvFixupACF.py uvResize.py XPlaneAnimObject.py XPlaneExport.py XPlaneExport.pyc XPlaneExport7.py XPlaneExport8.py XPlaneExportCSL.py XPlaneExportBodies.py XPlaneImport.py XPlaneImport.pyc XPlaneImportMDL.py XPlaneImportPlane.py XPlaneImportBodies.py XPlanePanelRegions.py XPlaneUtils.py XPlaneUtils.pyc XPlaneHelp.py XPlaneACF.py XPlaneACF.pyc XPlane2Blender.html XPlaneImportPlane.html XPlaneReadme.txt DataRefs.txt
for %%I in (%FILES%) do if exist "%DESTDIR%\%%I" del "%DESTDIR%\%%I" >nul: 2>&1

:copy
set FILES=DataRefs.txt ReadMe-XPlane2Blender.html XPlaneAG.py XPlaneAnimObject.py XPlaneAnnotate.py XPlaneExport.py XPlaneExport7.py XPlaneExport8.py XPlaneExport8_ManipOptionsInterpreter.py XPlaneExport8_util.py XPlaneExportCSL.py XPlaneFacade.py XPlaneHelp.py XPlaneImport.py XPlaneImportMDL.py XPlaneImportPlane.py XPlaneImport_util.py XPlaneLib.py XPlaneMacros.py XPlaneMultiObj.py XPlanePanelRegions.py XPlaneUtils.py uvFixupACF.py uvResize.py
for %%I in (%FILES%) do if not exist "%%I" goto srcfail
for %%I in (%FILES%) do copy /v /y %%I "%DESTDIR%\" >nul:
for %%I in (%FILES%) do if not exist "%DESTDIR%\%%I" goto copyfail
echo.
echo Installed scripts in folder
echo   %DESTDIR%
goto end

:copyfail
echo.
echo Failed to install scripts in folder
echo   %DESTDIR% !!!
echo.
echo Try running this installer as Administrator.
goto end

:srcfail
echo.
echo Failed to install scripts.
echo.
echo Did you extract all of the contents of the zip file?
goto end

:end
echo.
pause
:reallyend
