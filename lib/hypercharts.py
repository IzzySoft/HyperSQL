"""
$Id$
HyperCharts - JavaScript Charts generator using LTDiagram
(requires diagram.js from LTDiagram to be included with your pages JavaScript)
Copyright 2010 Itzchak Rehberg & IzzySoft

Example usage:

pie = PieChart('Pie',0,0,10,50)
pie.addPiece(10,'10%')
pie.addPiece(40,'40%')
pie.addPiece(50,'50%')
js = pie.generate()

bar = ChartLegend('Pie',120,0,80,15,5)
bar.addBar('10%','Give the tenth')
bar.addBar('40%','Forty of hundred years')
bar.addBar('50%','Fifty-Fifty')
js += bar.generate()

print '<SCRIPT>\njs\n</SCRIPT>'
"""

class Chart(object):
    """ Base class for all the chart classes """
    def __init__(self,name,x,y,offset,cols=[]):
        """
        Initialize base values
        @param self
        @param name name of the object (must be suitable for use as JavaScript variable name)
        @param int x x-position
        @param int y y-position
        @param int offset margin to surrounding elements
        @param optional list cols list of HTML color codes to use in the given order
        """
        self.name = name
        self.x = x
        self.y = y
        self.offset = offset
        self.cols = cols
        if len(cols)==0:
            self.cols.append('#cc3333')
            self.cols.append('#3366ff')
            self.cols.append('#dddddd')
            self.cols.append('#ff9933')
            self.cols.append('#33ff00')
        self.vals = []
        self.seq = -1

    def nextVal(self):
        """ Get the sequence id for the next piece """
        self.seq += 1
        return self.seq


class PieChart(Chart):
    """
    PieChart generates Pie Charts using LTDiagram
    """

    def __init__(self,name,x,y,offset,rad,cols=[]):
        """
        Initialize the pie with base values
        @param self
        @param string name name of the pie (to be used as JavaScript variable)
        @param int x x-position
        @param int y y-position
        @param int offset margin to surrounding elements
        @param int rad radius of the pie
        @param optional list cols list of HTML color codes to use in the given order
        """
        Chart.__init__(self,name,x,y,offset,cols)
        self.rad = rad

    def addPiece(self,val,tooltip=''):
        """
        Add the data for a piece
        @param self
        @param list piece float percentage for the piece, string tooltip
        """
        self.vals.append([val,tooltip])

    def makePiece(self,num,start,stop,tooltip=''):
        """
        Create a new piece
        @param self
        @param int num number (sequential) number of the piece
        @param float start start position in 1/100 of the entire pie (equals end position of previous piece or 0 if it's the first)
        @param float end end position in 1/100 of the entire pie
        @param optional string tooltip tooltip text (if any)
        @return string js JavaScript code
        """
        js = self.name +'[' + `num` +']=new Pie(' + `self.x` + ',' + `self.y` + ',' + `self.offset` \
            + ',' + `self.rad` + ',' + `start` + '*3.6,' + `stop` + '*3.6,"' + self.cols[num]
        if tooltip != '':
            js += '","' + tooltip + '");\n'
        else:
            js += '");\n'
        return js

    def generate(self):
        """
        Generate a pie chart for the given vals
        @param self
        @return string js JavaScript code
        """
        js = 'var ' + self.name + ' = new Array();\ndocument.open();\n'
        sum = 0
        for val in self.vals:
            js += self.makePiece(self.nextVal(), sum, sum+val[0], val[1])
            sum += val[0]
        js += 'function MouseOver' + self.name + '(i) { ' + self.name + '[i].MoveTo("","",10); }\n'
        js += 'function MouseOut' + self.name + '(i) { ' + self.name + '[i].MoveTo("","",0); }\n'
        js += 'document.close();\n'
        return js


class ChartLegend(Chart):
    """
    ChartLegend generates a group of Bar Charts using LTDiagram as legend for a Pie Chart
    """

    def __init__(self,pie,x,y,wid,hei,offset,cols=[],tcols=[]):
        """
        Initialize the pie with base values
        @param self
        @param string pie name of the pie this legend is for
        @param int x x-position
        @param int y y-position
        @param int wid width of the bars
        @param int hei height of the bars
        @param int offset space between the bars
        @param optional list cols list of HTML color codes to use for the background in the given order
        @param optional list tcols list of HTML color codes to use for the text in the given order
        """
        Chart.__init__(self,pie,x,y,offset,cols)
        self.wid = wid
        self.hei = hei
        self.tcols = tcols
        if len(tcols)==0:
            self.tcols.append('#ffffff')
            self.tcols.append('#ffffff')
            self.tcols.append('#000000')
            self.tcols.append('#000000')
            self.tcols.append('#000000')

    def addBar(self,text,tooltip=''):
        """
        Add the data for a bar item
        @param self
        @param string text what to write on the bar
        """
        self.vals.append([text,tooltip])

    def makeBar(self,num):
        """
        Create a new bar
        @param int rownum number of the bar
        """
        top = self.y + num * (self.hei + self.offset)
        bottom = top + self.hei
        js = 'new Bar(' + `self.x` + ',' + `top` + ',' + `self.x + self.wid` + ',' + `bottom` \
            + ',"' + self.cols[num] + '","' + self.vals[num][0] + '","' + self.tcols[num] \
            + '","' + self.vals[num][1] + '","void(0)","MouseOver' + self.name + '(' + `num` +')",' \
            + '"MouseOut' + self.name + '(' + `num` + ')");\n'
        return js

    def generate(self):
        """
        Generate the legend
        """
        js = 'document.open();\n'
        for i in range(len(self.vals)):
            js += self.makeBar(i)
        js += 'document.close();\n'
        return js

