# This library defines a lot of small but useful function, most
# of them known from functional languages such as Haskell.



import itertools



# A handy function which represents the identity function.
def identity (x):
    return x



def eq (a, b):
    return a == b



def neq (a, b):
    return a != b



def lt (a, b):
    return a < b



def gt (a, b):
    return a > b



def add (a, b):
    return a + b



def minus (a, b):
    return a - b



def mul (a, b):
    return a * b



def div (a, b):
    return a / b



def and_op (a, b):
    return (a and b)



def or_op (a, b):
    return a or b



# An alternate implementation of the max function which also accepts
# a mapping function that is applied to each element of the list before
# they are compared to each other. This method returns the original
# element of the list which scored highest compared with all other
# elements of that list.
def _list_opt (lst, cmp, default, key_fn):
    if (not lst):
        return default

    res = lst[0]
    best = key_fn (res)

    for l in lst:
        next = key_fn (l)
        if (next > best):
            best = next
            res = l

    return res



def max (lst, *, default = None, key_fn = identity):
    return _list_opt (lst, gt, default = default, key_fn = key_fn)



def min (lst, *, default = None, key_fn = identity):
    return _list_opt (lst, lt, default = default, key_fn = key_fn)



def dec (i):
    return i - 1



def inc (i):
    return i + 1



def fst (lst):
    return lst[0]



def snd (lst):
    return lst[1]



def head (lst):
    return lst[0]



def tail (lst):
    return lst[1:]



def fold():
    pass



def foldl (lst, fn, default = None):
    if (not lst):
        return default
    lres = fn (default, head (lst))
    return foldl (tail (lst), fn, default = lres)



def foldr (lst, fn, default = None):
    if (not lst):
        return default
    res = foldr (tail (lst), fn, default = head (lst))
    return fn (default, res)



# Groups the elements of a list, The grouping is based
# on equality of whatever the group-function returns. This function
# packs the grouped results into a list of tuples where the first
# element is the criteria that is shared by that group, and a list
# of elements belonging to that group. The list of elements per group
# has the same structure the input list had.
def groupby (lst, group_fn):
    return [(k, [g for g in grp]) for k, grp in itertools.groupby (lst, group_fn)]



# Receives a list of lists and returns a single list with all elements
# of the inner list concatenated into a single list.
def concat (lst):
    res = []
    for l in lst:
        res += l
    return res
    # Alternatively this could be impplemented like
    #return foldl (lst, add, [])

