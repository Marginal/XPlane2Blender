@rem Installation script for Windows NT/2000/XP
@echo off
echo Installing Blender scripts . . .
echo.

:prog
if "%ProgramFiles%"=="" goto appdata
set DESTDIR=%ProgramFiles%\Blender Foundation\Blender\.blender\scripts\
if not exist "%DESTDIR%" goto appdata
goto copy

:appdata
if "%USERPROFILE%"=="" goto home
set DESTDIR=%USERPROFILE%\Application Data\Blender Foundation\Blender\.blender\scripts\
if not exist "%DESTDIR%" goto home
goto copy

:home
if "%HOME%"=="" goto destfail
set DESTDIR=%HOME%\.blender\scripts\
if not exist "%DESTDIR%" goto destfail
goto copy

:destfail
echo Failed to find appropriate location for Blender scripts !!!
goto end

:copy
if exist "%DESTDIR%..\Bpymenus"         del "%DESTDIR%..\Bpymenus"
if exist "%DESTDIR%XPlaneReadme.txt"    del "%DESTDIR%XPlaneReadme.txt"
if exist "%DESTDIR%XPlane2Blender.html" del "%DESTDIR%XPlane2Blender.html"
if exist "%DESTDIR%XPlaneExport.py"     del "%DESTDIR%XPlaneExport.py"
if exist "%DESTDIR%XPlaneImport.py"     del "%DESTDIR%XPlaneImport.py"
copy /v /y XPlane2Blender.html              "%DESTDIR%" >nul:
copy /v /y XPlaneExport.py                  "%DESTDIR%" >nul:
copy /v /y XPlaneImport.py                  "%DESTDIR%" >nul:
if not exist "%DESTDIR%XPlane2Blender.html" goto copyfail
if not exist "%DESTDIR%XPlaneExport.py"     goto copyfail
if not exist "%DESTDIR%XPlaneImport.py"     goto copyfail
echo Installation successful.
goto end

:copyfail
echo Failed to install scripts in "%DESTDIR%" !!!
goto end

:end
echo.
pause
