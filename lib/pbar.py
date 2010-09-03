"""
Progressbar handlers

$Id$
"""
from iz_tools.progressbar import *
from hypercore.elements import metaInfo
from hypercore.logger import logg
pbar = progressBar() # make it global

def pbarInit(prefix,start,end,logname=''):
    """
    Initialize ProgressBar
    @param string prefix the progress message to pass
    @param int start start value (usually 0)
    @param int end max value
    """
    logg.getLogger(logname).debug(prefix)
    if metaInfo.printProgress:
        pbar.__init__(prefix,start,end)
        pbar.draw()

def pbarUpdate(newVal):
    """
    Update the ProgressBar
    @param int newVal new value (current state)
    """
    if metaInfo.printProgress:
        pbar.update(newVal)

def pbarClose():
    """ At end of processing, we need a newline """
    if metaInfo.printProgress: print


#------------------------------------------------------------------------------
def printProgress(msg,logname=''):
    """
    If config(Logging.progress) evaluates to True, print which step we are performing
    @param string msg what to print out
    """
    logg.getLogger(logname).debug(msg)
    if metaInfo.printProgress:
        print msg


