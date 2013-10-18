   #Copyright 2013 Aaron Curtis

   #Licensed under the Apache License, Version 2.0 (the "License");
   #you may not use this file except in compliance with the License.
   #You may obtain a copy of the License at

       #http://www.apache.org/licenses/LICENSE-2.0

   #Unless required by applicable law or agreed to in writing, software
   #distributed under the License is distributed on an "AS IS" BASIS,
   #WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   #See the License for the specific language governing permissions and
   #limitations under the License.

from distutils.core import setup
from setuptools import find_packages

REQUIREMENTS = [i.strip() for i in open("requirements.txt").readlines()]

setup(
    name='afterflight',
    version='0.2',
    author=u'Aaron Curtis',
    author_email='aaron@aarongcurtis.com',
    packages=find_packages(),
    url='http://github.com/foobarbecue/afterflight',
    license='Apache 2.0, see LICENCE.txt',
    description='Add maps and photos from the French National Geographic' + \
                ' Institute to GeoDjango',
    long_description=open('README.rst').read(),
    zip_safe=False,
    install_requires=REQUIREMENTS    
)