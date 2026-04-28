@echo off
cd /d "%~dp0"
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" > nul 2>&1
cl /EHsc main.cpp /Fehello_world.exe > compile_out.txt 2>&1
echo Exit code: %ERRORLEVEL%
type compile_out.txt
