#!/usr/bin/env python
#
# Public Domain 2014-present MongoDB, Inc.
# Public Domain 2008-2014 WiredTiger, Inc.
#
# This is free and unencumbered software released into the public domain.
#
# Anyone is free to copy, modify, publish, use, compile, sell, or
# distribute this software, either in source code form or as a compiled
# binary, for any purpose, commercial or non-commercial, and by any
# means.
#
# In jurisdictions that recognize copyright laws, the author or authors
# of this software dedicate any and all copyright interest in the
# software to the public domain. We make this dedication for the benefit
# of the public at large and to the detriment of our heirs and
# successors. We intend this dedication to be an overt act of
# relinquishment in perpetuity of all present and future rights to this
# software under copyright law.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#
# [TEST_TAGS]
# transactions
# [END_TAGS]

import wttest
import wiredtiger
from wtscenario import make_scenarios

# test_txn01.py
#    Transactions: basic functionality
class test_txn01(wttest.WiredTigerTestCase):
    nentries = 1000
    scenarios = make_scenarios([
        # ('col-f', dict(uri='file:text_txn01',key_format='r',value_format='S')),
        # ('col-t', dict(uri='table:text_txn01',key_format='r',value_format='S')),
        # ('fix-f', dict(uri='file:text_txn01',key_format='r',value_format='8t')),
        # ('fix-t', dict(uri='table:text_txn01',key_format='r',value_format='8t')),
        # ('row-f', dict(uri='file:text_txn01',key_format='S',value_format='S')),
        ('row-t', dict(uri='table:text_txn01',key_format='S',value_format='S')),
    ])

    def insert(self, cur, k, v):
        cur.set_key(k)
        cur.set_value(v)
        cur.insert()

    def test_increasing_commit_timestamp(self):
        key_format = "S"
        value_format = "S"
        uri = 'table:test_txn01'
        self.session.create(uri,
            'key_format=' + key_format +
            ',value_format=' + value_format)

        conn = self.conn
        sess_t1 = conn.open_session()

        sess_t1.begin_transaction('read_timestamp=' + self.timestamp_str(2))
        cursor_t1 = sess_t1.open_cursor(self.uri, None)
        cursor_t1.set_key("k1")
        cursor_t1.set_value("t1")
        cursor_t1.insert()
        sess_t1.commit_transaction('commit_timestamp=' + self.timestamp_str(5))

        # try:
        # except Exception as e:
            # wttest.WiredTigerTestCase.printVerbose(3, e)

    def test_conformance(self):
        key_format = "S"
        value_format = "S"
        self.session.create(self.uri,
            'key_format=' + key_format +
            ',value_format=' + value_format)

        conn = self.conn

        sess_t1 = conn.open_session()
        sess_t2 = conn.open_session()

        ## Action 0: MDBTxnStart, ['t2', 3, 'snapshot']
        res = None
        try:
            sess_t2.begin_transaction('read_timestamp=' + self.timestamp_str(3));cursor_t2 = sess_t1.open_cursor(self.uri, None)
        except wiredtiger.WiredTigerError as e:
            res = e
        self.assertEquals(res, None)

        ## Action 1: MDBTxnRead, ['t2', 'k1', 'NoValue']
        res = None
        try:
            cursor_t2.set_key("k1");sret = cursor_t2.search()
            self.assertEquals(sret, wiredtiger.WT_NOTFOUND)
        except wiredtiger.WiredTigerError as e:
            res = e
        self.assertEquals(res, None)

        ## Action 2: MDBTxnStart, ['t1', 4, 'snapshot']
        res = None
        try:
            sess_t1.begin_transaction('read_timestamp=' + self.timestamp_str(4));cursor_t1 = sess_t1.open_cursor(self.uri, None)
        except wiredtiger.WiredTigerError as e:
            res = e
        self.assertEquals(res, None)

        ## Action 3: MDBTxnWrite, ['t1', 'k1', 't1']
        res = None
        try:
            cursor_t1.set_key("k1");cursor_t1.set_value("t1");cursor_t1.insert()
        except wiredtiger.WiredTigerError as e:
            res = e
        self.assertEquals(res, None)

        ## Action 4: MDBTxnCommit, ['t2', 2]
        # TODOOO: Timestamps still not monotonic???
        res = None
        try:
            sess_t2.commit_transaction('commit_timestamp=' + self.timestamp_str(2))
        except wiredtiger.WiredTigerError as e:
            res = e
        self.assertEquals(res, None)

        # ## Action 5: MDBTxnStart, ['t2', 2, 'snapshot']
        # res = None
        # try:
        #     sess_t2.begin_transaction('read_timestamp=' + self.timestamp_str(2));cursor_t2 = sess_t1.open_cursor(self.uri, None)
        # except wiredtiger.WiredTigerError as e:
        #     res = e
        # self.assertEquals(res, None)

        # ## Action 6: MDBTxnWrite, ['t2', 'k1', 't2']
        # res = None
        # try:
        #     cursor_t2.set_key("k1");cursor_t2.set_value("t2");cursor_t2.insert()
        # except wiredtiger.WiredTigerError as e:
        #     res = e
        # self.assertNotEqual(res, None)
        # self.assertTrue(wiredtiger.wiredtiger_strerror(wiredtiger.WT_ROLLBACK) in str(e))


