"""
(PL/)SQL and Oracle Forms statistics
"""
__revision__ = '$Id$'

from hypercore.elements import metaInfo
from hypercore.helpers  import num_format,size_format
from hypercore.javadoc  import JavaDocVars
from iz_tools.system    import fopen
from .commonhtml        import MakeHTMLHeader, MakeHTMLFooter
from shutil             import copy2

# Setup gettext support
import gettext
from hypercore.gettext_init import langpath, langs
gettext.bindtextdomain('hypersql', langpath)
gettext.textdomain('hypersql')
lang = gettext.translation('hypersql', langpath, languages=langs, fallback=True)
_ = lang.ugettext

# Setup logging
from hypercore.logger import logg
logname = 'SQLStats'
logger = logg.getLogger(logname)


#------------------------------------------------------------------------------
def generateOutput(outfile):
    """
    Generate Statistics Page
    @param object outfile file object to write the stats into
    """
    from hypercore.charts import ChartLegend,PieChart

    pie_rad = 55
    pie_offset = 5
    bar_wid = 80
    bar_hei = 15

    outfile.write('<H1>' + metaInfo.indexPageName['stat'] + '</H1>\n')
    if metaInfo.indexPage['form'] != '':
        outfile.write('<P ALIGN="center">'+_('Oracle Forms are not considered for statistics')+'</P>\n')

    c = metaInfo.colors

    # LinesOfCode
    outfile.write("<TABLE CLASS='apilist stat'>\n")
    outfile.write('  <TR><TH COLSPAN="4">'+_('Lines of Code')+'</TH></TR>\n')
    outfile.write('  <TR><TH CLASS="sub">'+_('Name')+'</TH><TH CLASS="sub">'+_('Lines')+'</TH><TH CLASS="sub">'+_('Pct')+'</TH><TD ROWSPAN="6" CLASS="pie_chart"><DIV CLASS="pie_chart">\n')
    js = '<SCRIPT Language="JavaScript" TYPE="text/javascript">\n'
    js += '_BFont="font-family:Verdana;font-weight:bold;font-size:8pt;line-height:10pt;"\n'
    js += 'function initCharts() { for (var i=0;i<8;++i) { if (i<4) { MouseOutL(i); } if (i<5) { MouseOutFS(i); } MouseOutO(i); if (i<3) { MouseOutFL(i); MouseOutJ(i); } } }\n'
    colors = [col[0] for col in [c['code'],c['comment'],c['empty'],c['mixed']]]
    tcols  = [col[1] for col in [c['code'],c['comment'],c['empty'],c['mixed']]]
    pieposx = pie_rad + 2*pie_offset
    pieposy = 0
    # pie = PieChart(name,x,y,offset,rad[,colors[]])
    pie = PieChart('L',pieposx,pieposy,pie_offset,pie_rad,colors)
    # pie.addPiece(pct[,tooltip])
    pie.addPiece(metaInfo.getLocPct('code'))
    pie.addPiece(metaInfo.getLocPct('comment'))
    pie.addPiece(metaInfo.getLocPct('empty'))
    pie.addPiece(metaInfo.getLocPct('mixed'))
    js += pie.generate();
    # bar = new ChartLegend(name,x,y,wid,hei,offset[,cols[,tcols]])
    barposx = pieposx + pie_rad + 3*pie_offset
    barposy = pieposy - 2*pie_rad/3
    bar = ChartLegend('L',barposx,barposy,bar_wid,bar_hei,pie_offset,colors,tcols)
    # bar.addBar(text[,tooltip])
    bar.addBar(_('Code'),_('Plain Code'))
    bar.addBar(_('Comment'),_('Plain Comments'))
    bar.addBar(_('Empty'),_('Empty Lines'))
    bar.addBar(_('Mixed'),_('Lines with Code and Comments'))
    js += bar.generate()
    js += '</SCRIPT>\n'
    outfile.write(js);
    outfile.write('</DIV></TD></TR>\n')
    for name in ['totals','code','comment','empty','mixed']:
        outfile.write('  <TR><TH CLASS="sub">' + _(name.capitalize()) \
            + '</TH><TD ALIGN="right">' + num_format(metaInfo.getLoc(name)) \
            + '</TD><TD ALIGN="right">' + num_format(metaInfo.getLocPct(name),2) + '%' \
            + '</TD></TR>\n')
    outfile.write("</TABLE>\n")

    # Object Stats
    colors = [col[0] for col in [c['tab'],c['mview'],c['view'],c['func'],c['proc'],c['synonym'],c['sequence'],c['trigger'],c['pkg']]]
    tcols  = [col[1] for col in [c['tab'],c['mview'],c['view'],c['func'],c['proc'],c['synonym'],c['sequence'],c['trigger'],c['pkg']]]
    posy = 0
    tabs = 0
    views = 0
    mviews = 0
    funcs = 0
    procs = 0
    synonyms = 0
    sequences = 0
    triggers = 0
    for file_info in metaInfo.fileInfoList:
        tabs += len(file_info.tabInfoList)
        views += len(file_info.viewInfoList)
        mviews += len(file_info.mviewInfoList)
        synonyms += len(file_info.synInfoList)
        sequences += len(file_info.seqInfoList)
        triggers += len(file_info.triggerInfoList)
        funcs += len(file_info.functionInfoList)
        procs += len(file_info.procedureInfoList)
        for package_info in file_info.packageInfoList:
            funcs += len(package_info.functionInfoList)
            procs += len(package_info.procedureInfoList)
    totalObj = tabs + views + mviews + synonyms + sequences + funcs + procs + triggers
    outfile.write("<TABLE CLASS='apilist stat'>\n")
    outfile.write('  <TR><TH COLSPAN="4">'+_('Object Statistics')+'</TH></TR>\n')
    outfile.write('  <TR><TH CLASS="sub">'+_('Name')+'</TH><TH CLASS="sub">'+_('Value')+'</TH><TH CLASS="sub">'+_('Pct')+'</TH><TD ROWSPAN="8" CLASS="pie_chart" STYLE="height:120px;"><DIV CLASS="pie_chart">\n')
    js = '<SCRIPT Language="JavaScript" TYPE="text/javascript">\n'
    if totalObj > 0:
        barposy = pieposy - 4*pie_rad/3
        pie = PieChart('O',pieposx,pieposy,pie_offset,pie_rad,colors)
        pie.addPiece((float(tabs)/totalObj) * 100)
        pie.addPiece((float(mviews)/totalObj) * 100)
        pie.addPiece((float(views)/totalObj) * 100)
        pie.addPiece((float(funcs)/totalObj) * 100)
        pie.addPiece((float(procs)/totalObj) * 100)
        pie.addPiece((float(synonyms)/totalObj) * 100)
        pie.addPiece((float(sequences)/totalObj) * 100)
        pie.addPiece((float(triggers)/totalObj) * 100)
        js += pie.generate();
        bar = ChartLegend('O',barposx,barposy,bar_wid,bar_hei,pie_offset,colors,tcols)
        bar.addBar(_('Tables'))
        bar.addBar(_('MViews'))
        bar.addBar(_('Views'))
        bar.addBar(_('Functions'))
        bar.addBar(_('Procedures'))
        bar.addBar(_('Synonyms'))
        bar.addBar(_('Sequences'))
        bar.addBar(_('Triggers'))
        js += bar.generate()
        tabPct = num_format((float(tabs)/totalObj) * 100, 2)
        viewPct = num_format((float(views)/totalObj) * 100, 2)
        mviewPct = num_format((float(views)/totalObj) * 100, 2)
        funcPct = num_format((float(funcs)/totalObj) * 100, 2)
        procPct = num_format((float(procs)/totalObj) * 100, 2)
        synonymPct = num_format((float(synonyms)/totalObj) * 100, 2)
        sequencePct = num_format((float(sequences)/totalObj) * 100, 2)
        triggerPct = num_format((float(triggers)/totalObj) * 100, 2)
    else:
        js += 'function MouseOutO(i) {return;}\n'
        tabPct = num_format(0.0, 2)
        viewPct = num_format(0.0, 2)
        mviewPct = num_format(0.0, 2)
        synonymPct = num_format(0.0, 2)
        sequencePct = num_format(0.0, 2)
        triggerPct = num_format(0.0, 2)
        funcPct = num_format(0.0, 2)
        procPct = num_format(0.0, 2)
    js += '</SCRIPT>\n'
    outfile.write(js);
    outfile.write('</DIV></TD></TR>\n')
    outfile.write('  <TR><TH CLASS="sub">'+_('Tables')+'</TH><TD ALIGN="right">'+num_format(tabs)+'</TD><TD ALIGN="right">'+tabPct+'%</TD></TR>\n')
    outfile.write('  <TR><TH CLASS="sub">'+_('Materialized Views')+'</TH><TD ALIGN="right">'+num_format(mviews)+'</TD><TD ALIGN="right">'+mviewPct+'%</TD></TR>\n')
    outfile.write('  <TR><TH CLASS="sub">'+_('Views')+'</TH><TD ALIGN="right">'+num_format(views)+'</TD><TD ALIGN="right">'+viewPct+'%</TD></TR>\n')
    outfile.write('  <TR><TH CLASS="sub">'+_('Functions')+'</TH><TD ALIGN="right">'+num_format(funcs)+'</TD><TD ALIGN="right">'+funcPct+'%</TD></TR>\n')
    outfile.write('  <TR><TH CLASS="sub">'+_('Procedures')+'</TH><TD ALIGN="right">'+num_format(procs)+'</TD><TD ALIGN="right">'+procPct+'%</TD></TR>\n')
    outfile.write('  <TR><TH CLASS="sub">'+_('Synonyms')+'</TH><TD ALIGN="right">'+num_format(synonyms)+'</TD><TD ALIGN="right">'+synonymPct+'%</TD></TR>\n')
    outfile.write('  <TR><TH CLASS="sub">'+_('Sequences')+'</TH><TD ALIGN="right">'+num_format(sequences)+'</TD><TD ALIGN="right">'+sequencePct+'%</TD></TR>\n')
    outfile.write('  <TR><TH CLASS="sub">'+_('Triggers')+'</TH><TD ALIGN="right">'+num_format(triggers)+'</TD><TD ALIGN="right">'+triggerPct+'%</TD></TR>\n')
    outfile.write("</TABLE>\n")

    # FileStats
    barposy = pieposy - 2*pie_rad/3
    outfile.write("<TABLE CLASS='apilist stat'>\n")
    outfile.write('  <TR><TH COLSPAN="4">'+_('File Statistics')+'</TH></TR>\n')
    outfile.write('  <TR><TH CLASS="sub">'+_('Name')+'</TH><TH CLASS="sub">'+_('Value')+'</TH><TH CLASS="sub">'+_('Pct')+'</TH><TD ROWSPAN="8" CLASS="pie_chart"><DIV CLASS="pie_chart">\n')
    xmlFiles = metaInfo.getFileStat('xmlfiles')
    totalFiles = metaInfo.getFileStat('files') - xmlFiles
    # Lines
    colors = [col[0] for col in [c['file400l'],c['file1000l'],c['filebig']]]
    tcols  = [col[1] for col in [c['file400l'],c['file1000l'],c['filebig']]]
    stat = metaInfo.getFileLineStat([400,1000])
    limits = stat.keys() # for some strange reason, sorting gets lost in the dict
    stat[400] -= xmlFiles # they are always accounted with 0 lines here
    limits.sort()
    js = '<SCRIPT Language="JavaScript" TYPE="text/javascript">\n'
    pie = PieChart('FL',pieposx,pieposy,pie_offset,pie_rad,colors)
    sum  = (float(stat[400])/totalFiles)*100
    sum2 = (float(stat[1000])/totalFiles)*100
    pie.addPiece(sum)
    pie.addPiece(sum2)
    pie.addPiece(100-(sum+sum2))
    js += pie.generate();
    barposy -= pie_offset
    bar = ChartLegend('FL',barposx,barposy,bar_wid,bar_hei,pie_offset,colors,tcols)
    bar.addBar('&lt; 400',_('less than %s lines') % '400')
    bar.addBar('&lt; '+num_format(1000,0),_('%(from)s to %(to)s'' lines') % {'from': '400', 'to': num_format(1000,0)})
    bar.addBar('&gt; '+num_format(1000,0),_('%s lines and more') % num_format(1000,0))
    js += bar.generate()
    js += '</SCRIPT>\n'
    outfile.write(js);
    outfile.write('</DIV></TD></TR>\n')
    outfile.write('  <TR><TH CLASS="sub">'+_('Total Files')+'</TH><TD ALIGN="right">' + num_format(totalFiles) \
        + '</TD><TD ALIGN="right">' + num_format(100,2) + '%</TD></TR>\n')
    outfile.write('  <TR><TH CLASS="sub">'+_('Avg Lines')+'</TH><TD ALIGN="right">' + num_format(metaInfo.getFileStat('avg lines')) \
        + '</TD><TD>&nbsp;</TD></TR>\n')
    havestat = 0
    for limit in limits:
        havestat += stat[limit]
        outfile.write('  <TR><TH CLASS="sub">&lt; ' + num_format(limit,0) + '</TH>' \
            + '<TD ALIGN="right">' + num_format(stat[limit]) + '</TD>' \
            + '<TD ALIGN="right">' + num_format((float(stat[limit])/totalFiles)*100, 2) + '%</TD></TR>\n')
    outfile.write('  <TR><TH CLASS="sub">&gt; '+num_format(1000)+'</TH><TD ALIGN="right">' + num_format(totalFiles - havestat) \
        + '</TD><TD ALIGN="right">' + num_format((float(totalFiles - havestat)/totalFiles)*100, 2) + '%</TD></TR>\n')
    outfile.write('  <TR><TH CLASS="sub">'+_('Shortest')+'</TH><TD ALIGN="right">' \
        + num_format(metaInfo.getFileStat('min lines')) + '</TD><TD>&nbsp;</TD></TR>\n')
    outfile.write('  <TR><TH CLASS="sub">'+_('Longest')+'</TH><TD ALIGN="right">' \
        + num_format(metaInfo.getFileStat('max lines')) + '</TD><TD>&nbsp;</TD></TR>\n')
    outfile.write('  <TR><TH COLSPAN="4" CLASS="sub delim">&nbsp;</TH></TR>\n')
    # Sizes
    colors = [col[0] for col in [c['file10k'],c['file25k'],c['file50k'],c['file100k'],c['filebig']]]
    tcols  = [col[1] for col in [c['file10k'],c['file25k'],c['file50k'],c['file100k'],c['filebig']]]
    stat = metaInfo.getFileSizeStat([10240,25*1024,50*1024,102400])
    limits = stat.keys() # for some strange reason, sorting gets lost in the dict
    stat[10240] -= xmlFiles # they are in here with 0 byte size
    limits.sort()
    outfile.write('  <TR><TH CLASS="sub">'+_('Total Bytes')+'</TH><TD ALIGN="right">' + size_format(metaInfo.getFileStat('sum bytes')) \
        + '</TD><TD ALIGN="right">' + num_format(100,2) + '%</TD><TD COLSPAN="9" CLASS="pie_chart"><DIV CLASS="pie_chart">\n')
    js = '<SCRIPT Language="JavaScript" TYPE="text/javascript">\n'
    pieposy = pie_rad + pie_offset + bar_hei
    sum  = 0
    cols = ['codecol','commcol','mixcol','emptcol','lastcol']
    pie = PieChart('FS',pieposx,pieposy,pie_offset,pie_rad,colors)
    for limit in limits:
        pie.addPiece((float(stat[limit])/totalFiles)*100)
        sum += (float(stat[limit])/totalFiles)*100
    pie.addPiece(100-sum)
    js += pie.generate();
    barposy = pieposy - 2*pie_rad/3 -2*pie_offset
    bar = ChartLegend('FS',barposx,barposy,bar_wid,bar_hei,pie_offset,colors,tcols)
    oldlim = '0K'
    for limit in limits:
        bar.addBar('&lt; '+size_format(limit,0),_('Files between %(from)s and %(to)s') % {'from': oldlim, 'to': size_format(limit,0)})
        oldlim = size_format(limit,0)
    bar.addBar('&gt; '+size_format(102400,0),_('Files larger than %s') % size_format(102400,0))
    js += bar.generate()
    js += '</SCRIPT>\n'
    outfile.write(js);
    outfile.write('</DIV></TD></TR>\n')
    outfile.write('  <TR><TH CLASS="sub">'+_('Avg Bytes')+'</TH><TD ALIGN="right">' + size_format(metaInfo.getFileStat('avg bytes')) \
        + '</TD><TD>&nbsp;</TD></TR>\n')
    havestat = 0
    for limit in limits:
        havestat += stat[limit]
        outfile.write('  <TR><TH CLASS="sub">&lt; ' + size_format(limit,0) + '</TH>' \
            + '<TD ALIGN="right">' + num_format(stat[limit]) + '</TD>' \
            + '<TD ALIGN="right">' + num_format((float(stat[limit])/totalFiles)*100, 2) + '%</TD></TR>\n')
    outfile.write('  <TR><TH CLASS="sub">&gt; '+size_format(102400,0)+'</TH><TD ALIGN="right">' + num_format(totalFiles - havestat) \
        + '</TD><TD ALIGN="right">' + num_format((float(totalFiles - havestat)/totalFiles)*100, 2) + '%</TD></TR>\n')
    outfile.write('  <TR><TH CLASS="sub">'+_('Smallest')+'</TH><TD ALIGN="right">' \
        + size_format(metaInfo.getFileStat('min bytes')) + '</TD><TD>&nbsp;</TD></TR>\n')
    outfile.write('  <TR><TH CLASS="sub">'+_('Largest')+'</TH><TD ALIGN="right">' \
        + size_format(metaInfo.getFileStat('max bytes')) + '</TD><TD>&nbsp;</TD></TR>\n')
    outfile.write("</TABLE>\n")

    # JavaDoc
    jwarns = 0
    jbugs  = 0
    jtodo  = 0
    colors = [col[0] for col in [c['warn'],c['bug'],c['todo']]]
    tcols  = [col[1] for col in [c['warn'],c['bug'],c['todo']]]
    for file_info in metaInfo.fileInfoList:
        for package_info in file_info.packageInfoList:
            jwarns += package_info.verification.taskCount() + package_info.verification.funcCount() + package_info.verification.procCount()
            jbugs += package_info.bugs.taskCount() + package_info.bugs.funcCount() + package_info.bugs.procCount()
            jtodo += package_info.todo.taskCount() + package_info.todo.funcCount() + package_info.todo.procCount()
        oList = ['tab','view','mview','syn','seq','trigger','procedure','function']
        for oname in oList:
          for oInfo in file_info.__getattribute__(oname+'InfoList'):
            jwarns += oInfo.verification.taskCount()
            jbugs += oInfo.bugs.taskCount()
            jtodo += oInfo.todo.taskCount()
        if JavaDocVars['form_stats']:
          for form in file_info.formInfoList:
            jwarns += form.verification.allItemCount()
            jbugs  += form.bugs.allItemCount()
            jtodo  += form.todo.allItemCount()
    totalObj = jwarns + jbugs + jtodo
    outfile.write("<TABLE CLASS='apilist stat'>\n")
    outfile.write('  <TR><TH COLSPAN="4">'+_('JavaDoc Statistics')+'</TH></TR>\n')
    outfile.write('  <TR><TH CLASS="sub">'+_('Name')+'</TH><TH CLASS="sub">'+_('Value')+'</TH><TH CLASS="sub">'+_('Pct')+'</TH><TD ROWSPAN="8" CLASS="pie_chart" STYLE="height:120px;"><DIV CLASS="pie_chart">\n')
    js = '<SCRIPT Language="JavaScript" TYPE="text/javascript">\n'
    if totalObj > 0:
        pieposy = 0
        pie = PieChart('J',pieposx,pieposy,pie_offset,pie_rad,colors)
        sum  = (float(jwarns)/totalObj) * 100
        sum2 = (float(jbugs)/totalObj) * 100
        pie.addPiece(sum)
        pie.addPiece(sum2)
        pie.addPiece(100-(sum+sum2))
        js += pie.generate();
        barposy = pieposy - 2*pie_rad/3 - pie_offset
        bar = ChartLegend('J',barposx,barposy,bar_wid,bar_hei,pie_offset,colors,tcols)
        bar.addBar(_('Warnings'),_('JavaDoc validation warnings'))
        bar.addBar(_('Bugs'),_('Known Bugs (from your @bug tags)'))
        bar.addBar(_('Todos'),_('Todo items (from your @todo tags)'))
        js += bar.generate()
        warnPct = num_format((float(jwarns)/totalObj) * 100, 2)
        bugPct  = num_format((float(jbugs)/totalObj) * 100, 2)
        todoPct = num_format((float(jtodo)/totalObj) * 100, 2)
    else:
        js += 'function MouseOutJ(i) {return;}\n'
        warnPct = num_format(0.0, 2)
        bugPct  = num_format(0.0, 2)
        todoPct = num_format(0.0, 2)
    js += '</SCRIPT>\n'
    outfile.write(js);
    outfile.write('</DIV></TD></TR>\n')
    outfile.write('  <TR><TH CLASS="sub">'+_('JavaDoc Warnings')+'</TH><TD ALIGN="right">'+num_format(jwarns)+'</TD><TD ALIGN="right">'+warnPct+'%</TD></TR>')
    outfile.write('  <TR><TH CLASS="sub">'+_('Known Bugs')+'</TH><TD ALIGN="right">'+num_format(jbugs)+'</TD><TD ALIGN="right">'+bugPct+'%</TD></TR>')
    outfile.write('  <TR><TH CLASS="sub">'+_('Todo Items')+'</TH><TD ALIGN="right">'+num_format(jtodo)+'</TD><TD ALIGN="right">'+todoPct+'%</TD></TR>')
    outfile.write("</TABLE>\n")


#------------------------------------------------------------------------------
def MakeStatsPage():
    """
    Generate Statistics Page
    """

    if metaInfo.indexPage['stat'] == '': # statistics disabled
        return

    from progress import printProgress
    from os import path as os_path
    printProgress(_('Creating statistics page'), logname)

    outfile = fopen(metaInfo.htmlDir + metaInfo.indexPage['stat'], 'w', metaInfo.encoding)
    outfile.write(MakeHTMLHeader('stat',True,'initCharts();'))
    try:
        copy2(os_path.join(metaInfo.scriptpath,'diagram.js'), os_path.join(metaInfo.htmlDir,'diagram.js'))
    except IOError:
        logger.error(_('I/O error while copying %(source)s to %(target)s'), {'source':_('javascript file'),'target':_('HTML-Dir')})

    generateOutput(outfile)

    outfile.write(MakeHTMLFooter('stat'))
    outfile.close()


