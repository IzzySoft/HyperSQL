#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Dependency graph
$Id$

Example usage:

g = depgraph()
if g.deps_ok:
  g.set_graph('a -> b\nb -> c')
  #g.set_graph(['a -> b','b -> c'])
  g.make_graph('ab.png','png','Vera')
"""

#====================================================[ Imports and Presets ]===
from iz_tools.typecheck import *
from iz_tools.system import *
from hypercore.gettext_init import langpath, langs
from os import sep as os_sep, path as os_path, access as os_access, unlink as os_unlink
from tempfile import NamedTemporaryFile
from hypercore.logger import logg
logger = logg.getLogger('DepGraph')

# Setup gettext support
import gettext
gettext.bindtextdomain('depgraph', langpath)
gettext.textdomain('depgraph')
lang = gettext.translation('depgraph', langpath, languages=langs, fallback=True)
_ = lang.ugettext


#=========================================================[ DepGraph class ]===
class depgraph(object):
    """
    Generate dependency graphs using graphviz
    This requires the graphviz application to be installed
    """

    def __init__(self,mod='dot',charset='utf-8',deltmp=True):
        """
        Setup required dependencies and create the instance
        @param self
        @param optional string mod graphviz module to use. Defaults to 'dot'
        @param optional string charset charset to use (see set_charset). Default: 'utf-8'
        @param optional boolean deltmp Whether to delete the temporary command file. Default: True
        """
        self.bin   = ''  # the binary/executable
        self.mod   = ''  # just the name w/o path
        self.charset = ''
        self.graph = ''  # graph definition text
        self.name  = 'G' # name of the generated graph
        self.fontname = ''  # font to use with graphviz
        self.fontsize = ''  # font size to use with graphviz
        self.size = ''   # image size ('x-inch,y-inch')
        self.ranksep_dot = '' # rank separator for dot
        self.ranksep_twopi = '' # rank separator for twopi
        self.len_neato = '' # 'rank separator' for neato
        self.len_fdp = '' # 'rank separator' for fdp
        self.mindist_circo = '' # 'rank separator' for circo
        self.deltmp = deltmp
        self.set_mod(mod)
        self.set_charset(charset)

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
        binmod = mod
        if mod.find(os_sep)==-1:
            binmod = which(mod) # check for the binary in PATH environment
        if binmod==None:
            self.bin = ''
            self.mod = ''
        elif os_path.isfile(binmod) and os_access(binmod, os.X_OK):
            self.bin = binmod
            self.mod = mod
        else:
            self.bin = ''
            self.mod = ''

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
        """
        if not is_str(name):
            logger.error(_('%(func)s was called with wrong parameter type: required: [%(req)s], given: [%(got)s]'), {'func':'depgraph.set_name','req':'str','got':','.join(is_what(name))})
            return
        if name=='':
            logger.error(_('parameter %(parm)s to %(func)s must not be empty!'), {'parm':'name','func':'depgraph.set_name'})
            return
        self.name = name

    def set_charset(self,name='utf-8'):
        """
        Set the character set used in your graph definition. Supported charsets
        are 'utf-8' and 'iso-8859-1' (aka 'latin-1') currently, so all others
        will provoke an error from Graphviz and fallback to utf-8, until the
        Graphviz team supports them.
        @param self
        @param optional string name name of the charset (defaults to 'utf-8').
               Pass an empty string to use the defaults configured with graphviz,
               if unsure - and then investigate the error message shown, which
               usually suggests you the correct one to use
        @example depgraph.set_charset('iso-8859-1')
        """
        if not is_str(name):
            logger.error(_('%(func)s was called with wrong parameter type: required: [%(req)s], given: [%(got)s]'), {'func':'depgraph.set_charset','req':'str','got':','.join(is_what(name))})
            return
        name = name.lower()
        if name=='iso-8859-15': name='iso-8859-1'
        self.charset = name

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
            logger.error(_('%(func)s was called with wrong parameter type: required: [%(req)s], given: [%(got)s]'), {'func':'depgraph.set_fontsize','req':'numeric','got':','.join(is_what(size))})
            return
        self.fontsize = size

    def set_ranksep(self,size,mod):
        """
        Set a different rank separator (valid for dot only)
        Without that, the graphviz default font size is used.
        @param self
        @param string ranksep ranksep value (distance, numeric) or empty string to reset
        @param string mod Graphviz module to apply to (one of fdp, neato, circo, dot, twopi)
        """
        if not is_numeric(size) and size!='':
            logger.error(_('%(func)s was called with wrong parameter type: required: [%(req)s], given: [%(got)s]'), {'func':'depgraph.set_ranksep','req':'numeric','got':','.join(is_what(size))})
            return
        if not is_str(mod):
            logger.error(_('%(func)s was called with wrong parameter type: required: [%(req)s], given: [%(got)s]'), {'func':'depgraph.set_ranksep','req':'string','got':','.join(is_what(mod))})
            return
        if mod == 'fdp':
            self.len_fdp = size
        elif mod == 'neato':
            self.len_neato = size
        elif mod == 'circo':
            self.mindist_circo = size
        elif mod == 'dot':
            self.ranksep_dot = size
        elif mod == 'twopi':
            self.ranksep_twopi = size
        else:
            logger.error(_('unsupported Graphviz module "%s"'), mod)
            return

    def set_size(self,x,y):
        """
        Limit resulting image size
        Without this set, we leave the decision to graphviz. Use x=0 or y=0 to reset.
        @param self
        @param int x width in inches (sorry, but that's what graphviz expects)
        @param int y height in inches
        """
        if not is_numeric(x) or not is_numeric(y):
            logger.error(_('%(func)s was called with wrong parameter type: required: [%(req)s], given: [%(got)s]'), {'func':'depgraph.set_size','req':'numeric','got':','.join(is_what(size))})
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
        if self.mod == 'fdp' and self.len_fdp != '': props += ' -Elen='+self.len_fdp
        elif self.mod == 'neato' and self.len_neato != '': props += ' -Elen='+self.len_neato
        elif self.mod == 'dot' and self.ranksep_dot != '': props += ' -Granksep='+self.ranksep_dot
        elif self.mod == 'twopi' and self.ranksep_twopi != '': props += ' -Granksep='+self.ranksep_twopi
        elif self.mod == 'circo' and self.mindist_circo != '': props += ' -Gmindist='+self.mindist_twopi
        if self.charset!='': props += ' -Gcharset="'+self.charset+'"'
        out,err = popen( self.bin + props + parms )
        logger.debug('calling "'+self.bin + props + parms +'"')
        if self.deltmp: os_unlink(tmpname)
        return err
