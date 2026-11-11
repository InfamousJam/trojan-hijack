"""
Template for a defense. This file is ignored because its name starts with "_".

Copy it to a name without the underscore (e.g. defenses/keyword_detector.py),
fill in one or both functions, and delete the one you don't need.
"""

NAME = "my defense"  # label shown on the web page (optional)


def detect(content, source):
    """
    Slot 1. Runs on the untrusted CONTENT before the brain sees it.

    content: the exact text that was read (raw HTML for web pages)
    source:  where it came from, e.g. 'attacks/examples/deals_newsletter.eml'

    Return (flagged, reason). If flagged is True, the run stops here.
    """
    return False, "nothing checked yet"


def gate(action, context):
    """
    Slot 2. Runs on every email the brain wants to send, before it goes out.

    action:  {'tool': 'send_email', 'to': ..., 'subject': ..., 'body': ...}
    context: {'task':       the USER's request (trusted),
              'user_email': the user's own address,
              'source':     where the untrusted content came from,
              'channel':    'email' | 'web' | 'file',
              'content':    the untrusted text that was read}

    Return (allowed, reason). If allowed is False, that email is not sent.
    """
    return True, "nothing checked yet"
