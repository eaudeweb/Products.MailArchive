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

import sys
import os.path
import re

from .mbox_email import mbox_email
from .mbox_filters import mbox_filters
from Products.MailArchive.Utils import Utils

SPAM = 0
KEEP = 1
UNSURE = 2


def iter_mbox_offsets(path):
    """ Yield (start, stop) byte offsets of each message, after its From line """
    with open(path, 'rb') as f:
        start = None
        while True:
            pos = f.tell()
            line = f.readline()
            if not line or line.startswith(b'From '):
                if start is not None:
                    yield start, pos
                if not line:
                    break
                start = f.tell()


def _sort_value(value):
    # messages without a parsable date sort first
    if value is None:
        return ()
    return value


class mbox(mbox_filters, Utils):

    def __init__(self, path):
        self.path = path
        self.size = os.path.getsize(self.path)
        self.last_modified = os.path.getmtime(self.path)
        self.cache = {}
        self.starting = None
        self.ending = None
        mbox_filters.__dict__['__init__'](self)
        self.process_mbox()

    def process_mbox(self):
        #open a MBOX file and process all its content
        self.cache = {}
        starting, ending = None, None
        with open(self.path, 'rb') as f:
            for start, stop in iter_mbox_offsets(self.path):
                f.seek(start)
                m = mbox_email(f.read(stop - start), headersonly=True)
                d = m.getDateTime()
                s = m.getSubject()
                (result, reason) = self.run_rules(s)
                if result:
                    if s == '': s = '(no subject)'
                    from_addr = m.getFrom()
                    f_addr = from_addr[0]
                    if not f_addr: f_addr = from_addr[1]
                    index = self.get_unique_id(m)
                    self.cache[index] = (
                        index, start, stop-start,
                        s, d, f_addr, m.getMessageID(), m.getInReplyTo(), m.getTo(), m.getCC()
                    )
                    #process starting, ending
                    if d is not None:
                        if starting is None or d < starting: starting = d
                        if ending is None or d > ending: ending = d
        self.starting, self.ending = starting, ending

    def get_msg_index(self, msg): return msg[0]
    def get_msg_offset(self, msg): return msg[1]
    def get_msg_size(self, msg): return msg[2]
    def get_msg_subject(self, msg): return msg[3]
    def get_msg_date(self, msg): return msg[4]
    def get_msg_from(self, msg): return msg[5]
    def get_msg_id(self, msg): return msg[6]
    def get_msg_inreplyto(self, msg): return msg[7]
    def get_msg_to(self, msg):  return msg[8]
    def get_msg_cc(self, msg):  return msg[9]

    def get_mbox_file(self):
        with open(self.path, 'rb') as f:
            return f.read()

    def get_mbox_msg(self, index):
        #given the message index in messages list returns the message body
        msg_body = b''
        cache_item = self.cache.get(index, None)
        if cache_item is not None:
            with open(self.path, 'rb') as f:
                f.seek(self.get_msg_offset(cache_item))
                msg_body = f.read(self.get_msg_size(cache_item))
        return msg_body

    def __get_mbox_thread(self, msgs, node, depth):
        tree = []
        l = [msg for msg in msgs if msg[7] == node]
        for msg in l:
            msgs.remove(msg)
        for msg in l:
            tree.append((depth, msg))
            tree.extend(self.__get_mbox_thread(msgs, msg[6], depth+1))
        return tree

    def get_mbox_thread(self, msgs):
        #builds threads
        r = self.__get_mbox_thread(msgs, '', 0)
        for x in msgs:
            r.append((0, x))
        return r

    def get_mbox_msgs(self):
        #returns the list of messages
        return list(self.cache.values())

    def count_mbox_msgs(self):
        #returns the number of messages
        return len(self.cache.keys())

    def sort_mbox_msgs(self, n, r):
        #returns a sorted list of messages
        return sorted(self.cache.values(),
                      key=lambda x: (_sort_value(x[n]), x[0]), reverse=bool(r))

    def sort_mbox_msgs_ci(self, n, r):
        #returns a sorted list of messages - sort without case-sensitivity
        return sorted(self.cache.values(),
                      key=lambda x: (x[n].lower(), x[0]), reverse=bool(r))

    def get_unique_id_OLD(self, msg):
        #returns a unique id for this message based on Message-ID
        # BUG:
        # - this fails for messages like Message-ID: <1363282668.6978.YahooMailNeo@web160104.mail.bf1.yahoo.com>
        # - always returns YahooMailNeo as ID and messages are lost
        msg_id = msg.getMessageID()
        try:
            m = re.search(r'([\w]*)@', msg_id)
            return m.group(1) or msg_id
        except:
            return msg_id

    def get_unique_id(self, msg):
        #returns a unique id for this message based on Message-ID
        #for a value like <1363282668.6978.YahooMailNeo@web160104.mail.bf1.yahoo.com>
        # <CA+b1K2njiA9UEMeZC=QD359iW=0XJd3OuHfBwWFOhVoN954cew@mail.gmail.com>
        #1363282668.6978.YahooMailNeo will be returned
        msg_id = msg.getMessageID()
        try:
            m = re.search(r'([\w\.]*)@', msg_id)
            return m.group(1) or msg_id
        except:
            return msg_id

class mbox_imap(mbox):

    def __init__(self, imap_client_ob, mailbox_name):
        self.mailbox_name = mailbox_name
        self.size = -1
        self.last_modified = -1
        self.cache = {}
        self.starting = None
        self.ending = None
        mbox_filters.__dict__['__init__'](self)
        self.process_mbox(imap_client_ob)

    def process_mbox(self, imap_client_ob):
        #open an IMAP mailbox
        self.cache = {}
        messages = imap_client_ob.getMailboxMessages(self.mailbox_name)
        starting, ending = None, None
        idx = 1
        for msg in messages:
            m = mbox_email(msg.as_bytes(), headersonly=True)
            d = m.getDateTimeEx()
            s = m.getSubjectEx()
            (result, reason) = self.run_rules(s)
            if result:
                if not s: s = '(no subject)'
                from_addr = m.getFrom()
                f = from_addr[0]
                if not f: f = from_addr[1]
                index = m.getMessageID()
                #we use the full Message-ID in order to be able to query for it in the mailbox
                start, stop = 0, 0
                self.cache[index] = (
                    index, start, stop-start,
                    s, d, f, m.getMessageID(), m.getInReplyTo(), m.getTo(), m.getCC()
                )
                #process starting, ending
                if d is not None:
                    if starting is None or d < starting: starting = d
                    if ending is None or d > ending: ending = d
            idx += 1
        self.starting, self.ending = starting, ending

    def get_mbox_msg(self, index, imap_client_ob):
        #given the message index in messages list returns the message body
        return imap_client_ob.getMailBoxMessageBody(self.mailbox_name, index)

def main():
    b = mbox(sys.argv[1])
    print(b.cache)
    print(b.sort_mbox_msgs(3, 0))

if __name__ == '__main__':
    main ()
