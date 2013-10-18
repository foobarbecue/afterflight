afterflight
===========

 An application for analysis of UAV log and video.

 Introductory video with quickstart is at http://youtu.be/wdeeGyvHJ9c .

Installing the release version
**********************************

Installing the development version
**********************************

#. make sure you have scipy installed on your system. On ubuntu, that means doing: ``sudo apt-get install scipy``. Once scipy 0.13 is released, this step will no longer be necessary because setup.py will be able to install it properly.

#. Clone the afterflight repository to with ``git clone https://github.com/foobarbecue/afterflight.git``

#. In the directory that is created (called afterflight unless you specified otherwise), run ``pip -r requirements.txt``. This will install the remaining dependancies.

#. Create ``settings_local.py`` based on the example ``settings_local_example.py``. Usually you can just run ``cp settings_local_example.py settings_local.py``, but if you want to use a database other than sqlite (such as postgres) this is where your database access information will go.

#. Create your database tables by running ``python afterflight/manage.py syncdb``. This will also add a default site for the django sites framework, which is required for the authentication system.

#. Run a local development server: ``python afterflight/manage.py runserver``. By default this will run at http://localhost:8000 , so you can point your browser there to get started.

#. If you want to run this on a public server, follow https://docs.djangoproject.com/en/1.5/howto/deployment/ .