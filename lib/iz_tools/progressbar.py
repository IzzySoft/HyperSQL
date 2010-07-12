# $Id$
"""
Progress bar
Original Source: http://code.activestate.com/recipes/168639-progress-bar-class/
Modified by: Izzy
"""

from sys import stdout
from locale import getdefaultlocale
lc, encoding = getdefaultlocale()
if not encoding: encoding = 'utf-8'

class progressBar:
    """
    This is a simple text mode progress bar to show the percentage of completion.
    It is intended to take a string explaining the task running, which is
    displayed together with the actual progress bar.
    """
    def __init__(self, prefix='', minValue = 0, maxValue = 100, totalWidth=12, padLen=60):
        """
        Initialize the progress bar
        @param self
        @param string prefix Task running. This string should be no longer than padLen.
               Leaving it empty (default) will cause the bar starting at pos 0 (begin
               of the line). Otherwise, prefix will be right-padded by spaces, and
               the bar appended to its end.
        @param int minValue Start value (absolute number, usually 0=default)
        @param int maxValue End value (absolute number corresponding to 100%, default=100)
        @param int totalWidth Width of the *bar* (without the prefix) in characters
                   (default: 12)
        @param int padLen To how many chars the prefix (if specified) should be padded
        """
        if len(prefix)>0:
            prefix = prefix.ljust(60)
        self.prefixLen = len(prefix)
        self.mask = prefix + '[%s]'
        self.pbar = self.mask   # This holds the progress bar string
        self._old_pbar = self.pbar   # for draw()
        self.min = minValue
        self.max = maxValue
        self.span = maxValue - minValue
        self.width = totalWidth
        self.amount = 0       # When amount == max, we are 100% done 
        self.update(0)        # Build progress bar string

    def update(self, newAmount = 0):
        """
        Update the actual value and re-draw the progress bar (if necessary).
        This updates the "current value" and calls progressbar.draw(). The value
        passed may be greater or less than the recent value - or even the same.
        @param self
        @param int curVal
        """
        if newAmount < self.min: newAmount = self.min
        if newAmount > self.max: newAmount = self.max
        self.amount = newAmount

        # Figure out the new percent done, round to an integer
        diffFromMin = float(self.amount - self.min)
        if self.span!=0: percentDone = (diffFromMin / float(self.span)) * 100.0
        else: percentDone = 0
        percentDone = round(percentDone)
        percentDone = int(percentDone)

        # Figure out how many hash bars the percentage should be
        allFull = self.width - 2
        numHashes = (percentDone / 100.0) * allFull
        numHashes = int(round(numHashes))

        # build a progress bar with hashes and spaces
        bar = '='*numHashes + ' '*(allFull-numHashes)
        self.pbar = self.mask % bar

        # figure out where to put the percentage, roughly centered
        percentPlace = self.prefixLen + 1 + (self.width / 2) - len(str(percentDone)) 
        percentString = str(percentDone) + "%"

        # slice the percentage into the bar
        self.pbar = self.pbar[0:percentPlace] + percentString + self.pbar[percentPlace+len(percentString):]

        # call draw() to update screen if necessary
        self.draw()

    def __str__(self):
        """ Returns the current string of the bar (incl. prefix) """
        return self.pbar.encode(encoding)

    def draw(self):
        """ draw progress bar - but only if it has changed """
        if self.pbar != self._old_pbar:
            self._old_pbar = self.pbar
            stdout.write(self.__str__() + '\r')
            stdout.flush()

