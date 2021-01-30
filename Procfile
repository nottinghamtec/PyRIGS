release: rm -rf pipeline/ && python manage.py migrate
web: gunicorn PyRIGS.wsgi --log-file -
