"""
Small scanf implementation.

Python has powerful regular expressions, but sometimes they are totally overkill
when you just want to parse a simple-formatted string.
C programmers use the scanf-function for these tasks (see link below).

This implementation of scanf translates the simple scanf-format into
regular expressions. Unlike C you can be sure that there are no buffer overflows
possible.

For more information see
  * http://www.python.org/doc/current/lib/node49.html
  * http://en.wikipedia.org/wiki/Scanf

Original code from:
    http://code.activestate.com/recipes/502213-simple-scanf-implementation/

Modified original to make the %f more robust, as well as added %* modifier to
skip fields.

Adapted from:
    https://github.com/joshburnett/scanf
"""
import re
from typing import Tuple, Any

try:
    from functools import lru_cache
except ImportError:
    from backports.functools_lru_cache import lru_cache

DEBUG = False

# As you can probably see it is relatively easy to add more format types.
# Make sure you add a second entry for each new item that adds the extra
# few characters needed to handle the field omission.
scanf_translate = [
    (re.compile(_token), _pattern, _cast) for _token, _pattern, _cast in [
        ("%c", "(.)", lambda x: x),
        ("%\*c", "(?:.)", None),

        ("%(\d)c", "(.{%s})", lambda x: x),
        ("%\*(\d)c", "(?:.{%s})", None),

        ("%(\d)[di]", "([+-]?\d{%s})", int),
        ("%\*(\d)[di]", "(?:[+-]?\d{%s})", None),

        ("%[di]", "([+-]?\d+)", int),
        ("%\*[di]", "(?:[+-]?\d+)", None),

        ("%u", "(\d+)", int),
        ("%\*u", "(?:\d+)", None),

        ("%[fgeE]", "([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)", float),
        ("%\*[fgeE]", "(?:[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)", None),

        ("%s", "(\S+)", lambda x: x),
        ("%\*s", "(?:\S+)", None),

        ("%([xX])", "(0%s[\dA-Za-f]+)", lambda x: int(x, 16)),
        ("%\*([xX])", "(?:0%s[\dA-Za-f]+)", None),

        ("%o", "(0[0-7]*)", lambda x: int(x, 8)),
        ("%\*o", "(?:0[0-7]*)", None),
    ]]

# Cache formats
SCANF_CACHE_SIZE = 1000


def scanf(format_str, line, collapse_whitespace=True):
    # type: (str, str, bool) -> Tuple[Any]
    """
    scanf supports the following formats:
      %c        One character
      %5c       5 characters
      %d, %i    int value
      %7d, %7i  int value with length 7
      %f        float value
      %o        octal value
      %X, %x    hex value
      %s        string terminated by whitespace

    Any pattern with a * after the % (e.g., '%*f') will result in scanf matching the pattern but omitting the matched
    portion from the results. This is helpful when parts of the input string may change but should be ignored.

    Examples:

    >>> scanf("%s - %d errors, %d warnings", "/usr/sbin/sendmail - 0 errors, 4 warnings")
    ('/usr/sbin/sendmail', 0, 4)
    >>> scanf("%o %x %d", "0123 0x123 123")
    (83, 291, 123)
    >>> scanf("%o %*x %d", "0123 0x123 123")
    (83, 123)

    :param format_str: the scanf-compatible format string comprised of plain text and tokens from the table above.
    :param line: the text line to be parsed.
    :param collapse_whitespace: if True, performs a greedy match with whitespace in the input string,
    allowing for easy parsing of text that has been formatted to be read more easily. This enables better matching
    in log files where the data has been formatted for easier reading. These cases have variable amounts of whitespace
    between the columns, depending on the number of characters in the data itself.
    :return: a tuple of found values or None if the format does not match.
    """

    format_re, casts = _scanf_compile(format_str, collapse_whitespace)

    found = format_re.search(line)
    if found:
        groups = found.groups()
        return tuple([casts[i](groups[i]) for i in range(len(groups))])


def extract_data(pattern, text=None, filepath=None):
    # type: (str, str, str) -> Tuple[Any]
    """
    Read through an entire file or body of text one line at a time. Parse each line that matches the supplied
    pattern string and ignore the rest.

    Example:

    >>> extract_data("%o %x %d", "0123 0x123 123\n013 0x13 13")
    ([83, 11], [291, 19], [123, 13])

    :param pattern: the scanf-compatible format string comprised of plain text and tokens from the table above.
    :param text: the text with one or multiple lines to be parsed.
    :param filepath: the path to the file with text data to be parsed.
    :return: tuple with values as lists for each format symbol in the pattern per line.
    """
    y = []
    if text is None:
        text_source = open(filepath, 'r')
    else:
        text_source = text.splitlines()

    for line in text_source:
        match = scanf(pattern, line)
        if match is not None:
            if len(y) == 0:
                y = [[s] for s in match]
            else:
                for i, ydata in enumerate(y):
                    ydata.append(match[i])

    if text is None:
        text_source.close()

    return tuple(y)


@lru_cache(maxsize=SCANF_CACHE_SIZE)
def _scanf_compile(format_str, collapse_whitespace=True):
    """
    Compiles the format into a regular expression. Compiled formats are cached for faster reuse.

    For example:
    >>> format_re_compiled, casts = _scanf_compile('%s - %d errors, %d warnings')
    >>> print format_re_compiled.pattern
    (\S+) \- ([+-]?\d+) errors, ([+-]?\d+) warnings

    """

    format_pat = ""
    cast_list = []
    i = 0
    length = len(format_str)
    while i < length:
        found = None
        for token, pattern, cast in scanf_translate:
            found = token.match(format_str, i)
            if found:
                if cast is not None:
                    cast_list.append(cast)
                groups = found.groupdict() or found.groups()
                if groups:
                    pattern = pattern % groups
                format_pat += pattern
                i = found.end()
                break
        if not found:
            char = format_str[i]
            # escape special characters
            if char in "|^$()[]-.+*?{}<>\\":
                format_pat += "\\"
            format_pat += char
            i += 1
    if DEBUG:
        print("DEBUG: %r -> %s" % (format_str, format_pat))
    if collapse_whitespace:
        format_pat = re.sub(r'\s+', r'\\s+', format_pat)

    format_re = re.compile(format_pat)
    return format_re, cast_list
