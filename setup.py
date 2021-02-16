from setuptools import setup
from mft import __version__

setup(
    name='mft',
    version=__version__,
    description="A package to facilitate sharing files via SolarWinds Managed File Transfer.",
    url='https://github.com/GitPushPullLegs/mft',
    author='Joe Aguilar',
    author_email='Jose.Aguilar.6694@gmail.com',
    license='GNU General Public License',
    packages=['mft'],
    install_requires=['requests>=2.25.1',
                      'urllib3>=1.26.3',
                      ],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Operating System :: Microsoft :: Windows',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],
)