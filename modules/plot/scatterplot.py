from math import pi
from .data import Data

class Scatterplot(Data):
    nodename = 'mod:scatter'
    ADNA = [('data', (), '2D'), ('color', '#ff3085', 'rgba'), ('radius', 2, 'float')]

    def unit(self, axes):
        data, self.color, self._r = self.get_attributes()
        project = axes.project
        self._unitpoints = [project(x, y) for x, y in data]
        return self
    
    def draw(self, cr):
        cr.set_source_rgba( * self.color )
        circle_t = 2*pi
        r = self._r
        for x, y in self._points:
            cr.move_to(x, y)
            cr.arc(x, y, r, 0, circle_t)
            cr.close_path()
        cr.fill()
    
    def freeze(self, h, k):
        self._right = h
        self._points = [(x*h, y*k) for x, y in self._unitpoints]

members = [Scatterplot]
