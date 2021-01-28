release: rm -rf node_modules/ pipeline/ && python manage.py migrate
web: gunicorn PyRIGS.wsgi --log-file -
