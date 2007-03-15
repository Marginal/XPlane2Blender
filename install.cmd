@rem Installation script for Windows NT/2000/XP
@echo off

echo Installing Blender scripts . . .
echo.

rem Remove old versions
set FILES=..\Bpymenus helpXPlane.py uvCopyPaste.py uvResize.py XPlaneExport.py XPlaneExport.pyc XPlaneExport7.py XPlaneExport8.py XPlaneExportBodies.py XPlaneImport.py XPlaneImportPlane.py XPlaneImportBodies.py XPlaneUtils.py XPlaneUtils.pyc XPlaneACF.py XPlaneACF.pyc XPlane2Blender.html XPlaneImportPlane.html XPlaneReadme.txt
set DIRS="%HOME%\.blender\scripts" "%ProgramFiles%\Blender Foundation\Blender\.blender\scripts" "%USERPROFILE%\Application Data\Blender Foundation\Blender\.blender\scripts"
for %%D in (%DIRS%) do for %%I in (%FILES%) do if exist "%%~D\%%I" del "%%~D\%%I"

rem Find target script directories
for %%D in (%DIRS%) do if exist "%%~D\" (set DESTDIR=%%~D& goto copy)

:destfail
echo Failed to find appropriate location for Blender scripts !!!
goto end

:copy
set FILES=helpXPlane.py uvCopyPaste.py uvResize.py XPlaneExport.py XPlaneExport7.py XPlaneImport.py XPlaneImportPlane.py XPlaneUtils.py XPlaneACF.py XPlane2Blender.html
for %%I in (%FILES%) do copy /v /y %%I "%DESTDIR%\" >nul:
for %%I in (%FILES%) do if not exist "%DESTDIR%\%%I" goto copyfail
echo Installation successful.
goto end

:copyfail
echo Failed to install scripts in "%DESTDIR%" !!!
goto end

:end
echo.
pause
