set RUNTIME=d:\LegendGame\game\runtime\

for /f "tokens=4" %%i in ('netstat -a -n^|findstr "3310"^|findstr "LISTENING"') do set val=%%i
if not "%val%" == "LISTENING" (
    start /i %RUNTIME%MySQL51\bin\start.bat
    timeout 1 /NOBREAK
)

for /f "tokens=2" %%i in ('tasklist^|findstr "GameServer.exe"') do exit 0 /f
timeout 1 /NOBREAK

cd %RUNTIME%gameserver\

del /q GameServer.exe
copy GameServer.exe.×îÐÂ°æ±¾ GameServer.exe

@REM start /min gameserver /console && exit
start gameserver /console && exit 0