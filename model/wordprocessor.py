from model.text_t import character, _breaking_chars

_prose = set('ABCDEFGHIJKLMNOPGRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789&@#$- ')
# these characters get read as word-breaks in speech
_breaking_prose = set(('</p>', '<br>', '—', '–', '/', '(', ')', '\\', '|', '=', '+', '_'))

def check_spelling(word):
    if word.isalpha():
        return True
    else:
        return False

def words(text, spell=False):
    words = ''.join([e if (type(e) is str and e in _prose) else ' ' if (type(e) is str and e in _breaking_prose) else '' for e in text ]).split()
    word_count = len(words)
    
    if spell:
        misspelled = []
        for word in words:
            hyphens = word.count('-')
            if hyphens == 0:
                if not check_spelling(word):
                    misspelled.append(word)
            elif hyphens == 1:
                fragments = word.split('-')
                if not check_spelling(fragments[0]):
                    misspelled.append(fragments[0])
                if not check_spelling(fragments[1]):
                    misspelled.append(fragments[1])
        
        misspelled_indices = []
        for m in misspelled:
            misspelled_indices += find_word(m, text)
        
        return word_count, misspelled_indices
    else:
        return word_count

def find_word(word, text):
    results=[]
    word_length=len(word)
    
    for I in (i for i, e in enumerate(text) if e == word[0]):
        try:
            J = next(i for i, c in enumerate(text[I:word_length + 89]) if character(c) in _breaking_chars)
        except StopIteration:
            continue
        
        if ''.join([a for a in text[I:J] if type(a) is str and len(a) == 1]) == word:
            results.append((I, J))

    return results