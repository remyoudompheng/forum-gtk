
# Structure of pstats.Stats().stats 
#  { func: 
#          0 cc: external calls
#          1 nc: number of calls
#          2 tt: total time
#          3 ct: cumulative time
#          4 callers = {func: nc, cc, tt, ct}
#  func = filename, line, function name

# see /usr/lib/python2.5/cProfile.py
# see /usr/lib/python2.5/pstats.py

class KCacheGrind(object):
    def __init__(self, pstats_item):
        pstats_item.calc_callees()
        self.revdata = pstats_item.stats
        self.data = pstats_item.all_callees
        self.out_file = None

    def output(self, out_file):
        self.out_file = out_file
        print >> out_file, 'events: Ticks'
        self._print_summary()
        for func, stat in self.revdata.iteritems():
            self._entry(func, stat)

    def _print_summary(self):
        max_cost = 0
        for entry in self.revdata.itervalues():
            totaltime = int(entry[2] * 1000)
            max_cost = max(max_cost, totaltime)
        print >> self.out_file, 'summary: %d' % (max_cost,)

    def _entry(self, func, stat):
        out_file = self.out_file
        inlinetime = int(stat[2] * 1000)
        print >> out_file, 'fi=%s' % (func[0],)
        print >> out_file, 'fn=%s %s:%d' % (func[2], func[0], func[1])
        print >> out_file, '%d %d' % (func[1], inlinetime)
        # recursive calls are counted in entry.calls
        if self.data[func]:
            calls = self.data[func]
        else:
            calls = {}
        
        lineno = func[1]
        for subfunc, subdata in calls.iteritems():
            self._subentry(lineno, subfunc, subdata)
        print >> out_file

    def _subentry(self, lineno, subfunc, subdata):
        out_file = self.out_file
        totaltime = int(subdata[2] * 1000)
        print >> out_file, 'cfn=%s %s:%d' % (subfunc[2],subfunc[0],subfunc[1])
        print >> out_file, 'cfi=%s' % (subfunc[0])
        print >> out_file, 'calls=%d %d' % (subdata[0], subfunc[1])
        print >> out_file, '%d %d' % (lineno, totaltime)
