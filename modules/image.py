from cairo import ImageSurface, SVGSurface, Context, FORMAT_ARGB32
from urllib.error import URLError

from elements.elements import Inline_SE_element
from model.olivia import Inline

from style import styles

# cairo svg may not have all needed libraries
try:
    from IO.svg import render_SVG
except ImportError:
    render_SVG = None
    
_namespace = 'image'

def _paint_fail_frame(cr, h, k, msg):
    cr.set_font_size(10)
    cr.set_font_face(styles.ISTYLES[('strong',)]['font'])
    
    cr.set_source_rgba(1, 0, 0.1, 0.7)
    cr.rectangle(0, 0, 2 + h*0.1, 2)
    cr.rectangle(0, 2, 2, k*0.1)
    
    cr.rectangle(0, k, 2 + h*0.1, -2)
    cr.rectangle(0, k, 2, -k*0.1)

    cr.rectangle(h, k, -2 - h*0.1, -2)
    cr.rectangle(h, k, -2, -k*0.1)

    cr.rectangle(h, 0, -2 - h*0.1, 2)
    cr.rectangle(h, 0, -2, k*0.1)
    
    cr.move_to(6, 13)
    cr.show_text(msg)
    cr.fill()
        
class Image(Inline_SE_element):
    namespace = _namespace
    tags = {}
    DNA = {}
    
    ADNA = {_namespace: [('src', '', 'str'), ('width', 89, 'int')]}
    documentation = [(0, _namespace)]
    
    def _load(self, A):
        self._tree = A
        
        src, self.width = self._get_attributes(_namespace)
        
        self._surface_cache = None
        A, B = self._load_image_file(src)
        if A:
            self.render_image = B
        else:
            self.h = 89
            self.k = 0
            self._msg = B
            self.render_image = self.paint_Error
            
        self.factor = self.width / self.h

    def _load_image_file(self, src):
        success = False
        if src[-4:] == '.svg':
            if render_SVG is not None:
                try:
                    self._CSVG = render_SVG(src)
                    self.h = int(self._CSVG.h)
                    self.k = int(self._CSVG.k)
                    renderfunc = self.paint_SVG
                    success = True
                except URLError:
                    renderfunc = 'SVG not found'
            else:
                renderfunc = 'CairoSVG not available'
        else:
            try:
                self._surface_cache = ImageSurface.create_from_png(src)
                renderfunc = self.paint_PNG
                self.h = int(self._surface_cache.get_width())
                self.k = int(self._surface_cache.get_height())
                success = True
            except SystemError:
                renderfunc = 'Image not found'
        return success, renderfunc
        
    def paint_SVG(self, cr, render=False):
        cr.scale(self.factor, self.factor)
        if render:
            self._CSVG.paint_SVG(cr)
            return
        elif self._surface_cache is None:
            SC = ImageSurface(FORMAT_ARGB32, self.h, self.k)
            sccr = Context(SC)
            self._CSVG.paint_SVG(sccr)
            self._surface_cache = SC

        cr.set_source_surface(self._surface_cache)
        cr.paint()
    
    def paint_PNG(self, cr, render):
        cr.scale(self.factor, self.factor)
        cr.set_source_surface(self._surface_cache)
        cr.paint()
    
    def paint_Error(self, cr, render):
        _paint_fail_frame(cr, self.width, self.v, self._msg)
    
    def cast_inline(self, LINE, x, y, PP, F, FSTYLE):
        glyphwidth = self.width
        self.v = LINE['leading']
        return _MInline(glyphwidth, LINE['leading'], self.k * self.factor - LINE['leading'], self.render_image, x, y)

    def __len__(self):
        return 7

class _MInline(Inline):
    def __init__(self, width, A, D, draw, x, y):
        Inline.__init__(self, None, width, A, D)
        self._draw = draw
        self._x = x
        self._y = y
    
    def deposit_glyphs(self, repository, x, y):
        repository['_images'].append((self._draw, x + self._x, y - self.ascent + self._y))
