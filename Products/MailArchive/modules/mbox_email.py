#The contents of this file are subject to the Mozilla Public
#License Version 1.1 (the "License"); you may not use this file
#except in compliance with the License. You may obtain a copy of
#the License at http://www.mozilla.org/MPL/
#
#Software distributed under the License is distributed on an "AS
#IS" basis, WITHOUT WARRANTY OF ANY KIND, either express or
#implied. See the License for the specific language governing
#rights and limitations under the License.
#
#The Original Code is MailArchive 0.5
#
#The Initial Owner of the Original Code is European Environment
#Agency (EEA).  Portions created by Finsiel Romania are
#Copyright (C) 2000 by European Environment Agency.  All
#Rights Reserved.
#
#Contributor(s):
#  Original Code: 
#    Cornel Nitu (Finsiel Romania)
#    Dragos Chirila (Finsiel Romania)
#  Soren Roug, EEA


import email
import re
import codecs
from cgi import escape
from os.path import join
from email.Utils import parseaddr, parsedate, getaddresses
from email.Header import decode_header

from cleanhtml import HTMLCleaner
from Products.MailArchive.Utils import Utils

charset_table = {
     "window-1252": "cp1252",
     "windows-1252": "cp1252",
     "nil": "Latin-1",
     "default_charset": "Latin-1",
     "x-unknown": "Latin-1",
}

def to_unicode(s, encoding):
    if encoding:
        encoding = encoding.lower()
        charset  = charset_table.get(encoding, encoding)
        return unicode(s, charset, 'replace')
    else:
        return bytes_to_unicode(s)

def bytes_to_unicode(s):
    """ Decode 8-bit header or body bytes of unknown charset """
    if isinstance(s, unicode):
        return s
    try:
        return s.decode('utf-8')
    except UnicodeDecodeError:
        return s.decode('latin-1')

def address_to_unicode(addr):
    """ Decode an address with 8-bit bytes (raw in the header) """
    if isinstance(addr, str) and re.search(r'[\x80-\xff]', addr):
        return bytes_to_unicode(addr)
    return addr

def get_charset(charset, default='latin-1'):
    """ Return a codec name for the charset, or default if it is unknown """
    if charset:
        charset = charset_table.get(charset.lower(), charset.lower())
        try:
            codecs.lookup(charset)
            return charset
        except LookupError:
            pass
    return default


def extractUrl(msg):
    """ Functions to identify and extract URLs"""
    strg = re.sub(r'(?P<url>http[s]?://[-_&;,?:~=%#+/.0-9a-zA-Z]+)',
                  r'<a rel="nofollow" href="\g<url>">\g<url></a>', msg)
    return strg.strip()

def to_entities(str):
    res = []
    for ch in str:
        och = ord(ch)
        if och > 127:
            res.append('&#%d;' % och)
        else:
            res.append(ch)
    return ''.join(res)

def to_entities_quote(str):
    res = []
    for ch in str:
        och = ord(ch)
        if och > 127:
            res.append('&#%d;' % och)
        elif och == 38:
            res.append('&amp;')
        elif och == 60:
            res.append("&lt;")
        elif och == 62:
            res.append("&gt;")
        else:
            res.append(ch)
    return ''.join(res)

def join_header(parts):
    """ Join decoded (text, charset) header parts. On Python 2
    decode_header strips the whitespace around the unencoded parts, so put
    a space back between an encoded and an unencoded part; adjacent encoded
    words are joined without space (RFC 2047). """
    res = []
    prev = None
    for i, (text, enc) in enumerate(parts):
        if i and (enc is None) != (prev is None):
            res.append(u' ')
        res.append(text)
        prev = enc
    return u''.join(res)

def decode_string(value):
    if value is None:
        return None
    return join_header([(to_unicode(s, enc and get_charset(enc)), enc)
                        for s, enc in decode_header(value)])