"""
    def test_basic(self):
        return
        key_format = "S"
        value_format = "S"
        self.session.create(self.uri,
            'key_format=' + key_format +
            ',value_format=' + value_format)

        # Very simple transactional API usage.

        sess_t1 = self.conn.open_session()
        sess_t2 = self.conn.open_session()
        sess_t3 = self.conn.open_session()

        # sess_t1.begin_transaction()
        sess_t1.begin_transaction('read_timestamp=' + self.timestamp_str(6))
        cursor1 = sess_t1.open_cursor(self.uri, None)
        cursor1.set_key("k1");cursor1.set_value("t1");cursor1.insert()
        # print("Inserting value")
        

        sess_t3.begin_transaction('read_timestamp=' + self.timestamp_str(6))
        cursor3 = sess_t3.open_cursor(self.uri, None)
        cursor3.set_key("k1")
        cursor3.set_value("t3")
        # sess_t3.rollback_transaction()

        # try:
        #     ret = cursor3.insert()
        #     # self.assertNotEqual(ret, wiredtiger.WT_NOTFOUND)
        # except wiredtiger.WiredTigerError as e:
        #     self.assertTrue(wiredtiger.wiredtiger_strerror(wiredtiger.WT_ROLLBACK) in str(e))
        #     # print(wiredtiger.WT_NOTFOUND)
        #     wttest.WiredTigerTestCase.printVerbose(3, e)
        #     # wttest.WiredTigerTestCase.printVerbose(3, type(e))
        #     wttest.WiredTigerTestCase.printVerbose(3, "hello world")
        #     pass


        # sess_t3.commit_transaction('commit_timestamp=' + self.timestamp_str(7))
        sess_t1.commit_transaction('commit_timestamp=' + self.timestamp_str(7))

        sess_t2.begin_transaction()
        cursor2 = sess_t2.open_cursor(self.uri, None)
        cursor2.set_key("k2")
        cursor2.set_value("t2")
        cursor2.insert()
        sess_t2.commit_transaction()

        # Read values.
        sess = self.conn.open_session()
        cursor = sess.open_cursor(self.uri, None)

        sess.begin_transaction('read_timestamp=' + self.timestamp_str(8))
        cursor.set_key("k1")
        ret = cursor.search()
        self.assertNotEqual(ret, wiredtiger.WT_NOTFOUND)
        ret = cursor.get_value()
        self.assertEqual(ret, "t1")
        sess.commit_transaction()


    # # Return the number of records visible to the cursor.
    # def cursor_count(self, cursor):
    #     count = 0
    #     # Column-store appends result in phantoms, ignore records unless they
    #     # have our flag value.
    #     for r in cursor:
    #         if self.value_format == 'S' or cursor.get_value() == 0xab:
    #             count += 1
    #     return count

    # # Checkpoint the database and assert the number of records visible to the
    # # checkpoint matches the expected value.
    # def check_checkpoint(self, expected):
    #     s = self.conn.open_session()
    #     s.checkpoint("name=test")
    #     cursor = s.open_cursor(self.uri, None, "checkpoint=test")
    #     self.assertEqual(self.cursor_count(cursor), expected)
    #     s.close()

    # # Open a cursor with snapshot isolation, and assert the number of records
    # # visible to the cursor matches the expected value.
    # def check_txn_cursor(self, level, expected):
    #     s = self.conn.open_session()
    #     cursor = s.open_cursor(self.uri, None)
    #     s.begin_transaction(level)
    #     self.assertEqual(self.cursor_count(cursor), expected)
    #     s.close()

    # # Open a session with snapshot isolation, and assert the number of records
    # # visible to the cursor matches the expected value.
    # def check_txn_session(self, level, expected):
    #     s = self.conn.open_session(level)
    #     cursor = s.open_cursor(self.uri, None)
    #     s.begin_transaction()
    #     self.assertEqual(self.cursor_count(cursor), expected)
    #     s.close()

    # def check(self, cursor, committed, total):
    #     # The cursor itself should see all of the records.
    #     if cursor != None:
    #         cursor.reset()
    #         self.assertEqual(self.cursor_count(cursor), total)

    #     # Read-uncommitted should see all of the records.
    #     # Snapshot and read-committed should see only committed records.
    #     self.check_txn_cursor('isolation=read-uncommitted', total)
    #     self.check_txn_session('isolation=read-uncommitted', total)

    #     self.check_txn_cursor('isolation=snapshot', committed)
    #     self.check_txn_session('isolation=snapshot', committed)

    #     self.check_txn_cursor('isolation=read-committed', committed)
    #     self.check_txn_session('isolation=read-committed', committed)

    #     # Checkpoints should only write committed items.
    #     self.check_checkpoint(committed)



"""





# Test that read-committed is the default isolation level.
# class test_read_committed_default(wttest.WiredTigerTestCase):
#     uri = 'table:test_txn'

#     # Return the number of records visible to the cursor.
#     def cursor_count(self, cursor):
#         count = 0
#         for r in cursor:
#             count += 1
#         return count

#     def test_read_committed_default(self):
#         self.session.create(self.uri, 'key_format=S,value_format=S')
#         cursor = self.session.open_cursor(self.uri, None)
#         self.session.begin_transaction()
#         cursor['key: aaa'] = 'value: aaa'
#         self.session.commit_transaction()
#         self.session.begin_transaction()
#         cursor['key: bbb'] = 'value: bbb'

#         s = self.conn.open_session()
#         cursor = s.open_cursor(self.uri, None)
#         s.begin_transaction("isolation=read-committed")
#         self.assertEqual(self.cursor_count(cursor), 1)
#         s.commit_transaction()
#         s.begin_transaction(None)
#         self.assertEqual(self.cursor_count(cursor), 1)
#         s.commit_transaction()
#         s.close()
