@echo off
path=%path%;D:\部署\MySQL51\bin

echo start create game database: %1
set dbname=octgame%1
@REM echo %dbname%
@REM echo %~p0

echo show databases; > %~p0list-db.sql
mysql -uroot -psifuduan1 -P3306 < %~p0list-db.sql | findstr %dbname% && echo database already exists! && goto finish

echo create database %dbname%; > %~p0create-db.sql
mysql -uroot -psifuduan1 -P3306 < %~p0create-db.sql
mysql -uroot -psifuduan1 -P3306 %dbname% < D:\部署\sql\octgame开服原始.sql
del %~p0create-db.sql /q

:finish
del %~p0list-db.sql /q

@REM pause