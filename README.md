# TEC PA & Lighting - PyRIGS #
[![Build Status](https://travis-ci.org/nottinghamtec/PyRIGS.svg)](https://travis-ci.org/nottinghamtec/PyRIGS)
[![Coverage Status](https://coveralls.io/repos/github/nottinghamtec/PyRIGS/badge.svg)](https://coveralls.io/github/nottinghamtec/PyRIGS)

Welcome to TEC PA & Lightings PyRIGS program. This is a reimplementation of the existing Rig Information Gathering System (RIGS) that was developed using Ruby on Rails.

The purpose of this project is to make the system more compatible and easier to understand such that should future changes be needed they can be made without having to understand the intricacies of Rails.

### What is this repository for? ###
When a significant feature is developed on a branch, raise a pull request and it can be reviewed before being put into production.

Most of the documents here assume a basic knowledge of how Python and Django work (hint, if I don't say something, Google it, you will find 10000's of answers). The documentation is purely to be specific to TEC's application of the framework.

### Editing ###
It is recommended that you use the PyCharm IDE by JetBrains. Whilst other editors are available, this is the best for integration with Django as it can automatically manage all the pesky admin commands that frequently need running, as well as nice integration with git.

For the more experienced developer/somebody who doesn't want a full IDE and wants it to open in less than the age of the universe, I can strongly recommend [Sublime Text](http://www.sublimetext.com/). It has a bit of a steeper learning curve, and won't manage anything Django/git related out of the box, but once you get the hang of it is by far the fastest and most powerful editor I have used (for any type of project).

Please contact TJP for details on how to acquire these.

### Python Environment ###
Whilst the Python version used is not critical to the running of the application, using the same version usually helps avoid a lot of issues. Orginally written with the C implementation of Python 2 (CPython 2, specifically the Python 2.7 standard), the application now runs in Python 3.

Once you have your Python distribution installed, go ahead an follow the steps to set up a virtualenv, which will isolate the project from the system environment.

#### PyCharm ####
If you are using the prefered PyCharm IDE, then this should be quite easy.

1. Select "File/Settings" -> "Project Interpreter"
2. Click the small cog in the top right
3. Select "Create VirtualEnv"
4. Enter a name and a location. This doesn't matter where, just make sure it makes sense and you remember it incase you need it later (I recommend calling it "pyrigs" in "~/.virtualenvs/pyrigs")
5. Select the base interpreter to your Python 3 base interpreter (Python 2 will work, just be careful)
6. Click OK, you *don't* want to inherit global packages or make it available to all projects.
7. Open a file such as manage.py. PyCharm should winge that dependances aren't installed. This might take a while to register, but give it change. When it does, click the button to install them and let it do it's thing. If for some reason PyCharm should decide that it doesn't want to help you here, see below for the console instructions on how to do this manually.

To run the Django application follow these steps

1. Select "Run/Edit Configurations"
2. Create a new "Django server", give it a sensible name for when you need it later.
3. You might need to set the interpreter to be your virtualenv.
4. Click "OK"
5. Run the application

#### Console Based ####
If you aren't using PyCharm, or want to use a console for some reason, this is really easy, there is even [virtualenvwrapper](https://virtualenvwrapper.readthedocs.org/en/latest/) to help things along. Simply run
```
virtualenv <dir>
```
Where dir is the directory you wish to create the virtualenv in.

Next activate the virtualenv.
```
Windows
<virtualenv_dir>/Scripts/activate.bat

Unix
source <virtualenv_dir>/bin/activate
```
Finally install the requirements using pip
```
cd <pyrigs project directory>
pip install -r requirements.txt
```
This might take a while, but be patient and you should then be ready to go.

To run the server under normal conditions when you are already in the virtualenv (see above)
```
python manage.py runserver
```
Please refer to Django documentation for a full list of options available here.

### Development using docker

```
docker build . -t pyrigs
docker run -it --rm -p=8000:8000 -v $(pwd):/app pyrigs
```

### Sample Data ###
Sample data is available to aid local development and user acceptance testing. To load this data into your local database, first ensure the database is empty:
```
python manage.py flush
```
Then load the sample data using the command:
```
python manage.py generateSampleData
```
4 user accounts are created for convenience:

|Username |Password |
|---------|---------|
|superuser|superuser|
|finance  |finance  |
|keyholder|keyholder|
|basic    |basic    |

### Testing ###
Tests are contained in 3 files. `RIGS/test_models.py` contains tests for logic within the data models. `RIGS/test_unit.py` contains "Live server" tests, using raw web requests. `RIGS/test_integration.py` contains user interface tests which take control of a web browser. For automated Travis tests, we use [Sauce Labs](https://saucelabs.com). When debugging locally, ensure that you have the latest version of Google Chrome installed, then install [chromedriver](https://sites.google.com/a/chromium.org/chromedriver/) and ensure it is on the `PATH`.

You can run the entire test suite, or you can run specific sections individually. For example, in order of specificity:

```
python manage.py test
python manage.py test RIGS.test_models
python manage.py test RIGS.test_models.EventTestCase
python manage.py test RIGS.test_models.EventTestCase.test_current_events

```

[![forthebadge](https://forthebadge.com/images/badges/built-with-resentment.svg)](https://forthebadge.com) [![forthebadge](https://forthebadge.com/images/badges/contains-technical-debt.svg)](https://forthebadge.com)
