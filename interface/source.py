from itertools import chain, accumulate
from bisect import bisect

from interface.base import Base_kookie, accent
from style.styles import ISTYLES

def _chunks(L, n):
    br = [i + 1 for i, v in enumerate(L) if v == '\n']
    for line in (L[i : j - 1] for i, j in zip([0] + br, br + [len(L)])):
        for i in range(0, len(line), n):
            yield line[i : i + n], not bool(i)

def _paint_select(cl, sl, cx, sx, left, right):
    select = []
    if cl == sl:
                           # y, x1, x2
        select.append((cl, cx, sx))
    else:
        (cl, cx), (sl, sx) = sorted(((cl, cx), (sl, sx)))
        select.append((cl, cx, right))
        select.extend(((l, left, right) for l in range(cl + 1, sl)))
        select.append((sl, left, sx))
    return select
            
class Rose_garden(Base_kookie):
    def __init__(self, x, y, width, callback, value_acquire):        
        self._callback = callback
        self._value_acquire = value_acquire

        self.font = ISTYLES[('mono',)]
        fontsize = self.font['fontsize']
        self._K = self.font['fontmetrics'].advance_pixel_width(' ') * fontsize
        self._leading = int(fontsize * 1.3)
        
        self._chars = int((width - 30) // self._K)
        width = int(self._chars * self._K + 30)

        Base_kookie.__init__(self, x, y, width, 0, font=None)
        
        self._SYNCHRONIZE()
        
        self.is_over_hover = self.is_over
        
        # cursors
        self._i = 0
        self._j = 0
        
        self._scroll = 0

    def _ACQUIRE_REPRESENT(self):
        self._VALUE = self._value_acquire()
        self._GLYPHS = list(self._VALUE) + [None]
        self._grid_glyphs(self._GLYPHS)

    def _SYNCHRONIZE(self):
        self._ACQUIRE_REPRESENT()
        self._PREV_VALUE = self._VALUE

    def _grid_glyphs(self, glyphs):
        x = self._x
        y = self._y
        
        K = self._K
        leading = self._leading
        FMX = self.font['fontmetrics'].character_index
        
        lines = list(_chunks(self._GLYPHS, self._chars))
        self._IJ = [0] + list(accumulate(len(l) + 1 for l, br in lines))
        self._y_bottom = y + leading * len(lines)
        
        y += leading
        xd = x + 30
        self._LL = [[(FMX(character), xd + i*K, y + l*leading) for i, character in enumerate(line)] for l, (line, br) in enumerate(lines)]
        N = zip(accumulate(br for line, br in lines), enumerate(lines))
        self._numbers = [[(FMX(character), x + i*K, y + l*leading) for i, character in enumerate(str(int(N)))] for N, (l, (line, br)) in N if br]
    
    def _target(self, x, y):
        y -= self._y
        x -= self._x + 30
        
        l = min(max(int(y // self._leading), 0), len(self._LL) - 1)
        di = int(round(x / self._K))
        i = self._IJ[l]
        j = self._IJ[l + 1]
        g = min(max(di + i, i), j - 1)
        return g
    
    def is_over(self, x, y):
        return self._y <= y <= self._y_bottom and self._x - 10 <= x <= self._x_right + 10

    def _entry(self):
        return ''.join(self._GLYPHS[:-1])
    
    # typing
    def type_box(self, name, char):
        pass

    def focus(self, x, y):
        self._i = self._target(x, y)
        self._j = self._i

    def focus_drag(self, x, y):
        j = self._target(x, y)
        
        # force redraw if cursor moves
        if self._j != j:
            self._j = j
            return True
        else:
            return False
    
    def defocus(self):
        self._active = None
        self._dropdown_active = False
        self._scroll = 0
        # dump entry
        self._VALUE = self._entry()
        if self._VALUE != self._PREV_VALUE:
            self._BEFORE()
            self._callback(self._domain(self._VALUE), * self._params)
            self._SYNCHRONIZE()
            self._AFTER()
        else:
            return False
        return True

    def hover(self, x, y):
        return 1
    
    def _cursor_location(self, i):
        l = bisect(self._IJ, i) - 1
        gx = (i - self._IJ[l]) * self._K
        return l, int(self._x + 30 + gx), self._y + self._leading * l

    def draw(self, cr, hover=(None, None)):
        self._render_fonts(cr)
        # line numbers
        cr.set_source_rgb(0.7, 0.7, 0.7)
        cr.show_glyphs(chain.from_iterable(self._numbers))
        cr.fill()
        
        # highlight
        cr.set_source_rgba(0, 0, 0, 0.1)
        leading = self._leading
        cl, cx, cy = self._cursor_location(self._i)
        sl, sx, sy = self._cursor_location(self._j)

        for l, x1, x2 in _paint_select(cl, sl, cx, sx, self._x + 30, self._x_right):
            cr.rectangle(x1, self._y + l*leading, x2 - x1, leading)
        cr.fill()

        # text
        cr.set_source_rgb(0, 0, 0)
        cr.show_glyphs(chain.from_iterable(self._LL))
        cr.fill()

        # cursor
        cr.set_source_rgb( * accent)
        cr.rectangle(cx - 1, cy, 2, leading)
        cr.rectangle(sx - 1, sy, 2, leading)
        cr.fill()
