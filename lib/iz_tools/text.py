#!/usr/bin/python
# -*- coding: utf-8 -*-
# $Id$
"""
Some useful functions for string / text processing
"""

#====================================================[ Imports and Presets ]===
import re       # for getWordLineNo

#==============================================================[ Functions ]===
#--------------------------------------[ Finding lineNo with matching text ]---
def getWordLineNo(text,pattern):
    """
    Finding lineNo with matching text
    example:
    getWordLineNo(text,'<P>([^<]+)<SUP>')
    Adapted from: http://snippets.dzone.com/posts/show/1638
    By: Izzy
    @param string text to parse
    @param string pattern RegExp pattern to find
    @return list of tuples (lineno, offset, word)
    """
    res = []
    for m in re.finditer(pattern, text, re.I):
        start = m.start()
        lineno = text.count('\n', 0, start) + 1
        offset = start - text.rfind('\n', 0, start)
        word = m.group(0)
        res.append((lineno, offset, word))
    return res
