import bisect

from itertools import chain

from pyphen import pyphen
pyphen.language_fallback('en_US')

from fonts import fonttable

from state import noticeboard

from model import kevin
from model import errors
from model.wonder import words, character

hy = pyphen.Pyphen(lang='en_US')

# NOT the same as prose breaks because of '.', ':', etc. *Does not include ''' or '’' because these are found word-internal and when used as quotes, encapsulate single characters*
_breaking_chars = set((' ', '</p>', '<p>', '<br>', '—', '–', '-', ':', '.', ',', ';', '/', '!', '?', '(', ')', '[', ']', '{', '}', '\\', '|', '=', '+', '_', '"', '“', '”' ))

def outside_tag(sequence):
    for i in reversed(range(len(sequence) - 1)):

        if (character(sequence[i]), sequence[i + 1]) == ('<p>', '</p>'):
            del sequence[i:i + 2]

    return sequence

def _fail_class(startindex, l, attempt):
    errors.styleerrors.add_style_error(attempt, l)
    return ('_interface', startindex), fonttable.p_table.get_paragraph('_interface')

def _retrieve_fontclass(P, F, l):
    try:
        FSTYLE = fonttable.table.get_font(P, tuple(F))
    except KeyError:
        # happens if requested style is not defined
        errors.styleerrors.add_style_error(tuple(F), l)
        try:
            FSTYLE = fonttable.table.get_font(P, () )
        except AttributeError:
            FSTYLE = fonttable.table.get_font('_interface', () )
    
    return FSTYLE
            
def _assemble_line(text, startindex, c, l, anchor, stop, y, leading, PP, F, hyphenate=False):
    P = PP[0]
    
    LINE = {
            'c': c,
            'l': l,
            'i': startindex,
            
            'anchor': anchor,
            'stop': stop,
            'y': y,
            'leading': leading,
            
            'hyphen': None,
            
            'P_BREAK': False
            }
    
    # list that contains glyphs
    GLYPHS = []
    
    # start on the anchor
    x = anchor
    n = 0

    # retrieve font style
    FSTYLE = _retrieve_fontclass(P, F, l)

    # takes 1,989 characters starting from startindex
    letters = text[startindex:startindex + 1989]

    for letter in letters:
        CHAR = character(letter)

        if CHAR == '<f>':
            # look for negative classes
            if '~' + letter[1] in F:
                F.remove('~' + letter[1])
            else:
                F.append(letter[1])
                F.sort()
                
            FSTYLE = _retrieve_fontclass(P, F, l)
            
            GLYPHS.append((-4, x, y,  PP, tuple(F), x))
            
        elif CHAR == '</f>':
            try:
                F.remove(letter[1])
            except ValueError:
                F.append('~' + letter[1])
                F.sort()
            
            FSTYLE = _retrieve_fontclass(P, F, l)

            GLYPHS.append((-5, x, y,  PP, tuple(F), x))
            
        elif CHAR == '<p>':
            if GLYPHS:
                break
            else:
                # we don’t load the style because the outer function takes care of that
                GLYPHS.append((
                        -2,                     # 0
                        x - FSTYLE['fontsize'], # 1
                        y,                      # 2
                        
                        PP,                     # 3
                        tuple(F),               # 4
                        x - FSTYLE['fontsize']  # 5
                        ))
        
        elif CHAR == '</p>':
            LINE['P_BREAK'] = True
            GLYPHS.append((-3, x, y,  PP, tuple(F), x))
            break
        
        elif CHAR == '<br>':
            GLYPHS.append((-6, x, y,  PP, tuple(F), x))
            break
        
        else:
            glyphwidth = FSTYLE['fontmetrics'].advance_pixel_width(CHAR) * FSTYLE['fontsize']
            
            GLYPHS.append((
                    FSTYLE['fontmetrics'].character_index(CHAR),    # 0
                    x,                                              # 1
                    y,                                              # 2
                    
                    PP,                                             # 3
                    tuple(F),                                       # 4
                    x + glyphwidth                                  # 5
                    ))

            
            x += glyphwidth
            
            # work out line breaks
            if x > stop:
                n = len(GLYPHS)
                LN = letters[:n]
                if CHAR == ' ':
                    pass
                
                elif ' ' in LN or '-' in LN:
                    i = next(i for i, v in zip(range(len(LN) - 1, 0, -1), reversed(LN)) if v == ' ' or v == '-')
                    
                    ### AUTO HYPHENATION
                    if hyphenate:
                        try:
                            j = letters[i + 1:].index(' ')
                        except ValueError:
                            j = startindex
                        
                        word = ''.join([c if type(c) is str else ' ' for c in letters[i + 1: i + 1 + j] ])
                        for pair in hy.iterate(word):
                            k = len(pair[0])

                            # prevent too-short hyphenations
                            if len(pair[0].replace(' ', '')) < 2 or len(pair[1].replace(' ', '')) < 2:
                                continue
                            
                            try:
                                h_P = GLYPHS[i + k][3][0]
                                h_F = GLYPHS[i + k][4]
                                HFS = _retrieve_fontclass(h_P, h_F, l)
                                    
                                if GLYPHS[i + k][5] + HFS['fontmetrics'].advance_pixel_width('-') * HFS['fontsize'] < stop:
                                    i = i + k
                                    if letters[i] != '-':
                                        LINE['hyphen'] = (
                                                HFS['fontmetrics'].character_index('-'), 
                                                GLYPHS[i][5], # x
                                                GLYPHS[i][2], # y
                                                h_P,
                                                h_F
                                                )
                                    break
                            
                            except IndexError:
                                pass
                    ####################
                    
                    del GLYPHS[i + 1:]

                else:
                    del GLYPHS[-1]
                break
                
            else:
                x += FSTYLE['tracking']
    # n changes
    LINE['j'] = startindex + len(GLYPHS)
    LINE['GLYPHS'] = GLYPHS
    
    return LINE


