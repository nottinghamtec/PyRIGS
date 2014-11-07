# TEC PA & Lighting - PyRIGS #
Welcome to TEC PA & Lightings PyRIGS program. This is a reiplmentation of the exisiting Rig Information Gathering System (RIGS) that was developed using Ruby on Rails.

The purpose of this project is to make the system more compatible and easier to understand such that should future changes be needed they can be made without having to understand the intricacies of Rails.

At this stage the project is very early on, and the main focus has been on getting a working system that can be tested and put into use ASAP due to the imminent failure of the existing system. Because of this, the documentation is still quite weak, but this should be fixed as time goes on.

### What is this repository for? ###
For the rapid development of the application for medium term deployment, the main branch is being used.
Once the application is deployed in a production environment, other branches should be used to properly stage edits and pushes of new features.

Most of the documents here assume a basic knowledge of how Python and Django work (hint, if I don't say something, Google it, you will find 10000's of answers). The documentation is purely to be specific to TEC's application of the framework.

### Editing ###
It is recommended that you use the PyCharm IDE by JetBrains. Whilst other editors are available, this is the best for integration with Django as it can automatically manage all the pesky admin commands that frequently need running, as well as nice integration with git.

Please contact TJP for details on how to acquire this.

### Python Environment ###
Whilst it is not critical to the success of the application, it has be written with **Python 3** in mind. It might have been tested with Python 2, but it is not guaranteed to work with it.

Once you have Python 3 installed, please follow steps to set up a virtualenv, which will isolate the project from your system environment.

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
If you aren't using PyCharm, or want to use a console for some reason, this is really easy. Simply run
```
virtualenv <dir>
```
Where dir is the directory you wish to create the virtualenv in. Watch this doesn't do something dumb like call the Python 2 version of it, else you will have that ballache to deal with later.
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