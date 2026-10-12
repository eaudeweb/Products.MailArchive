Version 1.6 (unreleased)
========================
* bugfix when adding mailbox with year in name
* Improve layout
* add 'To' to emails table columns
* add datatable and replace old style sorting
* configure for the Belgian Environment
  [valipod]
* Use PEP 420 namespace packages [dumitval]
* Fix the email address obfuscation and the message threading on Python 3
  [dumitval]
* Read mbox files as bytes and parse them with the email package [dumitval]
* Fix mailboxes and message pages failing on non-UTF-8 bytes [dumitval]
* Fix mbox_filters failing on string.strip, which left the folder empty
  [dumitval]
* Fix the message body decoded with the top-level charset instead of the
  text part charset [dumitval]
* Fix HTML message bodies showing unescaped entities [dumitval]
* Escape attribute values in cleanhtml.HTMLCleaner [dumitval]
* Escape text/plain bodies in mbox_email.getContentEx [dumitval]
* Fix decode_string keeping only the first encoded word [dumitval]
* Fix attachment download returning text instead of bytes [dumitval]
* Use filename*=UTF-8'' for non-ASCII attachment names [dumitval]
* Fix sorting failing on messages without a Date header [dumitval]
* Fix updateArchives raising BadRequest with no archive to delete
  [dumitval]
* Reload a mailbox when its size or its modification date changes
  [dumitval]
* Fix the mbox_ignore property and archive deletion failing on iterators
  [dumitval]
* Fix the IMAP client failing on bytes responses [dumitval]
* Do not connect to IMAP when imap_servername is empty [dumitval]
* Log mailbox load errors instead of ignoring them [dumitval]
* Port the tests to zope.testrunner [dumitval]

Version 1.5 (2016-12-08)
========================

* Turn MailArchive into an IMAP client [chiridra]
