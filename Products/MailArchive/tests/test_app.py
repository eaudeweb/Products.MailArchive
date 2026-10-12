#acceptance tests
import os
import shutil
import tempfile
import time
import unittest

from AccessControl.SecurityManagement import newSecurityManager
from AccessControl.SecurityManagement import noSecurityManager
from AccessControl.SpecialUsers import system
from OFS.Application import Application
from Products.PageTemplates.ZopePageTemplate import ZopePageTemplate
from Testing.makerequest import makerequest
from zExceptions import NotFound

from Products.MailArchive.MailArchiveFolder import manage_addMailArchiveFolder

#constants
MBOX = 'mail_archive'
DATA_PATH = os.path.join(os.path.dirname(__file__), 'data')
MBOX_PATH = os.path.join(DATA_PATH, 'mbox_directory')

# get_mboxes() only loads the 'environment*' mailboxes
MBOX1 = 'environment_2021.mbx'
MBOX2 = 'environment_2022.mbx'
MBOX3 = 'environment_2023.mbx'
MBOX4 = 'environment_2024.mbx'
MBOX_FILES = {MBOX1: 'mbox1.mbx', MBOX2: 'mbox2.mbx', MBOX3: 'mbox3.mbx'}

STANDARD_TEMPLATE = """\
<metal:block define-macro="page"><html><body>
<metal:block define-slot="body" />
</body></html></metal:block>
"""

LATIN1_MSG = b"""\
From someone@example.com Wed Jun 22 10:00:00 2005
Message-ID: <latin1.1@example.com>
Date: Wed, 22 Jun 2005 10:00:00 +0200
From: J\xfcrgen <jurgen@example.com>
To: Ana <ana@example.com>
Subject: Gr\xfc\xdfe <b>
Content-Type: text/plain; charset=iso-8859-1
Content-Transfer-Encoding: 8bit

Sch\xf6ne Gr\xfc\xdfe & <tschau>

"""

NODATE_MSG = b"""\
From someone@example.com Wed Jun 22 11:00:00 2005
Message-ID: <nodate.2@example.com>
From: nodate@example.com
Subject: no date
In-Reply-To: <latin1.1@example.com>

reply without a date

"""


def mbox_with_attachment():
    with open(os.path.join(DATA_PATH, 'msg1.txt'), 'rb') as f:
        msg1 = f.read()
    return (b'From john@fns.ro Tue Jun 21 16:11:04 2005\n' + msg1 + b'\n' +
            LATIN1_MSG + NODATE_MSG)


