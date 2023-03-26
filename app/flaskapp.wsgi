#!/usr/bin/python
import sys, os
import logging
import site

python_home = '/var/www/html/..../virtualenv'

activate_this = python_home + '/bin/activate_this.py'
exec(open(activate_this).read(), {'__file__': activate_this})

logging.basicConfig(stream=sys.stderr)
# sys.path.insert(0, 'var/www/html/..........

from app import app as application
