@ECHO OFF

ECHO CMU CAPSTONE - INJURY PREDICT - Version Fall 2021
ECHO ==================================================
ECHO This script will perform a clean install of the application.
ECHO Before running this batch file, MS SQL sever setting and setting.py modicication are necessary.
SET /P _continue= Are you sure you want to continue?[y/n]
IF "%_continue%"=="y" GOTO :do_work
GOTO :end
:do_work
:: Get to right directory
cd injury_predict_web

:: Create virtual enviornment if it doesn't exist
if exist pyenv\ (
	ECHO Virtual environment already created
) else (
	ECHO Creating virtual environment
	python -m venv pyenv
	ECHO Virtual enviornment 'pyenv' created
)
:: Activate virtual enviornment
ECHO Activating virtual environment
CALL ./pyenv/Scripts/activate

:: Install requirements
ECHO Installing requirements
pip install -r requirements.txt
pip install pystan==2.17.1.0
pip install fbprophet==0.6
pip install django mssql-django
pip install wfastcgi

:: Create migrations
ECHO Creating new migrations
python manage.py makemigrations

:: Migrate
ECHO Migrating
python manage.py migrate

:: Initialize DB
ECHO Initializing database
python manage.py initialize_db

:: Create superuser
ECHO Creating superuser
python manage.py createsuperuser

:: Setup IIS
ECHO Enabling wfastcgi
call .\pyenv\Scripts\wfastcgi-enable
ECHO unlocking handlers
call %windir%\system32\inetsrv\appcmd unlock config -section:system.webServer/handlers

cd ..
deactivate
ECHO Finished installing.

:end