class MailArchiveTestCase(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        for name, source in MBOX_FILES.items():
            shutil.copy(os.path.join(MBOX_PATH, source),
                        os.path.join(self.tmpdir, name))
        self.app = makerequest(Application())
        self.app._setObject('standard_template.pt',
                            ZopePageTemplate('standard_template.pt',
                                             STANDARD_TEMPLATE))
        newSecurityManager(None, system)
        self.setUpArchives()
        manage_addMailArchiveFolder(self.app, MBOX, '', self.tmpdir)
        self.mbox = self.app[MBOX]

    def setUpArchives(self):
        pass

    def tearDown(self):
        noSecurityManager()
        shutil.rmtree(self.tmpdir)

    def mbox_path(self, name):
        return os.path.join(self.tmpdir, name)

    def archive_ids(self):
        return [x.id for x in self.mbox.getArchives()]


class Test01_MboxPreviousNext(MailArchiveTestCase):

    def test_prev_next_first(self):
        obj = self.mbox.getArchives()[0]    #only mbox1.mbx
        prev, next = obj.getPrevNext('815f70cf050329015744ac9a43', 'subject', 0)
        id = obj.get_msg_id(prev)
        self.assertEqual(id, '<815f70cf05033023503b4a9704@mail.gmail.com>')
        self.assertEqual(next, -1)
        prev, next = obj.getPrevNext('815f70cf050329015744ac9a43', 'subject', 1)
        id = obj.get_msg_id(next)
        self.assertEqual(prev, -1)
        self.assertEqual(id, '<815f70cf05033023503b4a9704@mail.gmail.com>')

    def test_prev_next_middle(self):
        obj = self.mbox.getArchives()[0]    #only mbox1.mbx
        prev, next = obj.getPrevNext('16970.59764.819866.775606', 'date', 0)
        prev = obj.get_msg_id(prev)
        next = obj.get_msg_id(next)
        self.assertEqual(prev, '<424A5688.6050106@microsfot.co.uk>')
        self.assertEqual(next, '<815f70cf05033023503b4a9704@mail.gmail.com>')
        prev, next = obj.getPrevNext('16970.59764.819866.775606', 'date', 1)
        prev = obj.get_msg_id(prev)
        next = obj.get_msg_id(next)
        self.assertEqual(prev, '<815f70cf05033023503b4a9704@mail.gmail.com>')
        self.assertEqual(next, '<424A5688.6050106@microsfot.co.uk>')

    def test_prev_next_last(self):
        obj = self.mbox.getArchives()[0]    #only mbox1.mbx
        # equal subjects are ordered by the message index
        prev, next = obj.getPrevNext('16970.59764.819866.775606', 'subject', 0)
        next = obj.get_msg_id(next)
        self.assertEqual(prev, -1)
        self.assertEqual(next, '<424A5688.6050106@microsfot.co.uk>')
        prev, next = obj.getPrevNext('16970.59764.819866.775606', 'subject', 1)
        prev = obj.get_msg_id(prev)
        self.assertEqual(prev, '<424A5688.6050106@microsfot.co.uk>')
        self.assertEqual(next, -1)


class Test02_MboxAddRemoveModify(MailArchiveTestCase):

    def read_mbox3(self):
        with open(self.mbox_path(MBOX3), 'rb') as f:
            return f.read()

    def write_mbox3(self, content):
        with open(self.mbox_path(MBOX3), 'wb') as f:
            f.write(content)

    def add_mbox(self):
        # drop the '<marker>' first line, so the file becomes an mbox
        self.write_mbox3(self.read_mbox3().split(b'\n', 1)[1])

    def del_mbox(self):
        os.unlink(self.mbox_path(MBOX3))

    def test_detect_add(self):
        """ new mailboxes in the directory are detected """
        self.assertEqual(self.archive_ids(), [MBOX1, MBOX2])
        self.add_mbox()
        self.mbox.updateArchives(0)
        self.assertEqual(self.archive_ids(), [MBOX3, MBOX1, MBOX2])

    def test_detect_delete(self):
        """ mailboxes deleted from the directory are detected """
        self.add_mbox()
        self.mbox.updateArchives(0)
        self.assertEqual(self.archive_ids(), [MBOX3, MBOX1, MBOX2])
        self.del_mbox()
        self.mbox.updateArchives(0)
        self.assertEqual(self.archive_ids(), [MBOX1, MBOX2])

    def test_update_without_changes(self):
        self.mbox.updateArchives(0)
        self.assertEqual(self.archive_ids(), [MBOX1, MBOX2])

    def test_detect_modification(self):
        """ a mailbox that changes in size is reloaded """
        self.add_mbox()
        self.mbox.updateArchives(0)
        self.assertEqual(self.mbox[MBOX3].count_mbox_msgs(), 2)
        with open(self.mbox_path(MBOX3), 'ab') as f:
            f.write(NODATE_MSG)
        self.mbox.updateArchives(0)
        self.assertEqual(self.mbox[MBOX3].count_mbox_msgs(), 3)

    def test_detect_modification_same_size(self):
        """ a mailbox that changes only its modification date is reloaded """
        self.add_mbox()
        self.mbox.updateArchives(0)
        content = self.read_mbox3()
        self.write_mbox3(content.replace(b'Subject: [rlug] Re:',
                                         b'Subject: [rlug] RE:'))
        mtime = time.time() + 10
        os.utime(self.mbox_path(MBOX3), (mtime, mtime))
        self.mbox.updateArchives(0)
        obj = self.mbox[MBOX3]
        subjects = [obj.get_msg_subject(x) for x in obj.get_mbox_msgs()]
        self.assertIn('[rlug] RE: ***SPAM*** seg. fault. din drakxtools',
                      subjects)

    def test_manage_properties(self):
        self.mbox.manageProperties(title='T', path=self.tmpdir,
                                   mbox_ignore=MBOX2 + '\r\n\r\nTrash',
                                   update_cache='1')
        self.assertEqual(self.mbox.mbox_ignore, [MBOX2, 'Trash'])
        self.assertEqual(self.archive_ids(), [MBOX1])


class Test03_ArchiveMbox(MailArchiveTestCase):

    def test_filter_mboxes(self):
        obj = self.mbox.getArchives()[1]    #only mbox2.mbx
        subjects = [obj.get_msg_subject(x[1]) for x in obj.sortMboxMsgs('subject')]
        self.assertEqual(subjects, ['msvcr70.dll '])

    def test_list_mailboxes(self):
        self.assertEqual(self.mbox.listMailboxes(),
                         [MBOX1 + ' *', MBOX2 + ' *', MBOX3])


class Test04_MboxSorted(MailArchiveTestCase):

    def test_sort_archives(self):
        """ archives are sorted on the date of the first message, newest first """
        objs = self.mbox.getArchives()
        start = [x.starting[:6] for x in objs]
        self.assertEqual(start, [(2005, 3, 29, 1, 57, 52), (2003, 9, 11, 11, 18, 25)])
        self.assertEqual(self.archive_ids(), [MBOX1, MBOX2])

    def test_sort_author_ascendent(self):
        obj = self.mbox.getArchives()[0]    #only mbox1.mbx
        msgs_sorted = obj.sortMboxMsgs('author')
        msgs_sorted_ids = [obj.get_msg_id(x[1]) for x in msgs_sorted]
        self.assertEqual(msgs_sorted_ids, ['<424A5688.6050106@microsfot.co.uk>', \
            '<815f70cf050329015744ac9a43@mail.gmail.com>', '<815f70cf05033023503b4a9704@mail.gmail.com>', \
            '<16970.59764.819866.775606@gargle.gargle.HOWL>'])

    def test_sort_author_descendent(self):
        obj = self.mbox.getArchives()[0]    #only mbox1.mbx
        msgs_sorted = obj.sortMboxMsgs('author', 1)
        msgs_sorted_ids = [obj.get_msg_id(x[1]) for x in msgs_sorted]
        self.assertEqual(msgs_sorted_ids, ['<16970.59764.819866.775606@gargle.gargle.HOWL>', \
            '<815f70cf05033023503b4a9704@mail.gmail.com>', '<815f70cf050329015744ac9a43@mail.gmail.com>', \
            '<424A5688.6050106@microsfot.co.uk>'])

    def test_sort_subject_ascendent(self):
        obj = self.mbox.getArchives()[0]    #only mbox1.mbx
        msgs_sorted = obj.sortMboxMsgs('subject')
        msgs_sorted_ids = [obj.get_msg_id(x[1]) for x in msgs_sorted]
        self.assertEqual(msgs_sorted_ids, ['<16970.59764.819866.775606@gargle.gargle.HOWL>', \
            '<424A5688.6050106@microsfot.co.uk>', '<815f70cf05033023503b4a9704@mail.gmail.com>', \
            '<815f70cf050329015744ac9a43@mail.gmail.com>'])

    def test_sort_subject_descendent(self):
        obj = self.mbox.getArchives()[0]    #only mbox1.mbx
        msgs_sorted = obj.sortMboxMsgs('subject', 1)
        msgs_sorted_ids = [obj.get_msg_id(x[1]) for x in msgs_sorted]
        self.assertEqual(msgs_sorted_ids, ['<815f70cf050329015744ac9a43@mail.gmail.com>', \
            '<815f70cf05033023503b4a9704@mail.gmail.com>', '<424A5688.6050106@microsfot.co.uk>', \
            '<16970.59764.819866.775606@gargle.gargle.HOWL>'])

    def test_sort_date_ascendent(self):
        obj = self.mbox.getArchives()[0]    #only mbox1.mbx
        msgs_sorted = obj.sortMboxMsgs('date')
        msgs_sorted_ids = [obj.get_msg_id(x[1]) for x in msgs_sorted]
        self.assertEqual(msgs_sorted_ids, ['<815f70cf050329015744ac9a43@mail.gmail.com>', \
            '<424A5688.6050106@microsfot.co.uk>', '<16970.59764.819866.775606@gargle.gargle.HOWL>', \
            '<815f70cf05033023503b4a9704@mail.gmail.com>'])

    def test_sort_date_descendent(self):
        obj = self.mbox.getArchives()[0]    #only mbox1.mbx
        msgs_sorted = obj.sortMboxMsgs('date', 1)
        msgs_sorted_ids = [obj.get_msg_id(x[1]) for x in msgs_sorted]
        self.assertEqual(msgs_sorted_ids, ['<815f70cf05033023503b4a9704@mail.gmail.com>', \
            '<16970.59764.819866.775606@gargle.gargle.HOWL>', '<424A5688.6050106@microsfot.co.uk>', \
            '<815f70cf050329015744ac9a43@mail.gmail.com>'])

    def test_sort_thread(self):
        obj = self.mbox.getArchives()[0]    #only mbox1.mbx
        msgs_sorted = obj.sortMboxMsgs('thread')
        msgs_sorted_ids = [obj.get_msg_id(x[1]) for x in msgs_sorted]
        self.assertEqual(msgs_sorted_ids, ['<815f70cf050329015744ac9a43@mail.gmail.com>', \
            '<424A5688.6050106@microsfot.co.uk>', '<16970.59764.819866.775606@gargle.gargle.HOWL>', \
            '<815f70cf05033023503b4a9704@mail.gmail.com>'])
        self.assertEqual([x[0] for x in msgs_sorted], [0, 1, 1, 2])


class Test05_Pages(MailArchiveTestCase):
    """ render the public pages to catch template errors """

    def setUpArchives(self):
        with open(self.mbox_path(MBOX4), 'wb') as f:
            f.write(mbox_with_attachment())

    def set_form(self, **kw):
        self.app.REQUEST.form.update(kw)

    def test_load_8bit_mbox(self):
        obj = self.mbox[MBOX4]
        self.assertEqual(obj.count_mbox_msgs(), 3)
        msg = obj.cache['latin1.1']
        self.assertEqual(obj.get_msg_subject(msg), 'Gr&#252;&#223;e &lt;b&gt;')
        self.assertEqual(obj.get_msg_from(msg), 'J&#252;rgen')
        self.assertEqual(obj.get_msg_date(obj.cache['nodate.2']), None)
        self.assertEqual(obj.starting[:3], (2005, 6, 21))
        self.assertEqual(obj.ending[:3], (2005, 6, 22))

    def test_get_mbox_msg_offsets(self):
        obj = self.mbox[MBOX4]
        body = obj.get_mbox_msg('latin1.1')
        self.assertTrue(body.startswith(b'Message-ID: <latin1.1@example.com>'))
        self.assertTrue(body.endswith(b'Sch\xf6ne Gr\xfc\xdfe & <tschau>\n\n'))

    def test_sort_without_date(self):
        obj = self.mbox[MBOX4]
        ids = [obj.get_msg_index(x[1]) for x in obj.sortMboxMsgs('date')]
        self.assertEqual(ids, ['nodate.2', '42B811E8.7090602', 'latin1.1'])
        msgs = obj.sortMboxMsgs('thread')
        self.assertEqual([(x[0], obj.get_msg_index(x[1])) for x in msgs],
                         [(0, 'latin1.1'), (1, 'nodate.2'), (0, '42B811E8.7090602')])

    def test_folder_index(self):
        html = self.mbox.index_html()
        self.assertIn('href="http://nohost/mail_archive/%s?skey=date&amp;rkey=1"' % MBOX4, html)
        self.assertIn('2005-06-21 - 2005-06-22', html)

    def test_archive_index(self):
        obj = self.mbox[MBOX4]
        html = obj.index_html()
        self.assertIn('Gr&#252;&#223;e &lt;b&gt;', html)
        self.assertIn('message_html?id=latin1.1', html)
        self.assertIn('class="zebraeven"', html)

    def test_archive_thread_view(self):
        self.set_form(skey='thread')
        html = self.mbox[MBOX4].index_html()
        self.assertIn(' ------ ', html)
        self.assertIn('no date', html)

    def test_message_page(self):
        self.set_form(id='latin1.1', skey='date')
        html = self.mbox[MBOX4].message_html()
        self.assertIn('<h1>Gr&#252;&#223;e &lt;b&gt;</h1>', html)
        self.assertIn('Sch&#246;ne Gr&#252;&#223;e &amp; &lt;tschau&gt;', html)
        # latin1.1 is the newest message
        self.assertIn('Previous message', html)
        self.assertNotIn('Next message', html)
        self.assertIn('id=42B811E8.7090602">Re: test email</a>', html)

    def test_message_page_attachments(self):
        self.set_form(id='42B811E8.7090602')
        html = self.mbox[MBOX4].message_html()
        self.assertIn('download_html?id=42B811E8.7090602&amp;name=test.png', html)

    def test_message_page_invalid_id(self):
        html = self.mbox[MBOX4].message_html()
        self.assertIn('Invalid message id', html)

    def test_download_attachment(self):
        with open(os.path.join(DATA_PATH, 'test.png'), 'rb') as f:
            png = f.read()
        obj = self.mbox[MBOX4]
        data = obj.download_html('42B811E8.7090602', 'test.png')
        self.assertEqual(data, png)
        response = self.app.REQUEST.RESPONSE
        self.assertEqual(response.getHeader('Content-Type'), 'image/png')
        self.assertEqual(response.getHeader('Content-Disposition'),
                         'attachment;filename=test.png')
        self.assertRaises(NotFound, obj.download_html,
                          '42B811E8.7090602', 'missing.png')

    def test_download_attachment_traversal(self):
        obj = self.mbox[MBOX4]
        f = obj._getOb('42B811E8.7090602+++test.png')
        self.assertEqual(f.content_type, 'image/png')
        self.assertEqual(self.app.REQUEST.RESPONSE.getHeader('Content-Disposition'),
                         'attachment;filename=test.png')

    def test_index_rdf(self):
        response = self.app.REQUEST.RESPONSE
        rdf = self.mbox.index_rdf(self.app.REQUEST, response)
        self.assertIn('<title>Gr&amp;#252;&amp;#223;e &amp;lt;b&amp;gt;</title>', rdf)
        self.assertIn('<dc:date>2005-06-22T10:00:00</dc:date>', rdf)

    def test_properties_page(self):
        html = self.mbox.properties_html()
        self.assertIn('%s *' % MBOX4, html)
        self.assertIn('Invalid connection values!', html)

    def test_index_xslt(self):
        xslt = self.mbox.index_xslt()
        self.assertIn('<xsl:stylesheet', xslt)
        self.assertEqual(self.app.REQUEST.RESPONSE.getHeader('Content-Type'),
                         'text/xml; charset=utf-8')
