import os
import unittest

from Products.MailArchive.modules.cleanhtml import HTMLCleaner
from Products.MailArchive.modules.mbox_email import mbox_email, decode_string

MSG_PATH = os.path.join(os.path.dirname(__file__), 'data')

HTML_MSG = b"""\
Message-ID: <html@example.com>
Subject: html
Content-Type: text/html; charset=utf-8

<html><body><p class='a"b' onclick="x()">&lt;script&gt; caf\xc3\xa9</p>
<script>alert(1)</script><a href="http://x/?a=1&amp;b=&quot;">l</a></body></html>
"""

MULTIPART_UTF8 = b"""\
Message-ID: <multi@example.com>
Subject: multipart
MIME-Version: 1.0
Content-Type: multipart/mixed; boundary="XX"

--XX
Content-Type: text/plain; charset=utf-8
Content-Transfer-Encoding: 8bit

caf\xc3\xa9
--XX--
"""


class Test_MboxEmail(unittest.TestCase):

    def open_msg(self, msg):
        with open(os.path.join(MSG_PATH, msg), 'rb') as f:
            return f.read()

    def open_file(self, name):
        with open(os.path.join(MSG_PATH, name), 'rb') as f:
            return f.read()

    def test_get_to(self):
        msg = mbox_email(self.open_msg('msg1.txt'))
        self.assertEqual(msg.getTo(), [('John Doe', 'john.doe@fns.ro')])

    def test_get_to_with_encoding(self):
        msg = mbox_email(self.open_msg('msg2.txt'))
        self.assertEqual(msg.getTo(), [('Tim Terleg&#229;rd', 'timte878@student.se')])

    def test_get_multiple_to(self):
        msg = mbox_email(self.open_msg('msg3.txt'))
        self.assertEqual(msg.getTo(), [('te Kelrg', 'Je.Kelrg@ee.int'), ('NFP', 'eiofp@roleeion.int'), ('Ulri tark', 'stk@sa.sk'), ('Schnder J&#252;rn', 'juen.schder@umweltamt.at')])

    def test_get_to_with_iso_2022_jp(self):
        # the ISO-2022-JP and gb2312 names decode on Python 3
        msg = mbox_email(self.open_msg('msg4.txt'))
        self.assertEqual(msg.getTo(), [('J?rgen Larsen', 'jorg.lan@iod.dk')])

    def test_get_to_with_wrong_encoding(self):
        msg = mbox_email(b'To: =?x-no-such-charset?Q?abc?= <a@b.c>\n\n')
        self.assertEqual(msg.getTo(), [('', 'a@b.c')])

    def test_get_from(self):
        msg = mbox_email(self.open_msg('msg1.txt'))
        self.assertEqual(msg.getFrom(), ('Smith', 'john@fns.ro'))

    def test_get_from_str_message(self):
        msg = mbox_email(self.open_msg('msg1.txt').decode('ascii'))
        self.assertEqual(msg.getFrom(), ('Smith', 'john@fns.ro'))

    def test_get_from_with_encoding(self):
        msg = mbox_email(self.open_msg('msg2.txt'))
        self.assertEqual(msg.getFrom(), ('Geir B&#230;kholt', 'lists@elvww.com'))

    def test_get_from_gb2312(self):
        msg = mbox_email(self.open_msg('msg4.txt'))
        self.assertEqual(msg.getFrom(), ('&#23435;&#25991;&#25991;', 'linong@upu.cn'))

    def test_get_from_8bit_header(self):
        msg = mbox_email(b'From: J\xfcrgen <j@x.dk>\n\n')
        self.assertEqual(msg.getFrom(), ('J&#252;rgen', 'j@x.dk'))

    def test_get_subject(self):
        msg = mbox_email(self.open_msg('msg1.txt'))
        self.assertEqual(msg.getSubject(), 'Re: test email')

    def test_get_subject_with_encoding(self):
        # the space before the encoded word is kept (RFC 2047)
        msg = mbox_email(self.open_msg('msg2.txt'))
        self.assertEqual(msg.getSubject(), '[Zope] FYI: Portall&#246;sungen f&#252;r den Bildungsbereich /  Zope Tagung (German)')

    def test_get_subject_with_wrong_encoding(self):
        msg = mbox_email(b'Subject: =?x-no-such-charset?Q?abc?=\n\n')
        self.assertEqual(msg.getSubject(), '')

    def test_get_subject_8bit_utf8(self):
        msg = mbox_email(b'Subject: caf\xc3\xa9 <b>\n\n')
        self.assertEqual(msg.getSubject(), 'caf&#233; &lt;b&gt;')

    def test_get_subject_8bit_latin1(self):
        msg = mbox_email(b'Subject: caf\xe9\n\n')
        self.assertEqual(msg.getSubject(), 'caf&#233;')

    def test_get_subject_windows_1252_alias(self):
        msg = mbox_email(b'Subject: =?window-1252?Q?caf=E9?=\n\n')
        self.assertEqual(msg.getSubject(), 'caf&#233;')

    def test_get_subject_ex(self):
        msg = mbox_email(self.open_msg('msg2.txt'))
        self.assertEqual(msg.getSubjectEx(), '[Zope] FYI: Portall\xf6sungen f\xfcr den Bildungsbereich /  Zope Tagung (German)')

    def test_get_date(self):
        msg = mbox_email(self.open_msg('msg1.txt'))
        self.assertEqual(msg.getDateTime()[:6], (2005, 6, 21, 16, 11, 4))

    def test_get_date_missing(self):
        msg = mbox_email(b'Subject: x\n\n')
        self.assertEqual(msg.getDateTime(), None)

    def test_get_cc(self):
        msg = mbox_email(self.open_msg('msg1.txt'))
        self.assertEqual(msg.getCC(), [('', 'nick.cave@fns.ro')])

    def test_get_multiple_cc(self):
        msg = mbox_email(self.open_msg('msg3.txt'))
        self.assertEqual(msg.getCC(), [('te Kelrg', 'Je.Kelrg@ee.int'), ('NFP', 'eiofp@roleeion.int'), ('Ulri tark', 'stk@sa.sk'), ('Schnder J&#252;rn', 'juen.schder@umweltamt.at')])

    def test_get_cc_with_encoding(self):
        msg = mbox_email(self.open_msg('msg2.txt'))
        self.assertEqual(msg.getCC(), [('Aur&#233;lien Camp&#233;as', 'aure.aa@wanoo.fr')])

    def test_get_cc_gb2312(self):
        msg = mbox_email(self.open_msg('msg4.txt'))
        self.assertEqual(msg.getCC(), [('&#23435;&#25991;&#25991;', 'linong@upu.cn')])

    def test_get_in_reply_to(self):
        msg = mbox_email(self.open_msg('msg1.txt'))
        self.assertEqual(msg.getInReplyTo(), '<42B812A3.8010205@fns.ro>')

    def test_get_message_id(self):
        msg = mbox_email(self.open_msg('msg1.txt'))
        self.assertEqual(msg.getMessageID(), '<42B811E8.7090602@fns.ro>')

    def test_get_message_id_folded(self):
        msg = mbox_email(b'Message-ID:\n <a@b.c>\n\n')
        self.assertEqual(msg.getMessageID(), '<a@b.c>')

    def test_get_content(self):
        msg = mbox_email(self.open_msg('msg1.txt'))
        self.assertEqual(msg.getContent(), '<div style="font-family: \'Courier New\', monospace; white-space: pre-wrap">test content<br /></div>')

    def test_get_content_with_encoding(self):
        # msg2.txt has a latin-1 body and no closing MIME boundary
        msg = mbox_email(self.open_msg('msg2.txt'))
        self.assertEqual(msg.getContent(), '<div style="font-family: \'Courier New\', monospace; white-space: pre-wrap">Urspr&#252;ngliche Nachricht</div>')

    def test_get_content_part_charset(self):
        msg = mbox_email(MULTIPART_UTF8)
        self.assertIn('caf&#233;', msg.getContent())

    def test_get_content_invalid_bytes(self):
        msg = mbox_email(b'Content-Type: text/plain; charset=utf-8\n\nab\xff\n')
        self.assertIn('ab&#65533;', msg.getContent())

    def test_get_content_unknown_charset(self):
        msg = mbox_email(b'Content-Type: text/plain; charset=x-nope\n\ncaf\xe9\n')
        self.assertIn('caf&#233;', msg.getContent())

    def test_get_content_html(self):
        content = mbox_email(HTML_MSG).getContent()
        self.assertIn('<div class="msgbody">', content)
        self.assertIn('&lt;script&gt; caf&#233;', content)
        self.assertIn('class="a&quot;b"', content)
        self.assertIn('href="http://x/?a=1&amp;b=&quot;" rel="nofollow"', content)
        self.assertNotIn('onclick', content)
        self.assertNotIn('alert', content)

    def test_get_content_ex(self):
        content = mbox_email(MULTIPART_UTF8).getContentEx()
        self.assertIn('caf\xe9', content)

    def test_get_content_ex_escapes_text(self):
        msg = b'Content-Type: text/plain\n\n<script>a@b</script> caf\xc3\xa9\n'
        content = mbox_email(msg).getContentEx()
        self.assertIn('&lt;script&gt;a&#64;b&lt;/script&gt; caf\xe9<br />', content)

    def test_get_content_ex_html_without_charset(self):
        content = mbox_email(HTML_MSG.replace(b'; charset=utf-8', b'')).getContentEx()
        self.assertIn('<div class="msgbody">', content)
        self.assertNotIn('alert', content)

    def test_list_attachments(self):
        msg = mbox_email(self.open_msg('msg1.txt'))
        self.assertEqual(msg.getAttachments(), [('test.png', 'test.png')])

    def test_list_multiple_attachments(self):
        msg = mbox_email(self.open_msg('msg3.txt'))
        self.assertEqual(msg.getAttachments(), [('test.png', 'test.png'),
                                                ('test.zip', 'test.zip')])

    def test_not_attachments(self):
        msg = mbox_email(self.open_msg('msg2.txt'))
        self.assertEqual(msg.getAttachments(), [])

    def test_get_attachment(self):
        msg = mbox_email(self.open_msg('msg1.txt'))
        target = self.open_file('test.png')
        self.assertEqual(msg.getAttachment('test.png'), target)

    def test_get_attachment_missing(self):
        msg = mbox_email(self.open_msg('msg1.txt'))
        self.assertEqual(msg.getAttachment('nothere.png'), None)

    def test_decode_string_multiple_encoded_words(self):
        value = '=?utf-8?Q?raport_?= =?utf-8?Q?anual=C4=83.pdf?='
        self.assertEqual(decode_string(value), 'raport anuală.pdf')

    def test_decode_string_plain(self):
        self.assertEqual(decode_string('test.png'), 'test.png')
        self.assertEqual(decode_string(None), None)


class Test_HTMLCleaner(unittest.TestCase):

    def test_clean(self):
        res = HTMLCleaner().clean('<html><body><b>x</b> &amp; &#169;</body></html>')
        self.assertEqual(res, '<div class="msgbody"><b>x</b> &amp; &#169;</div>')
