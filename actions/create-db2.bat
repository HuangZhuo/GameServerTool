echo off
path=%path%;D:\MTGame\game\runtime\MySQL51\bin

set id=%1

echo start create game+log database: %id%
if "%id%"=="" (
    echo empty args!
    exit
)

set gamedb=octgame%id%
set logdb=octlog%id%

set gamesql=%~p0octgame.sql
set logsql=%~p0octlog.sql

echo show databases like '%dbname%'; > %~p0list-db.sql
mysql -uroot -p123456 -P3310 < %~p0list-db.sql | findstr %gamedb% && echo %gamedb% already exists! || (
    echo create database %gamedb%; > %~p0create-db.sql
    mysql -uroot -p123456 -P3310 < %~p0create-db.sql
    mysql -uroot -p123456 -P3310 %gamedb% < %gamesql%
    echo %gamedb% is created!
)

echo show databases like '%logdb%'; > %~p0list-db.sql
mysql -uroot -p123456 -P3311 < %~p0list-db.sql | findstr %logdb% && echo %logdb% already exists! || (
    echo create database %logdb%; > %~p0create-db.sql
    mysql -uroot -p123456 -P3311 < %~p0create-db.sql
    mysql -uroot -p123456 -P3311 %logdb% < %logsql%
    echo %logdb% is created!
)

del %~p0list-db.sql /q
del %~p0create-db.sql /q
echo finished!
