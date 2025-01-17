
# [TEST_TAGS]
# transactions
# [END_TAGS]

import wttest
import wiredtiger
from wtscenario import make_scenarios

# test_txn01.py
#    Transactions: basic functionality
class test_txn01(wttest.WiredTigerTestCase):

    def test_trace_1(self):
        key_format = "S"
        value_format = "S"
        self.uri = 'table:test_txn01'
        self.session.create(self.uri,
            'key_format=' + key_format +
            ',value_format=' + value_format)

        conn = self.conn
        sess_t1 = conn.open_session()
        sess_t2 = conn.open_session()

        ### Action 1: MDBTxnStart(t2,1,snapshot)
        res = None
        try:
            sess_t2.begin_transaction('read_timestamp=' + self.timestamp_str(1));cursor_t2 = sess_t1.open_cursor(self.uri, None)
        except wiredtiger.WiredTigerError as e:
            res = e
        self.assertEquals(res, None)

        ### Action 2: MDBTxnCommit(t2,2)
        res = None
        try:
            sess_t2.commit_transaction('commit_timestamp=' + self.timestamp_str(2))
        except wiredtiger.WiredTigerError as e:
            res = e
        self.assertEquals(res, None)

        ### Action 3: MDBTxnStart(t1,2,snapshot)
        res = None
        try:
            sess_t1.begin_transaction('read_timestamp=' + self.timestamp_str(2));cursor_t1 = sess_t1.open_cursor(self.uri, None)
        except wiredtiger.WiredTigerError as e:
            res = e
        self.assertEquals(res, None)

        ### Action 4: MDBTxnStart(t2,1,snapshot)
        res = None
        try:
            sess_t2.begin_transaction('read_timestamp=' + self.timestamp_str(1));cursor_t2 = sess_t1.open_cursor(self.uri, None)
        except wiredtiger.WiredTigerError as e:
            res = e
        self.assertEquals(res, None)

        ### Action 5: MDBTxnWrite(t1,k1,t1)
        res = None
        try:
            cursor_t1.set_key("k1");cursor_t1.set_value("t1");cursor_t1.insert()
        except wiredtiger.WiredTigerError as e:
            res = e
        self.assertEquals(res, None)

        ### Action 6: MDBTxnCommit(t2,3)
        res = None
        try:
            sess_t2.commit_transaction('commit_timestamp=' + self.timestamp_str(3))
        except wiredtiger.WiredTigerError as e:
            res = e
        self.assertEquals(res, None)

        ### Action 7: MDBTxnStart(t2,3,snapshot)
        res = None
        try:
            sess_t2.begin_transaction('read_timestamp=' + self.timestamp_str(3));cursor_t2 = sess_t1.open_cursor(self.uri, None)
        except wiredtiger.WiredTigerError as e:
            res = e
        self.assertEquals(res, None)

        ### Action 8: MDBTxnAbort(t2)
        res = None
        try:
            sess_t2.rollback_transaction()
        except wiredtiger.WiredTigerError as e:
            res = e
        self.assertEquals(res, None)

        ### Action 9: MDBTxnStart(t2,2,snapshot)
        res = None
        try:
            sess_t2.begin_transaction('read_timestamp=' + self.timestamp_str(2));cursor_t2 = sess_t1.open_cursor(self.uri, None)
        except wiredtiger.WiredTigerError as e:
            res = e
        self.assertEquals(res, None)

        ### Action 10: MDBTxnAbort(t1)
        res = None
        try:
            sess_t1.rollback_transaction()
        except wiredtiger.WiredTigerError as e:
            res = e
        self.assertEquals(res, None)

        ### Action 11: MDBTxnRead(t2,k2,NoValue)
        res = None
        try:
            cursor_t2.set_key("k2");sret = cursor_t2.search();self.assertEquals(sret, wiredtiger.WT_NOTFOUND)
        except wiredtiger.WiredTigerError as e:
            res = e
        self.assertEquals(res, None)

        ### Action 12: MDBTxnWrite(t2,k2,t2)
        res = None
        try:
            cursor_t2.set_key("k2");cursor_t2.set_value("t2");cursor_t2.insert()
        except wiredtiger.WiredTigerError as e:
            res = e
        self.assertEquals(res, None)

        ### Action 13: MDBTxnStart(t1,4,snapshot)
        res = None
        try:
            sess_t1.begin_transaction('read_timestamp=' + self.timestamp_str(4));cursor_t1 = sess_t1.open_cursor(self.uri, None)
        except wiredtiger.WiredTigerError as e:
            res = e
        self.assertEquals(res, None)

        ### Action 14: MDBTxnCommit(t1,5)
        res = None
        try:
            sess_t1.commit_transaction('commit_timestamp=' + self.timestamp_str(5))
        except wiredtiger.WiredTigerError as e:
            res = e
        self.assertEquals(res, None)

