from math import pi, sqrt
from itertools import chain

from state import noticeboard
from state.constants import accent_light

from olivia.basictypes import interpret_int

from meredith.box import Null

from IO import un

def _draw_broken_bar(cr, x1, y1, x2, color_rgba, top):
    
    cr.set_source_rgba( * color_rgba)
    width = x2 - x1

    cross = 6
    gap = 6
    cr.rectangle(x1 - cross - gap, y1, cross, 1)
    cr.rectangle(x1, y1 - cross*top - gap*(top*2 - 1), 1, cross)

    cr.rectangle(x2 + gap, y1, cross, 1)
    cr.rectangle(x2, y1 - cross*top - gap*(top*2 - 1), 1, cross)
    cr.fill()
    
    cr.set_line_width(1)
    cr.set_dash([2, 5], 0)
    cr.move_to(x1 + gap, y1 + 0.5)
    cr.line_to(x2 - gap, y1 + 0.5)
    cr.stroke()
    
    cr.set_dash([], 0)

def _draw_portals(cr, frame, Tx, Ty, color1, color2):
    page = frame.page
             
    _draw_broken_bar(cr,
            round( Tx(frame[0][0][0] , page) ), 
            round( Ty(frame[0][0][1] , page) ),
            round( Tx(frame[1][0][0] , page) ),
            color1,
            top = 1
            )
    _draw_broken_bar(cr,
            round( Tx(frame[0][-1][0] , page) ), 
            round( Ty(frame[1][-1][1] , page) ),
            round( Tx(frame[1][-1][0] , page) ),
            color2,
            top = 0
            )

def overflow(cr, frames, Tx, Ty):
    if frames.overflow:
        frame = frames[-1]
        cr.set_source_rgba(1, 0, 0.1, 0.8)
        cr.set_line_width(2)
        x = round((Tx(frame[0][-1][0] , frame.page) + Tx(frame[1][-1][0], frame.page))*0.5)
        y = round(Ty(frame[0][-1][1] , frame.page))
        cr.move_to(x - 10, y + 10)
        cr.rel_line_to(10, 10)
        cr.rel_line_to(10, -10)
        cr.stroke()

