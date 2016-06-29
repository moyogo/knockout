from bulletholes.counter import TCounter as Counter

from meredith.styles import Textstyle

from fonts import hb, get_ot_font, Grid_font

from state import constants

def _create_interface():
    FD = {name: Textstyle(IT) for name, IT in constants.interface_fstyles.items()}
    P = [(FD[F], Counter(tags)) for F, tags in constants.interface_pstyle]
    ui_styles = ((), ('title',), ('strong',), ('label',), ('mono',))
    for U in ui_styles:
        F = Counter(U)
        # iterate through stack
        projection = Textstyle.BASE.copy()
        
        for TS in (TS for TS, tags in P if tags <= F):
            projection.update(TS)

        # set up fonts
        upem, hb_face, projection['__hb_font__'], projection['font'] = get_ot_font(projection['path'])
        projection['__factor__'] = projection['fontsize']/upem
        projection['__gridfont__'] = Grid_font(projection['__hb_font__'], upem)
        
        yield U, projection

ISTYLES = dict(_create_interface())
