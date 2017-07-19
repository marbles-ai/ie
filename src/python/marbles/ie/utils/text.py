from __future__ import unicode_literals, print_function
import regex as re  # Has better support for unicode


# r'\p{P}' is too broad
_UPUNCT = re.compile(r'([(),:;\u00a1\u00a7\u00b6\u00b7\u00bf])', re.UNICODE)
_UDQUOTE = re.compile(r'["\u2033\u2034\u2036\u2037\u201c\u201d]', re.UNICODE)
_USQUOTE = re.compile(r"\u2032([^\u2032\u2035]+)\u2035", re.UNICODE)
_USQL = re.compile(r"(?<=[a-z])(['](?:ll|s|ve|nt|m|re|d))(?=\s|$)", re.UNICODE | re.IGNORECASE)
_USQR = re.compile(r"(['])(?!(?:ll|s|ve|nt|m|re|d)(?:\s|$))", re.UNICODE | re.IGNORECASE)


def preprocess_sentence(text):
    """Pre-process a sentence.

    Args:
        text: The sentence.

    Returns:
        A sentence.
    """
    # Perform Unicode-Ascii substitutions and add spaces around punctuation
    text = _USQUOTE.sub(r"'\1'", text).replace('\u2019', "'")
    text = _UDQUOTE.sub(r' " ', text)
    text = _UPUNCT.sub(r' \1 ', text)
    text = _USQL.sub(r' \1', text)
    text = _USQR.sub(r'\1 ', text)
    # wa, ca, sha are not part of the vocab
    text = text.replace("wo n't", "won't")
    text = text.replace("ca n't", "can't")
    text = text.replace("sha n't", "shan't")

    # TODO: Fixup spelling errors
    return text
