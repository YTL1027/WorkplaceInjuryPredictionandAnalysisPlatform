@ECHO OFF

:: Get to right directory
cd injury_predict_web

:: Activate virtual enviornment
ECHO Activating virtual environment
CALL ./pyenv/Scripts/activate

:: Collect static
ECHO Collecting static files
python manage.py collectstatic

cd ..
deactivate
ECHO Finished collecting.
