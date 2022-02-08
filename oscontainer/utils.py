import logging
from typing import Any

from oscontainer.scanf import scanf

from oscontainer.constants import NO_LIMIT
from oscontainer.errors import OSContainerError

LOGGER = logging.getLogger(__name__)


def limit_from_str(limit_str):
    # type: (str) -> int
    if limit_str is None:
        raise OSContainerError("limit is None")

    if limit_str == "max":
        return NO_LIMIT

    return int(limit_str)


def load_multiline_scan(path, scan_format, match_line):
    # type: (str, str, str) -> Any
    """Loads content from multiline file using specified match criteria.
    :param path: the path to the file.
    :param scan_format: the format to use with scanf to extract value.
    :param match_line: the line to be matched for value to extract.
    :return: extracted value or None if not found.
    """
    with open(path, 'r') as f:
        for line in f:
            if line.__contains__(match_line):
                res = scanf(scan_format, line)
                if len(res) == 2:
                    return res[1]
    return None


def load_scan(path, scan_format):
    # type: (str,str) -> Any
    """Loads content of the file using provided scan format
    """
    val = load(path)
    return scanf(scan_format, val)


def load(path, binary=False, encoding="auto"):
    """ Loads a file content """
    with open(path, 'rb') as handle:
        tmp = handle.read()
        return tmp if binary else decode_text(tmp, encoding).strip()


def _detect_encoding(text):
    import codecs
    encodings = {codecs.BOM_UTF8: "utf_8_sig",
                 codecs.BOM_UTF16_BE: "utf_16_be",
                 codecs.BOM_UTF16_LE: "utf_16_le",
                 codecs.BOM_UTF32_BE: "utf_32_be",
                 codecs.BOM_UTF32_LE: "utf_32_le",
                 b'\x2b\x2f\x76\x38': "utf_7",
                 b'\x2b\x2f\x76\x39': "utf_7",
                 b'\x2b\x2f\x76\x2b': "utf_7",
                 b'\x2b\x2f\x76\x2f': "utf_7",
                 b'\x2b\x2f\x76\x38\x2d': "utf_7"}
    for bom in sorted(encodings, key=len, reverse=True):
        if text.startswith(bom):
            try:
                return encodings[bom], len(bom)
            except UnicodeDecodeError:
                continue
    decoders = ["utf-8", "Windows-1252"]
    for decoder in decoders:
        try:
            text.decode(decoder)
            return decoder, 0
        except UnicodeDecodeError:
            continue
    return None, 0


def decode_text(text, encoding="auto"):
    bom_length = 0
    if encoding == "auto":
        encoding, bom_length = _detect_encoding(text)
        if encoding is None:
            LOGGER.warning("can't decode %s" % str(text))
            return text.decode("utf-8", "ignore")  # Ignore not compatible characters
    return text[bom_length:].decode(encoding)
