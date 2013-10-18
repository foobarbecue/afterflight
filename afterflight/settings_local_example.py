

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'af_db.db'
    }
}

# This is for django-debug-toolbar which is an optional
# development tool
INTERNAL_IPS = ('127.0.0.1',)

#Add optional dependencies
DEBUG_APPS = ('debug_toolbar',)

DEBUG = True
TEMPLATE_DEBUG = DEBUG