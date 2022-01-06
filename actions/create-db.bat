@echo off
path=%path%;D:\MTGame\game\runtime\MySQL51\bin

echo start create game database: %1
set dbname=octgame%1
@REM echo %dbname%
@REM echo %~p0

echo show databases like '%dbname%'; > %~p0list-db.sql
mysql -uroot -p123456 -P3310 < %~p0list-db.sql | findstr %dbname% && echo database already exists! && goto finish

echo create database %dbname%; > %~p0create-db.sql
mysql -uroot -p123456 -P3310 < %~p0create-db.sql
mysql -uroot -p123456 -P3310 %dbname% < %~p0octgame.sql
del %~p0create-db.sql /q

:finish
del %~p0list-db.sql /q

@REM pause