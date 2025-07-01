from pathlib import Path
from setuptools import setup, find_packages


NAME = 'fraudit'
DESCRIPTION = ''
URL = ''
AUTHOR = 'Godwin AMEGAH'
EMAIL = 'komlan.godwin.amegah@gmail.com'
REQUIRES_PYTHON = '>=3.10'

for line in open('src/fraudit/__init__.py'):
    line = line.strip()
    if '__version__' in line:
        context = {}
        exec(line, context)
        VERSION = context['__version__']

HERE = Path(__file__).parent

try:
    with open(HERE / "README.md", encoding='utf-8') as f:
        long_description = '\n' + f.read()
except FileNotFoundError:
    long_description = DESCRIPTION

REQUIRES_FILE = HERE / 'requirements.txt'
REQUIRED = [i.strip() for i in open(REQUIRES_FILE) if not i.startswith('#')]


setup(
    name=NAME,
    version=VERSION,
    description=DESCRIPTION,
    author_email=EMAIL,
    long_description=long_description,
    long_description_content_type='text/markdown',
    author=AUTHOR,
    url=URL,
    python_requires=REQUIRES_PYTHON,
    install_requires=REQUIRED,
    extras_require={},
    packages=[p for p in find_packages() if p.startswith('fraudit')],
    include_package_data=True,
    license='MIT License',
    classifiers=[
        # Trove classifiers
        # Full list: https://pypi.python.org/pypi?%3Aaction=list_classifiers
        'License :: OSI Approved :: MIT License',
        'Topic :: Text :: Short Text',
        'Topic :: Scientific/Engineering :: Spark, PySpark, PySpark Streaming, PySpark SQL',
    ],
)