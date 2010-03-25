#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Dependency graph
"""

#====================================================[ Imports and Presets ]===
from systools import *
from os import sep as os_sep, path as os_path, access as os_access, unlink as os_unlink
from tempfile import NamedTemporaryFile
import logging
logger = logging.getLogger('main.depgraph')

# Setup gettext support
import gettext
from locale import getdefaultlocale
from sys import argv as pargs
from os import environ as os_environ
langs = []
lc, encoding = getdefaultlocale()
if (lc):
    langs = [lc,lc[:2]]
language = os_environ.get('LANGUAGE', None)
if (language):
    langs += language.split(":")
langs += ['en_US']
langpath = os_path.split(pargs[0])[0] + os.sep + 'lang'
gettext.bindtextdomain('hyperjdoc', langpath)
gettext.textdomain('depgraph')
lang = gettext.translation('depgraph', langpath, languages=langs, fallback=True)
_ = lang.ugettext


#=========================================================[ DepGraph class ]===
class depgraph(object):
    """
    Generate dependency graphs using graphviz
    This requires the graphviz application to be installed
    """

    def __init__(self,mod='dot'):
        """
        Setup required dependencies and create the instance
        @param self
        @param optional string mod graphviz module to use. Defaults to 'dot'
        """
        self.bin   = ''  # the binary/executable
        self.graph = ''  # graph definition text
        self.name  = 'G' # name of the generated graph
        self.fontname = ''  # font to use with graphviz
        self.fontsize = ''  # font size to use with graphviz
        self.size = ''   # image size ('x-inch,y-inch')
        self.ranksep = '' # rank separator for dot
        self.set_mod(mod)

    def set_mod(self,mod='dot'):
        """
        Set the graphviz module to use
        @param self
        @param optional string mod name of the module. This can be a full path, file.ext or file. Default: 'dot'
        @throws TypeError if the passed argument is neither string nor dict
        @example depgraph.set_mod('/usr/bin/dot') # this will be bound to *nix systems
        @example depgraph.set_mod('dot')          # this will find dot (*nix) or dot.exe (Win+OS/2) in the PATH
        """
        if not is_str(mod):
            logger.error(_('%(func)s was called with wrong parameter type: required: [%(req)s], given: [%(got)s]'), {'func':'depgraph.set_mod','req':'str','got':','.join(is_what(mod))})
            raise TypeError
        if mod.find(os_sep)==-1:
            mod = which(mod) # check for the binary in PATH environment
        if os_path.isfile(mod) and os_access(mod, os.X_OK):
            self.bin = mod
        else:
            self.bin = ''

    def deps_ok(self):
        """
        Check whether depgraph can operate (i.e. it found a suitable executable)
        @return boolean
        """
        if self.mod != '': return True
        return False

    def set_graph(self,graph):
        """
        Setup the graph definition
        @param self
        @param mixed graph either array of strings (multiple lines of defs) or string
        @throws TypeError if the passed argument is neither string nor dict
        @example depgraph.set_graph('a -> b\nb -> c')    # using string input
        @example depgraph.set_graph(['a -> b','b -> c']) # using array input
        """
        if is_str(graph): self.graph = graph
        elif is_list(graph): self.graph = '\n'.join(graph)
        else:
            logger.error(_('%(func)s was called with wrong parameter type: required: [%(req)s], given: [%(got)s]'), {'func':'depgraph.set_graph','req':'str','got':','.join(is_what(graph))})
            raise TypeError

    def set_name(self,name='G'):
        """
        Set the name for the graph
        @param self
        @param optional string name name of the graph (defaults to a simple 'G')
        @throws TypeError if the passed name is not a string
        @throws ValueError when an empty string is passed (graph *must* have a name)
        """
        if not is_str(name):
            logger.error(_('%(func)s was called with wrong parameter type: required: [%(req)s], given: [%(got)s]'), {'func':'depgraph.set_name','req':'str','got':','.join(is_what(name))})
            raise TypeError
        if name=='':
            logger.error(_('parameter %(parm)s to %(func)s must not be empty!'), {'parm':'name','func':'depgraph.set_name'})
            raise ValueError
        self.name = name

    def set_fontname(self,font):
        """
        Set a different default font
        Without that, the graphviz default font (usually "Times") is used.
        If you set this, it is simply passed to graphviz - without making sure the font is available
        @param self
        @param string font Font name - or empty string to reset
        """
        if not is_str(font):
            logger.error(_('%(func)s was called with wrong parameter type: required: [%(req)s], given: [%(got)s]'), {'func':'depgraph.set_fontname','req':'str','got':','.join(is_what(font))})
            return
        self.fontname = font

    def set_fontsize(self,size):
        """
        Set a different default font size
        Without that, the graphviz default font size is used.
        @param self
        @param string font size (in points) - or empty string to reset
        """
        if not is_numeric(size) and size!='':
            logger.error(_('%(func)s was called with wrong parameter type: required: [%(req)s], given: [%(got)s]'), {'func':'depgraph.set_fontsize','req':'numeric','got':','.join(is_what(font))})
            return
        self.fontsize = size

    def set_ranksep(self,size):
        """
        Set a different rank separator (valid for dot only)
        Without that, the graphviz default font size is used.
        @param self
        @param string ranksep - or empty string to reset
        """
        if not is_numeric(size) and size!='':
            logger.error(_('%(func)s was called with wrong parameter type: required: [%(req)s], given: [%(got)s]'), {'func':'depgraph.set_ranksep','req':'numeric','got':','.join(is_what(font))})
            return
        self.ranksep = size

    def set_size(self,x,y):
        """
        Limit resulting image size
        Without this set, we leave the decision to graphviz. Use x=0 or y=0 to reset.
        @param self
        @param int x width in inches (sorry, but that's what graphviz expects)
        @param int y height in inches
        """
        if not is_numeric(x) or not is_numeric(y):
            logger.error(_('%(func)s was called with wrong parameter type: required: [%(req)s], given: [%(got)s]'), {'func':'depgraph.set_size','req':'numeric','got':','.join(is_what(font))})
            return
        if x==0 or y==0: self.size = ''
        else: self.size = `x`+','+`y`

    def make_graph(self,fname,ftype='png'):
        """
        Create the dependency graph as a file named fname of the type ftype
        @param self
        @param string fname name of the graphics file to create. If no path is specified,
                the current directory is used. If a path is specified, it should already exist!
        @param string ftype graphics type. Must be supported by the used graphviz module! Defaults to 'png'.
        @return string error stderr from graphviz (if any - otherwise empty string)
        """
        if not is_str(ftype):
            logger.error(_('%(func)s was called with wrong parameter type: required: [%(req)s], given: [%(got)s]'), {'func':'depgraph.make_graph','req':'str','got':','.join(is_what(ftype))})
            return
        if not is_str(fname):
            logger.error(_('%(func)s was called with wrong parameter type: required: [%(req)s], given: [%(got)s]'), {'func':'depgraph.make_graph','req':'str','got':','.join(is_what(fname))})
            return
        if self.graph == '':
            logger.error(_('make_graph() called on an empty graph!'))
            return
        # Write graph information to a temporary file
        tmpname = fname + '.tmp'
        outfile = fopen(tmpname,'w')
        outfile.write( 'digraph ' + self.name + '{\n' + self.graph +'\n}\n' )
        outfile.close()
        # Call graphviz to generate the image
        props = ' -T'+ftype+' -Nstyle=filled'
        parms = ' -o '+fname+' '+tmpname
        if self.fontname!='': props += ' -Nfontname="'+self.fontname+'"'
        if self.fontsize!='': props += ' -Nfontsize="'+self.fontsize+'"'
        if self.size!='': props += ' -Gsize="'+self.size+'"'
        if self.ranksep!='': props += ' -Granksep='+self.ranksep
        out,err = popen( self.bin + props + parms )
        logger.info('calling "'+self.bin + props + parms +'"')
        #os_unlink(tmpname)
        return err
        
"""
g = depgraph()
print g.bin
if g.deps_ok: print 'We can use this!'
g.set_graph('a -> b\nb -> c')
print g.graph
g.set_graph(['a -> b','b -> c'])
print g.graph
#g.set_graph(1)
g.make_graph('/srv/www/htdocs/igwebapi/lib/ab.png','png','Vera')
"""
