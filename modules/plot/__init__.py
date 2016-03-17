from bisect import bisect
from itertools import chain

from model.olivia import Block, Flowing_text
from elements.elements import Block_element
from model.george import Subcell
from .cartesian import namespace, X, Y, axismembers, Cartesian2
from .data import Data

from . import scatterplot, f, histogram

class Plot_key(object):
    def __init__(self, keys, subcell, c, top, py, overlay):
        if keys:
            texts, self._icons, colors = zip( * keys )
            self.color = colors[-1]

            self._i = len(texts) - 1
            y = top
            ky = []
            for FTX in texts:
                FTX.layout(subcell, c, y, overlay)
                leading1 = FTX.LINES[0] ['leading']
                leading2 = FTX.LINES[-1]['leading']
                ky.append((int(y - py + leading1*0.25), int(FTX.y - py + leading2*0.25)))
                y = FTX.y + leading2*0.25
            
            self._ky = ky
            self._ki = [k[1] for k in ky]
        else:
            self._i = -1
            self.color = (0, 0, 0, 1)
            self._icons = ()
            self._ky = []
            self._ki = []
    
    def draw(self, cr):
        for icon, cell in zip(self._icons, self._ky):
            icon(cr, * cell)
    
    def target(self, y):
        return 2 + min(self._i, max(0, bisect(self._ki, y)))

class Plot(Block_element):
    nodename = namespace
    ADNA = [('height', 89, 'int'), ('tickwidth', 0.5, 'float')]
    DNA = {'x': {}, 'y': {}, 'dataset': {}, 'num': {}}
    
    def _load(self):
        self.X, self.Y = self.find_nodes(X, Y)
        self.X.enum()
        self.Y.enum()
        
        self._FLOW = [Flowing_text(A.content) for A in (self.X, self.Y)]
        
        AXES = Cartesian2(self.X, self.Y)
        self._datasets = [PL.unit(AXES) for PL in self.filter_nodes(Data, inherit=True)]
        self._keys = list(chain.from_iterable(PL.key() for PL in self._datasets))
        self._FLOW += [K[0] for K in self._keys]
    
    def ink_graph(self, cr):
        cr.set_source_rgb(0, 0, 0)
        self.X.draw(cr, self['tickwidth'])
        self.Y.draw(cr, self['tickwidth'])
        cr.fill()
        
        for PL in self._datasets:
            PL.draw(cr)
        self._KEY.draw(cr)
    
    def ink_annot(self, cr):
        cr.set_source_rgba( * self._KEY.color )
        
    def regions(self, x, y):
        if y > 0:
            return 0
        elif y < -self['height'] and x < self._yaxis_div:
            return 1
        else:
            return self._KEY.target(y)
    
    def transform_data(self, width):
        pass
    
    def typeset(self, bounds, c, y, overlay):
        P_x, P_y, P_key, = self.styles(overlay, 'x', 'y', 'dataset')
        F_num, = self.styles(None, 'num')

        top = y
        height = self['height']
        left, right = bounds.bounds(y + height/2)

        # y axis
        self._FLOW[1].layout(Subcell(bounds, -0.15, 0.15), c, y, P_y)
        y = self._FLOW[1].y
        
        px = left
        py = int(y + height) + 10
        
        w = right - left
        self._yaxis_div = w*0.15
        self.X.freeze(w)
        self.Y.freeze(height)
        for PL in self._datasets:
            PL.freeze(w, -height)
        
        MONO = list(chain.from_iterable(A.print_numbers({'R': 0, 'l': 0, 'c': c, 'page': bounds.page}, self.PP, F_num) for A in (self.X, self.Y)))
        
        # x axis
        self._FLOW[0].layout(bounds, c, py + 20, P_x)
        
        self._KEY = Plot_key(self._keys, Subcell(bounds, 0.2, 1), c, top, py, P_key)
        
        return GraphBlock(self._FLOW, MONO, 
                    (top, self._FLOW[0].y, left, right), 
                    self.ink_graph, self.ink_annot, 
                    (px, py), self.regions, self.PP)
        
class GraphBlock(Block):
    def __init__(self, FLOW, MONO, box, draw, draw_annot, origin, regions, PP):
        Block.__init__(self, FLOW, * box, PP)
        self._origin = origin
        self._MONO = MONO
        self._draw = draw
        self._draw_annot = draw_annot
        self._regions = regions

    def _print_annot(self, cr, O):
        if O in self._FLOW:
            self._draw_annot(cr)
            self._handle(cr)
            cr.fill()
    
    def target(self, x, y):
        if x <= self['right']:
            dx, dy = self._origin
            return self._regions(x - dx, y - dy)
        else:
            return None
    
    def deposit(self, repository):
        repository['_paint'].append((self._draw, * self._origin )) # come before to avoid occluding child elements
        repository['_paint_annot'].append((self._print_annot, 0, 0))
        for A in self._FLOW:
            A.deposit(repository)
        for A in self._MONO:
            A.deposit(repository, * self._origin)

members = [Plot] + axismembers
members.extend(chain.from_iterable(D.members for D in (scatterplot, f, histogram)))
inline = False