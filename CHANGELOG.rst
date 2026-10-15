Version 1.6 (unreleased)
========================
* bugfix when adding mailbox with year in name
* Improve layout
* add 'To' to emails table columns
* add datatable and replace old style sorting
* configure for the Belgian Environment
  [valipod]
* getContent: decode the body with the charset of the text part, replace
  undecodable bytes and fall back to Latin-1 for unknown charsets; the
  archive showed UTF-8 bodies as mojibake ("collÃ¨gues")
* codecs_lookup: map the charset_table aliases, so header parts in
  window-1252, x-unknown, nil and default_charset are no longer dropped
* decode_string: join all the decoded parts of the header, not only the
  first encoded word
* keep the space between an encoded word and the plain text around it in
  the subject and the names; Python 2 decode_header strips it
* decode the 8-bit header parts and the raw 8-bit addresses in From, To and
  Cc as UTF-8 or Latin-1; the message page failed at random on such
  addresses with UnicodeDecodeError
* getContentEx (IMAP view): escape text/plain bodies and decode HTML bodies
  without a charset
* getInReplyTo / getMessageID: strip folded header whitespace
* getAttachment: compare the attachment names as UTF-8, so attachments with
  non-ASCII names are found
* HTMLCleaner: escape the kept attribute values, which could inject HTML
* imap_client.connOpen: do not connect to localhost:993 when no IMAP server
  is set
* updateArchives: reload a mailbox when its size or its modification time
  changed (was: and)
* _add_archives / _add_archives_imap: log the exception instead of ignoring
  it
  [dumitval]

Version 1.5 (2016-12-08)
========================

* Turn MailArchive into an IMAP client [chiridra]
