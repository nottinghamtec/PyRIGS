release: node node_modules/gulp/bin/gulp build && python.manage.py collectstatic && python manage.py migrate
web: gunicorn PyRIGS.wsgi --log-file -
