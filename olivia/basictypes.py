from edit.arithmetic import NumericStringParser, ParseException

nsp = NumericStringParser()

def interpret_bool(b):
    t = type(b)
    if t in {bool, int}:
        return bool(b)
    elif t is str:
        if b in {'True', '1'}:
            return True
        else:
            return bool(interpret_int(b))
    else:
        return False

def interpret_int(n, fail=0):
    if type(n) is int:
        return n
    elif type(n) is float:
        return int(n)
    else:
        try:
            return int(nsp.eval(n))
        except ParseException:
            return fail
    
def interpret_float(f, fail=0):
    if type(f) in {int, float}:
        return f

    else:
        try:
            v = nsp.eval(f)
            if v.is_integer():
                return int(v)
            else:
                return v
        except ParseException:
            return fail

def interpret_float_tuple(value):
    L = (interpret_float(val, fail=None) for val in value.split(','))
    return (v for v in L if v is not None)