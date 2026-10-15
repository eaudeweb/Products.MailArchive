import os, sys
if __name__ == '__main__':
    execfile(os.path.join(sys.path[0], 'framework.py'))
    
from Testing import ZopeTestCase
import email

from Products.MailArchive.modules.cleanhtml import HTMLCleaner
from Products.MailArchive.modules.imap_client import imap_client
from Products.MailArchive.modules.mbox_email import mbox_email, decode_string

MSG_PATH = os.path.join(INSTANCE_HOME, r'Products/MailArchive/tests/data')

HTML_MSG = """\
Message-ID: <html@example.com>
Subject: html
Content-Type: text/html; charset=utf-8

<html><body><p class='a"b' onclick="x()">&lt;script&gt; caf\xc3\xa9</p>
<script>alert(1)</script><a href="http://x/?a=1&amp;b=&quot;">l</a></body></html>
"""

MULTIPART_UTF8 = """\
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


class Test_MboxEmail(ZopeTestCase.ZopeTestCase):

    def open_msg(self, msg):
        path = os.path.join(MSG_PATH, msg)
        return open(path).read()
    
    def open_file(self, name):
        path = os.path.join(MSG_PATH, name)
        return open(path, 'rb').read()
        
    def test_get_to(self):
        msg = mbox_email(self.open_msg('msg1.txt'))
        self.assertEqual(msg.getTo(), [(u'John Doe', 'john.doe@fns.ro')])
        
    def test_get_to_with_encoding(self):
        msg = mbox_email(self.open_msg('msg2.txt'))
        self.assertEqual(msg.getTo(), [(u'Tim Terleg&#229;rd', 'timte878@student.se')])

    def test_get_multiple_to(self):
        msg = mbox_email(self.open_msg('msg3.txt'))
        self.assertEqual(msg.getTo(), [(u'te Kelrg', 'Je.Kelrg@ee.int'), (u'NFP', 'eiofp@roleeion.int'), (u'Ulri tark', 'stk@sa.sk'), (u'Schnder J&#252;rn', 'juen.schder@umweltamt.at')])

    def test_get_to_with_iso_2022_jp(self):
        # the ISO-2022-JP and gb2312 names decode
        msg = mbox_email(self.open_msg('msg4.txt'))
        self.assertEqual(msg.getTo(), [(u'J?rgen Larsen', 'jorg.lan@iod.dk')])

    def test_get_to_with_wrong_encoding(self):
        msg = mbox_email('To: =?x-no-such-charset?Q?abc?= <a@b.c>\n\n')
        self.assertEqual(msg.getTo(), [('', 'a@b.c')])

    def test_get_from(self):
        msg = mbox_email(self.open_msg('msg1.txt'))
        self.assertEqual(msg.getFrom(), (u'Smith', 'john@fns.ro'))

    def test_get_from_with_encoding(self):
        msg = mbox_email(self.open_msg('msg2.txt'))
        self.assertEqual(msg.getFrom(), (u'Geir B&#230;kholt', 'lists@elvww.com'))

    def test_get_from_gb2312(self):
        msg = mbox_email(self.open_msg('msg4.txt'))
        self.assertEqual(msg.getFrom(),
                         (u'&#23435;&#25991;&#25991;', 'linong@upu.cn'))

    def test_get_subject(self):
        msg = mbox_email(self.open_msg('msg1.txt'))
        self.assertEqual(msg.getSubject(), u'Re: test email')
    
    def test_get_subject_with_encoding(self):
        msg = mbox_email(self.open_msg('msg2.txt'))
        self.assertEqual(msg.getSubject(), u'[Zope] FYI: Portall&#246;sungen f&#252;r den Bildungsbereich /  Zope Tagung (German)')

    def test_get_subject_with_wrong_encoding(self):
        msg = mbox_email('Subject: =?x-no-such-charset?Q?abc?=\n\n')
        self.assertEqual(msg.getSubject(), '')

    def test_get_date(self):
        msg = mbox_email(self.open_msg('msg1.txt'))
        self.assertEqual(msg.getDateTime()[:6], (2005, 6, 21, 16, 11, 4))
    
    def test_get_cc(self):
        msg = mbox_email(self.open_msg('msg1.txt'))
        self.assertEqual(msg.getCC(), [('', 'nick.cave@fns.ro')])

    def test_get_multiple_cc(self):
        msg = mbox_email(self.open_msg('msg3.txt'))
        self.assertEqual(msg.getCC(), [(u'te Kelrg', 'Je.Kelrg@ee.int'), (u'NFP', 'eiofp@roleeion.int'), (u'Ulri tark', 'stk@sa.sk'), (u'Schnder J&#252;rn', 'juen.schder@umweltamt.at')])

    def test_get_cc_with_encoding(self):
        msg = mbox_email(self.open_msg('msg2.txt'))
        self.assertEqual(msg.getCC(), [(u'Aur&#233;lien Camp&#233;as', 'aure.aa@wanoo.fr')])

    def test_get_cc_gb2312(self):
        msg = mbox_email(self.open_msg('msg4.txt'))
        self.assertEqual(msg.getCC(),
                         [(u'&#23435;&#25991;&#25991;', 'linong@upu.cn')])

    def test_get_in_reply_to(self):
        msg = mbox_email(self.open_msg('msg1.txt'))
        self.assertEqual(msg.getInReplyTo(), '<42B812A3.8010205@fns.ro>')
    
    def test_get_message_id(self):
        msg = mbox_email(self.open_msg('msg1.txt'))
        self.assertEqual(msg.getMessageID(), '<42B811E8.7090602@fns.ro>')
    
    def test_get_content(self):
        msg = mbox_email(self.open_msg('msg1.txt'))
        self.assertEqual(msg.getContent(), '<div style="font-family: \'Courier New\', monospace; white-space: pre-wrap">test content<br /></div>')
    
    def test_get_content_with_encoding(self):
        # msg2.txt has a latin-1 body and no closing MIME boundary
        msg = mbox_email(self.open_msg('msg2.txt'))
        self.assertEqual(msg.getContent(), '<div style="font-family: \'Courier New\', monospace; white-space: pre-wrap">Urspr&#252;ngliche Nachricht</div>')

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

    def test_get_subject_8bit_latin1(self):
        msg = mbox_email('Subject: caf\xe9\n\n')
        self.assertEqual(msg.getSubject(), u'caf&#233;')

    def test_get_subject_windows_1252_alias(self):
        msg = mbox_email('Subject: =?window-1252?Q?caf=E9?=\n\n')
        self.assertEqual(msg.getSubject(), u'caf&#233;')

    def test_get_message_id_folded(self):
        msg = mbox_email('Message-ID:\n <a@b.c>\nIn-Reply-To: <a@b>\n  <c@d>\n\n')
        self.assertEqual(msg.getMessageID(), '<a@b.c>')
        self.assertEqual(msg.getInReplyTo(), '<a@b> <c@d>')

    def test_get_content_part_charset(self):
        msg = mbox_email(MULTIPART_UTF8)
        self.assertIn('caf&#233;', msg.getContent())

    def test_get_content_invalid_bytes(self):
        msg = mbox_email('Content-Type: text/plain; charset=utf-8\n\nab\xff\n')
        self.assertIn('ab&#65533;', msg.getContent())

    def test_get_content_unknown_charset(self):
        msg = mbox_email('Content-Type: text/plain; charset=x-nope\n\ncaf\xe9\n')
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
        self.assertIn(u'caf\xe9', content)

    def test_get_content_ex_escapes_text(self):
        msg = 'Content-Type: text/plain\n\n<script>a@b</script> caf\xc3\xa9\n'
        content = mbox_email(msg).getContentEx()
        self.assertIn(u'&lt;script&gt;a&#64;b&lt;/script&gt; caf\xe9<br />', content)

    def test_get_content_ex_html_without_charset(self):
        content = mbox_email(HTML_MSG.replace('; charset=utf-8', '')).getContentEx()
        self.assertIn('<div class="msgbody">', content)
        self.assertNotIn('alert', content)

    def test_decode_string_multiple_encoded_words(self):
        value = '=?utf-8?Q?raport_?= =?utf-8?Q?anual=C4=83.pdf?='
        self.assertEqual(decode_string(value), u'raport anual\u0103.pdf')

    def test_get_attachment_non_ascii_name(self):
        for name in ('raport_\xc4\x83.txt', '=?utf-8?Q?raport=5F=C4=83.txt?='):
            msg = mbox_email(
                'MIME-Version: 1.0\n'
                'Content-Type: multipart/mixed; boundary="XX"\n\n'
                '--XX\nContent-Type: text/plain\n\nbody\n'
                '--XX\nContent-Type: text/plain\n'
                'Content-Disposition: attachment; filename="%s"\n\n'
                'data\n--XX--\n' % name)
            self.assertEqual(msg.getAttachment('raport_\xc4\x83.txt'), 'data')
            self.assertEqual(msg.getAttachment(u'raport_\u0103.txt'), 'data')

    def test_8bit_addresses(self):
        msg = mbox_email('From: A <s\xc3\xa9b@x.be>\nTo: B <j\xe9@x.be>\n'
                         'Cc: C <c@x.be>\n\n')
        self.assertEqual(msg.getFrom()[1], u's\xe9b@x.be')
        self.assertEqual(msg.getTo(), [(u'B', u'j\xe9@x.be')])
        self.assertEqual(msg.getCC(), [(u'C', 'c@x.be')])
        # the obfuscated link can be mixed with unicode in the page
        for i in range(20):
            u'' + msg.antispam(msg.getTo()[0][1])

    def test_header_spaces_around_encoded_words(self):
        value = '=?iso-8859-1?q?R=E9union?= =?utf-8?b?w6k=?= suite'
        self.assertEqual(decode_string(value), u'R\xe9union\xe9 suite')
        self.assertEqual(decode_string('Re: =?utf-8?q?caf=C3=A9?= ok'),
                         u'Re: caf\xe9 ok')
        msg = mbox_email('Subject: Re: =?utf-8?q?caf=C3=A9?= ok\n'
                         'From: =?utf-8?q?Andr=C3=A9?= Dupont <a@b.c>\n\n')
        self.assertEqual(msg.getSubject(), u'Re: caf&#233; ok')
        self.assertEqual(msg.getFrom()[0], u'Andr&#233; Dupont')

    def test_decode_string_plain(self):
        self.assertEqual(decode_string('test.png'), u'test.png')
        self.assertEqual(decode_string(None), None)


class Test_HTMLCleaner(ZopeTestCase.ZopeTestCase):

    def test_quote_attributes(self):
        res = HTMLCleaner().clean('<html><body><a title="a&quot;&gt;&lt;b&gt;">x</a></body></html>')
        self.assertEqual(res, u'<div class="msgbody"><a title="a&quot;&gt;&lt;b&gt;">x</a></div>')


class Test_ImapClient(ZopeTestCase.ZopeTestCase):

    def test_no_servername(self):
        client = imap_client('', 'user', 'password')
        client.connOpen()
        self.assertFalse(client.connValid())

def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(Test_MboxEmail))
    suite.addTest(makeSuite(Test_HTMLCleaner))
    suite.addTest(makeSuite(Test_ImapClient))
    return suite

if __name__ == '__main__':
    framework()