class mbox_email(Utils):
    """ wrapper for email """

    def __init__(self, msg):
        self._msg = email.message_from_string(msg)

    def codecs_lookup(self, encoding):
        if encoding is not None:
            encoding = charset_table.get(encoding.lower(), encoding)
            try:
                codecs.lookup(encoding)
                return 1
            except LookupError:
                return 0
        else:
            return 1

    def getTo(self):
        res = []
        buf = getaddresses(self._msg.get_all('to', ''))
        for i in buf:
            header = decode_header(i[0])
            data = join_header([(to_unicode(s, enc), enc) for s, enc in header
                                if self.codecs_lookup(enc)])
            res.append((to_entities_quote(data), address_to_unicode(i[1])))
        return res
            
    def getFrom(self):
        buf = parseaddr(self._msg.get('from', ''))
        header = decode_header(buf[0])
        data = join_header([(to_unicode(s, enc), enc) for s, enc in header
                            if self.codecs_lookup(enc)])
        return (to_entities_quote(data), address_to_unicode(buf[1]))

    def getCC(self):
        res = []
        buf = getaddresses(self._msg.get_all('cc', ''))
        for i in buf:
            header = decode_header(i[0])
            data = join_header([(to_unicode(s, enc), enc) for s, enc in header
                                if self.codecs_lookup(enc)])
            res.append((to_entities_quote(data), address_to_unicode(i[1])))
        return res

    def getSubject(self):
        buf = self._msg.get('subject', '')
        header = decode_header(buf)
        data = join_header([(to_unicode(s, enc), enc) for s, enc in header
                            if self.codecs_lookup(enc)])
        return to_entities_quote(data)

    def getSubjectEx(self):
        return decode_string(self._msg.get('subject', u''))

    def getDateTime(self):
        return parsedate(self._msg.get('date', None))

    def getDateTimeEx(self):
        return email.utils.parsedate(self._msg['Date'])

    def getInReplyTo(self):
        return ' '.join(self._msg.get('In-Reply-To', '').split())

    def getMessageID(self):
        return ' '.join(self._msg.get('Message-ID', '').split())

    def getContent(self):
        """ Walks through the message until it finds one that
            is either text/plain or text/html
        """
        payloads = []
        for part in self._msg.walk():
            ct_type = part.get_content_type()
            if ct_type in ['text/plain', 'text/html']:
                p = part.get_payload(decode=True) or ''
                charset = get_charset(part.get_content_charset() or
                                      self._msg.get_content_charset())
                p = unicode(p, charset, 'replace')
                if ct_type == 'text/html':
                    mycleaner = HTMLCleaner()
                    try:
                        p = mycleaner.clean(p)
                        p = to_entities(p)
                    except:
                        p = to_entities_quote(p)
                    p = p.replace('@', '&#64;')
                else:
                    p = to_entities_quote(p)
                    p = p.replace('@', '&#64;')
                    p = p.replace('\n', '<br />')
                    p = p.replace('\r', '')
                    p =  extractUrl(p)
                    p = '''<div style="font-family: 'Courier New', monospace; white-space: pre-wrap">%s</div>''' % p
                payloads.append(p.encode('ascii'))
                return "".join(payloads)

    def getContentEx(self):
        """ Walks through the message until it finds one that
            is either text/plain or text/html
        """
        payloads = []
        for part in self._msg.walk():
            ct_type = part.get_content_type()
            if ct_type in ['text/plain', 'text/html']:
                p = part.get_payload(decode=True) or ''
                charset = part.get_content_charset()
                if charset is None:
                    # We cannot know the character set, so return decoded "something"
                    p = bytes_to_unicode(p)
                else:
                    p = unicode(p, get_charset(charset), 'ignore')
                if ct_type == 'text/html':
                    mycleaner = HTMLCleaner()
                    try:
                        p = mycleaner.clean(p)
                    except Exception:
                        p = escape(p)
                    p = p.replace('@', '&#64;')
                else:
                    p = escape(p)
                    p = p.replace('@', '&#64;')
                    p = p.replace('\n', '<br />')
                    p = p.replace('\r', '')
                    p =  extractUrl(p)
                    p = u'''<div style="font-family: 'Courier New', monospace; white-space: pre-wrap">%s</div>''' % p
                payloads.append(p)
                return u''.join(payloads)

    def getAttachments(self):
        atts = []
        for part in self._msg.walk():
            if part.get_content_maintype() == 'multipart':
                continue
            filename = part.get_filename()
            if filename:
                filename = decode_string(filename)
                atts.append((filename, self.urlQuote(self.toUtf8(filename))))
            #if not filename:
            #    ext = mimetypes.guess_extension(part.get_type())
            #    if not ext:
            #        # Use a generic bag-of-bits extension
            #        ext = '.bin'
            #        filename = 'unknown%03d%s' % (counter, ext)
            #counter += 1
        return atts

    def getAttachment(self, filename):
        clean = lambda x: re.sub(r'[\r\n\t]', '', x)
        filename = self.toUtf8(filename)
        for part in self._msg.walk():
            if part.get_content_maintype() == 'multipart':
                continue
            in_email = self.toUtf8(decode_string(part.get_filename()) or '')
            if filename == in_email or clean(filename) == clean(in_email):
                return part.get_payload(decode=True)
        return None