class Frame_cursor(Null):
    name = 'framecursor'
    def __init__(self, KT, attrs, content=None):
        self.__orig_info = (interpret_int(attrs['section']), 
                            interpret_int(attrs['frame']))
        self.KT = KT
    
    def reactivate(self, info=None):
        self.BODY       = self.KT.BODY
        self.normalize  = self.KT.BODY.normalize_XY
        if info is None:
            info = self.__orig_info
        self.initialize_from_params( * info )
    
    def initialize_from_params(self, s, c):
        self._mode = 'outlines'
        if s is None:
            s = 0
        if c is None:
            c = 0
        
        try:
            self.section = self.BODY.content[s]
        except IndexError:
            self.section = self.BODY.content[0]
        self._FRAMES = self.section['frames']

        try:
            frame = self._FRAMES[c]
        except IndexError:
            frame = self._FRAMES[0]
            c = 0

        self.PG = frame.page
        self.HPG = frame.page
        self._selected_point = [c, None, None]
        self._selected_portal = (None, None, None)

        # these are stateful
        self._hover_point = (None, None, None)
        self._hover_portal = (None, None)
                        
        self._grid_controls = self.BODY['grid']
        self.render_grid = self._grid_controls.render

    def print_A(self):
        return ' '.join(chain((self.name,), (''.join((a, '="', str(v), '"')) for a, v in zip(('section', 'frame'), self.at()))))
    
    def at(self):
        return self.BODY.content.index(self.section), self._selected_point[0]

    def add_frame(self):
        self.section['frames'].add_frame()
        self.section.layout()

    def target_select(self, x, y):
        p, c, r, i = self._FRAMES.which_point(x, y, 20)
        if c is not None:
            self.HPG = p
            xp, yp = self.normalize(x, y, p)
            if r is None:
                ptype, dpx, dpy = self._FRAMES[c].which_portal(xp, yp, radius=5)
                self._hover_portal = (c, ptype)
        self._hover_point = c, r, i

    def target(self, x, y):
        p, c, r, i = self._FRAMES.which_point(x, y, 20)
        self._selected_point = [c, r, i]
        if c is not None:
            self.PG = p
            xp, yp = self.normalize(x, y, p)
            if r is None:
                self._selected_portal = self._FRAMES[c].which_portal(xp, yp, radius=5)
            else:
                self._selected_portal = (None, 0, 0)
            return xp, yp
        
        # try different tract
        for section in self.BODY.content:
            p, c, r, i = section['frames'].which_point(x, y, 20)
            if c is not None:
                self.PG = p
                self._selected_point = [c, r, i]
                self.section = section
                self._FRAMES = section['frames']
                return self.normalize(x, y, p)
        
        self._selected_portal = (None, 0, 0)
        return self.normalize(x, y, self.PG)

    def press(self, x, y, name):
        un.history.undo_save(3)
        
        self._grid_controls.clear_selection()
        xn, yn = self.target(x, y)
        c, r, i = self._selected_point
        portal = self._selected_portal
        self._add_point = None
        if c is None:
            if name != 'ctrl':
                self._FRAMES.clear_selection()
            
            if self._grid_controls.press(xn, yn):
                self._mode = 'grid'
                return True
            else:
                return False
            
        else:
            self._mode = 'outlines'
            #clear selection
            if name != 'ctrl' and not self._FRAMES.is_selected(c, r, i):
                self._FRAMES.clear_selection()
            
            # MAKE SELECTIONS
            if i is not None:
                self._FRAMES.make_selected(c, r, i, name)
                self._selected_portal = (None, None, None)

            elif portal[0] == 'entrance':
                self._FRAMES.make_selected(c, 0, 0, name)
                self._FRAMES.make_selected(c, 1, 0, name)
                r = 0
                i = 0
            elif portal[0] == 'portal':
                self._FRAMES.make_selected(c, 0, -1, name)
                self._FRAMES.make_selected(c, 1, -1, name)
                r = 1
                i = len(self._FRAMES[c][1]) - 1
            
            elif r is not None:
                # prepare to insert point if one was not found
                self._add_point = c, r, yn, name
            
            if i is not None:
                self._sel_locale = tuple(self._FRAMES[c][r][i][:2])
                self._release_locale = self._sel_locale

            return True
    
    def dpress(self):
        if self._add_point is not None:
            c, r, yn, name = self._add_point
            i = self._FRAMES[c].insert_point(r, yn)
            self._FRAMES.make_selected(c, r, i, name)
            self._selected_point[2] = i
            self._release_locale = None
    
    def press_motion(self, x, y):
        x, y = self.normalize(x, y, self.PG)
        if self._mode == 'outlines':
            c, r, i = self._selected_point
            portal, px, py = self._selected_portal
            
            if i is not None or portal is not None:
                if i is not None:
                    x0, y0 = self._FRAMES[c][r][i][:2]
                    self._FRAMES.translate_selection(x, y, x0, y0)
                    
                    anchor = tuple(self._FRAMES[c][r][i][:2])

                elif portal == 'entrance':
                    x0, y0 = self._FRAMES[c][0][0][:2]
                    self._FRAMES.translate_selection(x - px, y - py, x0, y0)
                    
                    anchor = tuple(self._FRAMES[c][0][0][:2])

                elif portal == 'portal':
                    x0, y0 = self._FRAMES[c][1][-1][:2]
                    self._FRAMES.translate_selection(x - px, y - py, x0, y0)
                
                    anchor = tuple(self._FRAMES[c][1][-1][:2])
                
                if self._sel_locale != anchor:
                    self._sel_locale = anchor
                    noticeboard.redraw_becky.push_change()
 
        elif self._mode == 'grid':
            # translate grid lines
            self._grid_controls.move_grid(x, y)

    def release(self):
        self._grid_controls.release()

        c, r, i = self._selected_point
        portal, px, py = self._selected_portal

        if i is not None or portal is not None:
            self._FRAMES.fix(c)
            
            if i is not None:
                anchor = tuple(self._FRAMES[c][r][i][:2])

            if portal == 'entrance':
                anchor = tuple(self._FRAMES[c][0][0][:2])

            elif portal == 'portal':
                anchor = tuple(self._FRAMES[c][1][-1][:2])

            if self._release_locale != anchor:
                self._release_locale = anchor
                self.section.layout()
                return
        
        un.history.pop()
    
    def key_input(self, name):
        if name in ['BackSpace', 'Delete']:
            if self._mode == 'outlines':
                c, r, i = self._selected_point
                portal, px, py = self._selected_portal
                if portal is not None or (c is not None and i is None):
                    un.history.undo_save(3)
                    
                    # delete channel
                    del self._FRAMES[c]
                    # wipe out entire tract if it's the last one
                    if not self._FRAMES:
                        old_tract = self.section
                        self.BODY.content.remove(old_tract)
                        self.section = self.BODY.content[-1]
                        self._FRAMES = self.section['frames']
                
                else:
                    un.history.undo_save(3)
                    if not self._FRAMES.delete_selection():
                        un.history.pop()
                
                self._FRAMES.fix()
                self.section.layout()
            
            elif self._mode == 'grid':
                self._grid_controls.del_grid()
                
        elif name == 'All':
            self._FRAMES.expand_selection(self._selected_point[0])
            
    
    def hover(self, x, y, hovered=[None, None]):
        self.target_select(x, y)
        if self._hover_point != hovered[0]:
            noticeboard.redraw_becky.push_change()
            hovered[0] = self._hover_point
        elif self._hover_portal != hovered[1]:
            noticeboard.redraw_becky.push_change()
            hovered[1] = self._hover_portal

    def render(self, cr, Tx, Ty, A=1, frames=None):
        if frames is None:
            em = int(sqrt(A)*15)
            cr.set_font_size(em)
            for c, frame in enumerate(self._FRAMES):
                page = frame.page
                
                if c == self._hover_portal[0] and self._hover_portal[1] is not None:
                    if 'entrance' == self._hover_portal[1]:
                        colors = (0.3, 0.3, 0.3, 1), (1, 0, 0.1, 0.5)
                    elif 'portal' == self._hover_portal[1]:
                        colors = (0.3, 0.3, 0.3, 0.5), (1, 0, 0.1, 1)
                else:
                    colors = (0.3, 0.3, 0.3, 0.5), (1, 0, 0.1, 0.5)
                _draw_portals(cr, frame, Tx, Ty, * colors )
                
                # draw railings
                if c == self._selected_point[0]:
                    cr.set_source_rgba( * accent_light )
                elif c == self._hover_point[0]:
                    cr.set_source_rgba( * accent_light, 0.7)
                else:
                    cr.set_source_rgba( * accent_light, 0.5)
                
                railingpoints = tuple(tuple((Tx(p[0], page), Ty(p[1], page), p[2]) for p in railing) for railing in frame)
                
                for r, points in enumerate(railingpoints):
                    cr.move_to(points[0][0], points[0][1])
                    
                    for x, y, a in points:
                        cr.line_to(x, y)
                    
                    cr.set_line_width(2)
                    cr.stroke()

                    # draw selections
                    for i, (x, y, a) in enumerate(points):
                        cr.arc(x, y, 3, 0, 2*pi)
                        if (c, r, i) == self._hover_point:
                            cr.set_source_rgba( * accent_light , 0.5)
                            cr.fill()
                            cr.set_source_rgba( * accent_light , 0.7)
                        else:
                            cr.fill()
                        if a:
                            cr.arc(x, y, 5, 0, 2*pi)
                            cr.set_line_width(1)
                            cr.stroke()
            
                cr.move_to(railingpoints[0][0][0] - 1.5*em, railingpoints[0][0][1] + 0.7*em)
                cr.show_text(str(c))
                cr.move_to(railingpoints[0][-1][0] - 1.5*em, railingpoints[0][-1][1])
                cr.show_text(str(c + 1))
            
            cr.set_line_width(1)
            for frame in chain.from_iterable(section['frames'] for section in self.BODY.content if section is not self.section):
                page = frame.page
                
                cr.set_source_rgba(0.3, 0.3, 0.3, 0.3)
                
                pts = (( Tx(p[0], page), Ty(p[1], page) ) for p in chain(frame[0], reversed(frame[1])))
                cr.move_to( * next(pts) )
                for point in pts:
                    cr.line_to( * point )
                
                cr.close_path()
                
            cr.stroke()
            overflow(cr, self._FRAMES, Tx, Ty)
            
        else:
            for frame in frames:
                _draw_portals(cr, frame, Tx, Ty, (0.3, 0.3, 0.3, 0.5), (1, 0, 0.1, 0.5))
            
            overflow(cr, frames, Tx, Ty)

members = Frame_cursor,
