from distutils.core import setup, Extension
import os
import sys

sources = []
for root, dirs, files in os.walk(os.path.join(os.getcwd(), 'src', 'ksp')):
    for f in files:
        if f.endswith(".cpp"):
             sources.append(os.path.join(root, f))

ksp = Extension('ksp',
                    include_dirs = [
                         os.path.join(os.getcwd(), 'lib/pybind11/include'),
                         os.path.abspath(os.path.join(sys.executable, "..", "Library", "include")),
                    ],
                    libraries = ['boost_regex'],
                    library_dirs = [os.path.abspath(os.path.join(sys.executable, "..", "Library", "lib"))],
                    sources = sources)

setup (name = 'ksp',
       version = '1.0',
       description = 'A wrapper for the k-shortest paths with limited overlap implementation by Theodoros Chondrogiannis (https://github.com/tchond/kspwlo).',
       author = 'M.Folini',
       author_email = 'marc.folini@gmx.ch',
       url = '',
       long_description = '',
       ext_modules = [ksp],
)
