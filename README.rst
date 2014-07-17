afterflight
===========

 An application for analysis of UAV log and video.
 
 Development server is live at http://afterflight.foobarbecue.com .

 Introductory video with quickstart is at http://youtu.be/8XBCBC2oJ70 .

Installing the development version
**********************************

#. make sure you have scipy and matplotlib installed on your system. On ubuntu, that means doing: ``sudo apt-get install scipy matlplotlib``. These packages often do not install correctly through the python package system.

#. Clone the afterflight repository to with ``git clone https://github.com/foobarbecue/afterflight.git`` . From now on 

#. In the directory that is created (called afterflight unless you specified otherwise), run ``pip install -r ./afterflight/requirements.txt``. This will install the remaining dependancies.

#. Create ``settings_local.py`` based on the example ``settings_local_example.py``. Usually you can just run ``cp settings_local_example.py settings_local.py``, but if you want to use a database other than sqlite (such as postgres) this is where your database access information will go.

#. Create your database tables by running ``python afterflight/manage.py syncdb``.

#. Run a local development server: ``cd afterflight && python ./manage.py runserver``. By default this will run at http://localhost:8000 , so you can point your browser there to get started.

#. If you want to run this on a public server, follow https://docs.djangoproject.com/en/1.5/howto/deployment/ .

#. If you want to enable login using providers such as google and facebook, you will need to add credentials for those services as explained here https://github.com/pennersr/django-allauth (afterflight uses django-allauth for authentication)

Installing the release version
**********************************

Doing it this way is a work in progress and probably not yet functional.

#. make sure you have scipy and matplotlib installed on your system. On ubuntu, that means doing: ``sudo apt-get install scipy matlplotlib``. These packages often do not install correctly through the python package system.

#. pip install afterflight

#. Create ``settings_local.py`` based on the example ``settings_local_example.py``. Usually you can just run ``cp settings_local_example.py settings_local.py``, but if you want to use a database other than sqlite (such as postgres) this is where your database access information will go.

#. Create your database tables by running ``python afterflight/manage.py syncdb``.

#. Run a local development server: ``python afterflight/manage.py runserver``. By default this will run at http://localhost:8000 , so you can point your browser there to get started.

#. If you want to run this on a public server, follow https://docs.djangoproject.com/en/1.5/howto/deployment/ .

#. If you want to enable login using providers such as google and facebook, you will need to add credentials for those services as explained here https://github.com/pennersr/django-allauth (afterflight uses django-allauth for authentication)
 
