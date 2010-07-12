"""
$Id$
HyperSQL gettext basics
Copyright 2010 Itzchak Rehberg & IzzySoft

This evaluates the basic settings required for gettext
"""

# Setup gettext support
import gettext
from locale import getdefaultlocale
from sys import argv as pargs
from os import environ as os_environ, path as os_path, sep as os_sep
langs = []
lc, encoding = getdefaultlocale()
if (lc):
    langs = [lc,lc[:2]]
language = os_environ.get('LANGUAGE', None)
if (language):
    langs += language.split(":")
langs += ['en_US']
langpath = os_path.split(pargs[0])[0] + os_sep + 'lang'

"""
# Example for what has to be done in a module afterwards:

from gettext_init import langpath, langs
import gettext

gettext.bindtextdomain('module_name', langpath)
gettext.textdomain('module_name')
lang = gettext.translation('module_name', langpath, languages=langs, fallback=True)
_ = lang.ugettext
"""