import os
import shutil
import tempfile
import unittest

from Products.MailArchive.Utils import Utils
from Products.MailArchive.modules.imap_client import imap_client
from Products.MailArchive.modules.mbox import mbox_imap
from Products.MailArchive.modules.mbox_filters import mbox_filters, SPAM


class Test_Utils(unittest.TestCase):

    def setUp(self):
        self.utils = Utils()

    def test_lines_to_list(self):
        self.assertEqual(self.utils.lines_to_list('a\r\n\r\nb'), ['a', 'b'])
        self.assertEqual(self.utils.lines_to_list(''), [])

    def test_remove_duplicates(self):
        self.assertEqual(self.utils.remove_duplicates(['a', 'b', 'a']), ['a', 'b'])

    def test_url_quote(self):
        self.assertEqual(self.utils.urlQuote('a bă'), 'a%20b%C4%83')
        self.assertEqual(self.utils.urlUnquote('a%20b%C4%83'), 'a bă')

    def test_to_unicode(self):
        self.assertEqual(self.utils.toUnicode(b'\xc4\x83'), 'ă')
        self.assertEqual(self.utils.toUnicodeEx(b'\xe9'), '\xe9')
        self.assertEqual(self.utils.toUtf8('ă'), b'\xc4\x83')

    def test_cleanup_mbox_id(self):
        self.assertEqual(self.utils.cleanupMboxId('INBOX.Sent Items'), 'INBOX-Sent Items')

    def test_content_disposition(self):
        self.assertEqual(self.utils.content_disposition('my file.pdf'),
                         'attachment;filename=my_file.pdf')
        self.assertEqual(self.utils.content_disposition('raportă.pdf'),
                         "attachment;filename*=UTF-8''raport%C4%83.pdf")

    def test_get_mboxes(self):
        tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmpdir)
        files = {
            'environment_2021.mbx': b'From a@b\n\xff\xfe' + b'\xe9' * 9000,
            'environment_2022.mbx': b'\xff\xfe not an mbox',
            'environment_2023': b'From a@b\n',
            'other.mbx': b'From a@b\n',
        }
        for name, content in files.items():
            with open(os.path.join(tmpdir, name), 'wb') as f:
                f.write(content)
        mboxes, others = self.utils.get_mboxes(tmpdir, ['environment_2023'])
        self.assertEqual([x[1] for x in mboxes], ['environment_2021.mbx'])
        self.assertEqual([x[1] for x in others], ['environment_2022.mbx'])


class Test_Filters(unittest.TestCase):

    def test_blackwords(self):
        filters = mbox_filters()
        result, reason = filters.run_rules(
            "DON'T DELETE THIS MESSAGE -- FOLDER INTERNAL DATA")
        self.assertEqual(result, SPAM)
        self.assertTrue(filters.run_rules('hello')[0])


class FakeIMAP(object):

    def __init__(self, messages):
        self.messages = messages

    def login(self, user, password):
        return 'OK', [b'Logged in']

    def list(self):
        return 'OK', [b'(\\HasNoChildren) "." "INBOX"',
                      b'(\\HasNoChildren) "." "Trash"']

    def select(self, name, readonly=False):
        return 'OK', [str(len(self.messages)).encode('ascii')]

    def search(self, charset, criteria):
        return 'OK', [b' '.join(str(i + 1).encode('ascii')
                                for i in range(len(self.messages)))]

    def fetch(self, num, parts):
        return 'OK', [(b'1 (RFC822 {10}', self.messages[int(num) - 1]), b')']

    def logout(self):
        pass


class Test_IMAP(unittest.TestCase):

    def make_client(self, messages):
        client = imap_client('imap.example.com', 'user', 'pass')
        client._imap_client__imap_connection = FakeIMAP(messages)
        client._imap_client__imap_flg = True
        return client

    def test_conn_open_without_server(self):
        client = imap_client('', '', '')
        client.connOpen()
        self.assertFalse(client.connValid())

    def test_list_mailboxes(self):
        client = self.make_client([])
        self.assertEqual(client.listMailboxes(['Trash']), ['INBOX'])
        self.assertEqual(client.listMailboxesEx([]),
                         [{'name': 'INBOX', 'counter': 0},
                          {'name': 'Trash', 'counter': 0}])

    def test_mbox_imap(self):
        msg = (b'Message-ID: <1@x>\nDate: Wed, 22 Jun 2005 10:00:00 +0200\n'
               b'From: J\xc3\xbcrgen <j@x>\nSubject: caf\xc3\xa9\n\nbody\n')
        client = self.make_client([msg])
        box = mbox_imap(client, 'INBOX')
        self.assertEqual(list(box.cache), ['<1@x>'])
        item = box.cache['<1@x>']
        self.assertEqual(box.get_msg_subject(item), 'caf\xe9')
        self.assertEqual(box.get_msg_from(item), 'J&#252;rgen')
        self.assertEqual(box.starting[:3], (2005, 6, 22))
        self.assertEqual(box.get_mbox_msg('<1@x>', client), msg)
