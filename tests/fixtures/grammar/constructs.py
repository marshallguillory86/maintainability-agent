"""Every control-flow construct the Python language reference defines.

One function per construct, so a disagreement names the construct rather
than a file total. Written from the reference's "Compound statements"
chapter and the "Boolean operations", "Conditional expressions" and
"Displays for lists, sets and dictionaries" sections of the expressions
chapter — not from recollection, which is how D112, D113 and D114 got in.

The last function is deliberately branchless: a construct that is *not* a
decision has to stay uncounted, and `with` is the one most often mistaken
for one because it has a suite.
"""


def if_statement(flag):
    if flag:
        return "yes"
    return "no"


def elif_chain(value):
    if value == 1:
        return "one"
    elif value == 2:
        return "two"
    elif value == 3:
        return "three"
    return "many"


def while_loop(limit):
    total = 0
    while total < limit:
        total += 1
    return total


def for_loop(items):
    total = 0
    for item in items:
        total += item
    return total


def try_except(source):
    try:
        return source()
    except ValueError:
        return "value"
    except KeyError:
        return "key"


def boolean_and(left, right):
    return left and right


def boolean_or(left, right):
    return left or right


def conditional_expression(flag):
    return "yes" if flag else "no"


def comprehension(items):
    return [item * 2 for item in items if item]


def match_statement(value):
    match value:
        case 1:
            return "one"
        case 2:
            return "two"
        case _:
            return "many"


def with_statement(handle):
    with handle as opened:
        return opened.read()