class Cursor(object):
    def __init__(self, i):
        self.cursor = i
    
    def skip(self, jump, text):
        self.cursor += jump
        # prevent overruns
        if self.cursor > len(text) - 1:
            self.cursor = len(text) - 1
        if character(text[self.cursor]) == '<p>':
            direction = 1
            if jump < 0:
                direction = -1
            while True:
                self.cursor += direction
                if character(text[self.cursor]) != '<p>':
                    break

    def set_cursor(self, index, text):
        self.cursor = index
        self.skip(0, text)

class Text(object):
    def __init__(self, text, channels, cursor, select):
        self.text = kevin.deserialize(text)
        self.channels = channels
        
        self._glyphs = []
        
        self._page_intervals = {}
        # STRUCTURE:
        # PAGE_INTERVALS = {PAGE: [(a, b) u (c, d) u (e, f)] , PAGE: [(g, h) u (i, j)]}
        
        self._sorted_pages = {}
        
        # create cursor objects
        self.cursor = Cursor(cursor)
        self.select = Cursor(select)
        
        # STATS
        self.word_count = '—'
        self.misspellings = []
    
    def _generate_lines(self, l, startindex):
        
        try:
            # ylevel is the y position of the first line to print
            # here we are removing the last existing line so we can redraw that one as well
            li = self._glyphs.pop(-1)
            c = li['c']
            y = li['y'] - li['leading']
            
        except IndexError:
            # which happens if nothing has yet been rendered
            c = 0
            y = self.channels.channels[c].railings[0][0][1]
            p = (self.text[0][1], 0)
            f = []
            try:
                paragraphclass = fonttable.p_table.get_paragraph(p[0])
            except KeyError:
                # happens if requested style is not defined
                p, paragraphclass = _fail_class(startindex, l, (p[0],))
                
        
        page = self.channels.channels[c].page
        page_start_l = l
        
        while True:
            # check for paragraph change
            try:
                if character(self.text[startindex]) != '<p>':
                    # extract last used style
                    f = list(self._glyphs[-1]['GLYPHS'][-1][4])
                    p = self._glyphs[-1]['GLYPHS'][-1][3]
                else:
                    f = []
                    p = (self.text[startindex][1], startindex)
                    
                try:
                    paragraphclass = fonttable.p_table.get_paragraph(p[0])
                except KeyError:
                    # happens if requested style is not defined
                    p, paragraphclass = _fail_class(startindex, l, (p[0],))
                    
            except IndexError:
                pass

            # move down
            y += paragraphclass['leading']
            
            # see if the lines have overrun the portals
            if y > self.channels.channels[c].railings[1][-1][1] and c < len(self.channels.channels) - 1:
                c += 1
                # jump to new entrance
                y = self.channels.channels[c].railings[0][0][1] + paragraphclass['leading']
                
                # PAGINATION
                page_new = self.channels.channels[c].page
                if page_new != page:
                    if page not in self._page_intervals:
                        self._page_intervals[page] = [ (page_start_l, l) ]
                        
                    elif type(self._page_intervals[page][-1]) is int:
                        self._page_intervals[page][-1] = (self._page_intervals[page][-1], l)
                        
                    else:
                        self._page_intervals[page].append( (page_start_l, l) )
                    
                    page = page_new
                    page_start_l = l
                #############

            # generate line objects
            LINE = _assemble_line(
                    self.text, 
                    startindex, 
                    c, 
                    l, 
                    
                    self.channels.channels[c].edge(0, y)[0], 
                    self.channels.channels[c].edge(1, y)[0], 
                    y, 
                    paragraphclass['leading'], 
                    
                    p, 
                    f, 
                    
                    hyphenate = paragraphclass['hyphenate']
                    )
            
            # get the index of the last glyph printed so we know where to start next time
            startindex = LINE['j']
            # check for paragraph break (which returns a negative version of startindex)
            if LINE['P_BREAK']:

                y += paragraphclass['margin_bottom']
                
                if startindex > len(self.text) - 1:
                    self._glyphs.append(LINE)
                    del LINE
                    # this is the end of the document
                    break
            else:
                pass
            l += 1

            self._glyphs.append(LINE)
            del LINE

        if page not in self._page_intervals:
            self._page_intervals[page] = [ (page_start_l, l + 1) ]
            
        elif type(self._page_intervals[page][-1]) is int:
            self._page_intervals[page][-1] = (self._page_intervals[page][-1], l + 1)
            
        else:
            self._page_intervals[page].append( (page_start_l, l + 1) )


        self._line_startindices = [line['i'] for line in self._glyphs]

    def _recalculate(self):
        # clear sorts
        self._sorted_pages = {}
        
        # avoid recalculating lines that weren't affected
        try:
            l = self.index_to_line( min(self.select.cursor, self.cursor.cursor) ) - 1
            if l < 0:
                l = 0
            
            self._page_intervals = { page: [I for I in 
                    [ interval if interval[1] <= l else interval[0] if interval[0] <= l else None for interval in intervals]
                    if I is not None] for page, intervals in self._page_intervals.items() if intervals[0][0] < l}    
            
            startindex = self._glyphs[l]['i']
            self._glyphs = self._glyphs[:l + 1]
            #        i = affected
            self._generate_lines(l, startindex)
        except AttributeError:
            self.deep_recalculate()
        
        # tally errors
        errors.styleerrors.update(l)

    def deep_recalculate(self):
        # clear sorts
        self._glyphs = []
        self._sorted_pages = {}
        self._page_intervals = {}
        
        self._generate_lines(0, 0)
        
        # tally errors
        errors.styleerrors.update(0)


    def _target_line(self, x, y, c=None):

        # get all y values
        clines = [(LINE['y'], LINE['l']) for LINE in self._glyphs if LINE['c'] == c]
        
        yy, ll = zip( * clines)
        # find the clicked line
        lineindex = None
        if y >= yy[-1]:
            lineindex = len(yy) - 1
        else:
            lineindex = bisect.bisect(yy, y)

        return ll[lineindex]
    
    def target_glyph(self, x, y, l=None, c=None):

        if l is None:
            l = self._target_line(x, y, c)

        # find first glyph to the right of click spot
        try:
            glyphindex = bisect.bisect([glyph[1] for glyph in self._glyphs[l]['GLYPHS']], x )
        except IndexError:
            # if l is greater than the length of the document
            l = l % len(self._glyphs)
            glyphindex = bisect.bisect([glyph[1] for glyph in self._glyphs[l]['GLYPHS']], x )
        
        # determine x position of glyph before it
        glyphx = self._glyphs[l]['GLYPHS'][glyphindex - 1][1]
        # if click is closer to it, shift glyph index left one
        try:
            if abs(x - glyphx) < abs(x - self._glyphs[l]['GLYPHS'][glyphindex][1]):
                glyphindex += -1
        except IndexError:
            glyphindex = len(self._glyphs[l]['GLYPHS']) - 1
            
        return glyphindex + self._glyphs[l]['i']

    # get line number given character index
    def index_to_line(self, index):
        return bisect.bisect(self._line_startindices, index) - 1

    def take_selection(self):
        if self.cursor.cursor == self.select.cursor:
            return False
        else:
            self._sort_cursors()

            return self.text[self.cursor.cursor:self.select.cursor]

    def delete(self, start=None, end=None, da=0, db=0):

        self._sort_cursors()

        if start is None:
            start = self.cursor.cursor + da
            
        if end is None:
            end = self.select.cursor + db


        if [character(e) for e in self.text[start:end]] == ['</p>', '<p>']:
            del self.text[start:end]
            
            offset = start - end
        
        else:
            # delete every PAIRED paragraph block
            ptags = [ e for e in self.text[start:end] if character(e) in ('<p>', '</p>') ]
            del self.text[start:end]

            outside = outside_tag(ptags)
            if outside:
                if (outside[0], character(outside[1])) == ('</p>', '<p>'):
                    style = next(c[1] for c in self.text[start::-1] if character(c) == '<p>')
                    if style == outside[1][1]:
                        del outside[0:2]
                        
                self.text[start:start] = outside

            offset = start - end + len(outside)
        
        # fix spelling lines
        self.misspellings = [pair if pair[1] < start else (pair[0] + offset, pair[1] + offset, pair[2]) if pair[0] > end else (0, 0, None) for pair in self.misspellings]

        self._recalculate()
        self.cursor.set_cursor(start, self.text)
        self.select.cursor = self.cursor.cursor

    def insert(self, segment):
        if self.take_selection():
            self.delete(self.cursor.cursor, self.select.cursor)
        
        s = len(segment)
        self.text[self.cursor.cursor:self.cursor.cursor] = segment
        self._recalculate()
        self.cursor.skip(s, self.text)
        self.select.cursor = self.cursor.cursor
        
        # fix spelling lines
        self.misspellings = [pair if pair[1] < self.cursor.cursor else (pair[0] + s, pair[1] + s, pair[2]) if pair[0] > self.cursor.cursor else (pair[0], pair[1] + s, pair[2]) for pair in self.misspellings]
    
    def bridge(self, tag, sign):
        S = self.take_selection()
        if S and '</p>' not in S:
            
            DA = 0
            
            I = self.cursor.cursor
            J = self.select.cursor

            P_1 = I - next(i for i, c in enumerate(self.text[I - 1::-1]) if character(c) == '<p>')
            P_2 = J + self.text[J:].index('</p>') + 1

            if sign:
                CAP = ('</f>', '<f>')
                
                self.text.insert(P_1, (CAP[0], tag))
                DA += 1
                
                P_2 += 1
                I += 1
                J += 1
            else:
                CAP = ('<f>', '</f>')
            
            paragraph = self.text[P_1:P_2]
            
            # if selection falls on top of range
            if character(self.text[I - 1]) == CAP[0]:
                I -= next(i for i, c in enumerate(self.text[I - 2::-1]) if character(c) != CAP[0]) + 1

            if character(self.text[J]) == CAP[1]:
                J += next(i for i, c in enumerate(self.text[J + 1:]) if character(c) != CAP[1]) + 1

            if sign:
                ftags = [(i + P_1, e[0]) for i, e in enumerate(paragraph) if e == (CAP[1], tag) or e == (CAP[0], tag)] + [(P_2, CAP[1])] + [(None, None)]
            else:
                ftags = [(i + P_1, e[0]) for i, e in enumerate(paragraph) if e == (CAP[1], tag) or e == (CAP[0], tag)] + [(None, None)]
            
            pairs = []
            for i in reversed(range(len(ftags) - 2)):
                if (ftags[i][1], ftags[i + 1][1]) == CAP:
                    pairs.append((ftags[i][0], ftags[i + 1][0]))
                    del ftags[i:i + 2]
            
            # ERROR CHECKING
            if ftags != [(None, None)]:
                print ('INVALID TAG SEQUENCE, REMNANTS: ' + str(ftags))
            
            instructions = []
            drift_i = 0
            drift_j = 0

            for pair in pairs:
                if pair[1] <= I or pair[0] >= J:
                    pass
                elif pair[0] >= I and pair[1] <= J:
                    instructions += [(pair[0], False), (pair[1], False)]
                    DA -= 2
                    
                    drift_j += -2
                elif I < pair[1] <= J:
                    instructions += [(pair[1], False), (I, True, (CAP[1], tag) )]
                    if not sign:
                        drift_i += 1
                elif I <= pair[0] < J:
                    instructions += [(pair[0], False), (J, True, (CAP[0], tag) )]
                    if not sign:
                        drift_j += -1
                elif pair[0] < I and pair[1] > J:
                    instructions += [(I, True, (CAP[1], tag) ), (J, True, (CAP[0], tag) )]
                    DA += 2
                    
                    if sign:
                        drift_j += 2
                    else:
                        drift_i += 1
                        drift_j += 1

            if instructions:
                activity = True
                
                instructions.sort(reverse=True)
                for instruction in instructions:
                    if instruction[1]:
                        self.text.insert(instruction[0], instruction[2])
                    else:
                        del self.text[instruction[0]]
            else:
                activity = False
            
            if sign:
                if self.text[P_1] == (CAP[0], tag):
                    del self.text[P_1]
                    DA -= 1
                    
                    drift_i -= 1
                    drift_j -= 1

                else:
                    self.text.insert(P_1, (CAP[1], tag) )
                    DA += 1
                    
                    drift_j += 1

            
            if activity:
                self.cursor.cursor = I + drift_i
                self.select.cursor = J + drift_j
                
                self._recalculate()
                
                # redo spelling for this paragraph
                self.misspellings = [pair if pair[1] < P_1 else
                        (pair[0] + DA, pair[1] + DA, pair[2]) if pair[0] > P_2 else
                        (0, 0, 0) for pair in self.misspellings ]
                # paragraph has changed
                self.misspellings += words(self.text[P_1:P_2 + DA] + ['</p>'], startindex=P_1, spell=True)[1]
                
                return True
            else:
                return False
                
    def _sort_cursors(self):
        if self.cursor.cursor > self.select.cursor:
            self.cursor.cursor, self.select.cursor = self.select.cursor, self.cursor.cursor
    
    def expand_cursors(self):
        # order
        self._sort_cursors()
        
        if character(self.text[self.cursor.cursor - 1]) == '<p>' and character(self.text[self.select.cursor]) == '</p>':
            self.cursor.cursor = 1
            self.select.cursor = len(self.text) - 1
        else:
            self.select.cursor += self.text[self.select.cursor:].index('</p>')
            self.cursor.cursor = self.text_index_location(self.cursor.cursor)[2][1] + 1
    
    def expand_cursors_word(self):

        try:
            # select block of spaces
            if self.text[self.select.cursor] == ' ':
                I = next(i for i, c in enumerate(self.text[self.select.cursor::-1]) if c != ' ') - 1
                self.cursor.cursor -= I
                
                J = next(i for i, c in enumerate(self.text[self.select.cursor:]) if c != ' ')
                self.select.cursor += J
            
            # select block of words
            elif character(self.text[self.select.cursor]) not in _breaking_chars:
                I = next(i for i, c in enumerate(self.text[self.select.cursor::-1]) if character(c) in _breaking_chars) - 1
                self.cursor.cursor -= I
                
                J = next(i for i, c in enumerate(self.text[self.select.cursor:]) if character(c) in _breaking_chars)
                self.select.cursor += J
            
            # select block of punctuation
            else:
                I = next(i for i, c in enumerate(self.text[self.select.cursor::-1]) if character(c) not in _breaking_chars or c == ' ') - 1
                self.cursor.cursor -= I
                
                # there can be only breaking chars at the end (</p>)
                try:
                    J = next(i for i, c in enumerate(self.text[self.select.cursor:]) if character(c) not in _breaking_chars or c == ' ')
                    self.select.cursor += J
                except StopIteration:
                    self.select.cursor = len(self.text) - 1

        except ValueError:
            pass


    ### FUNCTIONS USEFUL FOR DRAWING AND INTERFACE
    
    def line_indices(self, l):
        return self._glyphs[l]['i'], self._glyphs[l]['j']

    # get location of specific glyph
    def text_index_location(self, index, ahead=False):
        l = self.index_to_line(index)
        try:
            glyph = self._glyphs[l]['GLYPHS'][index - self._glyphs[l]['i']]
        except IndexError:
            glyph = self._glyphs[l]['GLYPHS'][-1]
            print ('ahead')
            ahead = True

        return glyph[1:5]

    def stats(self, spell):
        if spell:
            self.word_count, self.misspellings = words(self.text, spell=True)
        else:
            self.word_count = words(self.text)

    def line_data(self, l):
        anchor = self._glyphs[l]['anchor']
        stop = self._glyphs[l]['stop']
        leading = self._glyphs[l]['leading']
        y = self._glyphs[l]['y']
        return anchor, stop, leading, y

    def extract_glyphs(self, refresh=False):

        if refresh:
            self._sorted_pages = {}

        if not self._sorted_pages:

            for page, intervals in self._page_intervals.items():
                sorted_page = {'_annot': [], '_intervals': intervals}
                
                for line in chain.from_iterable(self._glyphs[slice( * interval)] for interval in intervals):

                    p_name = line['GLYPHS'][0][3][0]
                    hyphen = line['hyphen']
                    
                    for glyph in line['GLYPHS']:
                        
                        if glyph[0] < 0:
                            if glyph[0] == -6:
                                sorted_page['_annot'].append( (glyph[0], line['anchor'], line['y'] + line['leading']) + glyph[3:])
                            else:
                                sorted_page['_annot'].append(glyph)
                        else:
                            K = glyph[0:3]
                            f = glyph[4]
                            try:
                                sorted_page[(p_name, f)].append(K)
                            except KeyError:
                                sorted_page[(p_name, f)] = []
                                sorted_page[(p_name, f)].append(K)
                    if hyphen is not None:
                        try:
                            sorted_page[hyphen[3:5]].append((hyphen[0:3]))
                        except KeyError:
                            sorted_page[hyphen[3:5]] = []
                            sorted_page[hyphen[3:5]].append((hyphen[0:3]))
                
                self._sorted_pages[page] = sorted_page

        return self._sorted_pages