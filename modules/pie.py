from math import pi, atan2
from itertools import chain, accumulate
from bisect import bisect

from model.olivia import Atomic_text, Block
from edit.paperairplanes import interpret_rgba, interpret_float
from IO.xml import print_attrs, print_styles
from elements.elements import Block_element

_namespace = 'mod:pie'

class _Pie(object):
    def __init__(self, slices, radius, active=0):
        self.slices = slices
        self.active = active
        self.r = radius
        self.center = (0, 0)

class PieChart(Block_element):
    namespace = _namespace
    tags = {_namespace + ':' + T for T in ('slice',)}
    DNA = {'slice': {}}
            
    def _load(self, L):
        self._tree = L
        self.PP = L[0][2]
        radius = interpret_float(L[0][1].get('radius', 89))
        slices, labels = zip( * (( (interpret_float(tag[1]['prop']), interpret_rgba(tag[1]['color'])), E) for tag, E in L[1] if tag[0] == self.namespace + ':slice'))
        total = sum(P for P, C in slices)
                       # percentage | arc length | color
        self._pie = _Pie([(P/total, P/total*2*pi, C) for P, C in slices], radius)
        self._FLOW = [Atomic_text(text) for text in labels]
        
    def represent(self, indent):
        name, attrs = self._tree[0][:2]
        attrs.update(print_styles(self.PP))
        lines = [[indent, print_attrs(name, attrs)]]
        for tag, E in self._tree[1]:
            lines.append([indent + 1, print_attrs( * tag)])
            lines.extend(self._SER(E, indent + 2))
            lines.append([indent + 1, '</' + tag[0] + '>'])
        lines.append([indent, '</' + self.namespace + '>'])
        return lines

    def fill(self, bounds, c, y):
        r = self._pie.r
        top = y
        y += 22
        left, right = bounds.bounds(y + r)
        px = (right + left)/2
        py = y + r
        for S in self._FLOW:
            S.cast(bounds, c, y)
            y += 20
        bottom = py + r + 22
        
        self._pie.center = px, py
        return _MBlock(self._FLOW, (top, bottom, left, right), self._pie, self.PP)

class _MBlock(Block):
    def __init__(self, FLOW, box, pie, PP):
        Block.__init__(self, FLOW, * box, PP)
        self._slices = pie.slices
        self._slices_t = list(accumulate(s[1] for s in self._slices))
        self._pie = pie
    
    def _print_pie(self, cr):
        x, y = self._pie.center
        r = self._pie.r
        t = 0
        for i, S in enumerate(self._slices):
            percent, arc, color = S
            cr.move_to(x, y)
            cr.arc(x, y, r, t, t + arc)
            cr.close_path()
            cr.set_source_rgba( * color)
            cr.fill()
            t += arc

    def _print_annot(self, cr, O):
        if O is self._FLOW[self._pie.active]:
            x, y = self._pie.center
            r = self._pie.r
            i = self._pie.active
            t = self._slices_t[i - 1]
            percent, arc, color = self._slices[i]
            cr.set_source_rgba( * color)
            cr.set_line_width(2)
            cr.arc(x, y, r + 13, t, t + arc)
            cr.stroke()

    def _target_slice(self, x, y):
        px, py = self._pie.center
        r = self._pie.r
        dx = x - px
        dy = y - py
        if dx**2 + dy**2 > (r + 13)**2:
            return self._pie.active
        else:
            t = atan2(dy, dx)
            if t < 0:
                t += 2*pi
            return bisect(self._slices_t, t)
    
    def I(self, x, y):
        s = self._target_slice(x, y)
        self._pie.active = s
        return self._FLOW[s]
    
    def deposit(self, repository):
        for A in self._FLOW:
            A.deposit(repository)
        repository['_paint'].append(self._print_pie)
        repository['_paint_annot'].append(self._print_annot)
