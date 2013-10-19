# For deployment, change this to the hostname or IP address
# of your server
ALLOWED_HOSTS=['127.0.0.1']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'af_db.db'
    }
}

# This is for django-debug-toolbar which is an optional
# development tool
INTERNAL_IPS = ('127.0.0.1',)

# Add optional dependencies
DEBUG_APPS = ('debug_toolbar',)

DEBUG = False
TEMPLATE_DEBUG = DEBUG