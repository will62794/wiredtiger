#
# coverage_pct = 1.0
# 155 traces
#

# [TEST_TAGS]
# transactions
# [END_TAGS]

import wttest
import wiredtiger
from wtscenario import make_scenarios
from helper import simulate_crash_restart

class test_txn_mbt(wttest.WiredTigerTestCase):

    def check_action(self, action_fn, expected_res, expected_exception):
        res = None
        try:
            action_fn()
        except wiredtiger.WiredTigerError as e:
            res = e
        self.assertEquals(res, None)
        self.assertTrue(wiredtiger.wiredtiger_strerror(expected_exception) in str(res))

    def evict(self, k):
        evict_cursor = self.session.open_cursor(self.uri, None, "debug=(release_evict)")
        self.session.begin_transaction()
        evict_cursor.set_key(k)
        evict_cursor.search()
        evict_cursor.reset()
        evict_cursor.close()
        self.session.rollback_transaction()

    def debug_info(self):
        with self.expectedStdoutPattern('transaction state dump'):
            self.conn.debug_info('txn')

    def test_setup(self):
        key_format,value_format = "S","S"
        self.uri = 'table:test_txn01'
        self.session.create(self.uri, 'key_format=' + key_format + ',value_format=' + value_format)
        conn = self.conn
        self.cursors = {}
        self.conn.set_timestamp('oldest_timestamp='+self.timestamp_str(1))

    def check_timestamps(self, all_durable=None, stable_ts=None, oldest_ts=None):
        if all_durable is not None:
            self.assertTimestampsEqual(self.conn.query_timestamp('get=all_durable'), str(all_durable))
        if stable_ts is not None:
            self.assertTimestampsEqual(self.conn.query_timestamp('get=stable_timestamp'), str(stable_ts))
        if oldest_ts is not None:
            self.assertTimestampsEqual(self.conn.query_timestamp('get=oldest_timestamp'), str(oldest_ts))

    def check_response(self, res, err_code, sret=None):
        if err_code == "WT_ROLLBACK":
            self.assertNotEqual(res, None)
            self.assertTrue(wiredtiger.wiredtiger_strerror(wiredtiger.WT_ROLLBACK) in str(res))
        elif err_code == "WT_NOTFOUND":
            # lines.append("self.assertEqual(res, None)")
            self.assertEqual(sret, wiredtiger.WT_NOTFOUND)
        elif err_code == "WT_PREPARE_CONFLICT":
            self.assertTrue(wiredtiger.wiredtiger_strerror(wiredtiger.WT_PREPARE_CONFLICT) in str(res))
        else:
            self.assertEquals(res, None)
            # if action_name == "TransactionRemove":
                # lines.append("self.assertEquals(sret, 0)")

    def crash(self):
        simulate_crash_restart(self, ".", "RESTART")

    def begin_transaction(self, tid, sess, readTs, ignorePrepare, res_expected, err_code):
        res,sret = None,None
        try:
            sess.begin_transaction(f'ignore_prepare={ignorePrepare},read_timestamp=' + self.timestamp_str(readTs));self.cursors[tid] = self.cursors[tid] = sess.open_cursor(self.uri, None)
            self.assertTimestampsEqual(sess.query_timestamp('get=read'), str(readTs))
        except wiredtiger.WiredTigerError as e:
            res = e
        # self.assertEquals(res, res_expected)
        self.check_response(res, err_code)

    def transaction_write(self, tid, k, res_expected, err_code):
        res,sret = None,None
        try:
            self.cursors[tid].set_key(k);self.cursors[tid].set_value(tid);self.cursors[tid].insert()
        except wiredtiger.WiredTigerError as e:
            res = e
        # self.assertEquals(res, res_expected)
        self.check_response(res, err_code)

    def transaction_read(self, tid, k, v, res_expected, err_code):
        res,sret = None,None
        try:
            self.cursors[tid].set_key(k)
            self.cursors[tid].read_stable()
            sret = self.cursors[tid].search()
                # self.assertEquals(res, None)
            if v == "NoValue":
                self.assertEquals(sret, wiredtiger.WT_NOTFOUND)
            else:
                # self.assertEquals(res, res_expected)
                self.assertEquals(self.cursors[tid].get_value(), v)
        except wiredtiger.WiredTigerError as e:
            res = e
        self.check_response(res, err_code, sret=sret)

    def transaction_remove(self, tid, k, res_expected, err_code):
        res,sret = None,None
        try:
            self.cursors[tid].set_key(k);sret = self.cursors[tid].remove()
        except wiredtiger.WiredTigerError as e:
            res = e
        # self.assertEquals(res, None)
        # self.assertEquals(sret, 0)
        self.check_response(res, err_code, sret=sret)


    def commit_transaction(self, sess, tid, commitTs, res_expected, err_code):
        res,sret = None,None
        try:
            # Set timestamp as well explicitly to cover that API.
            sess.timestamp_transaction_uint(wiredtiger.WT_TS_TXN_TYPE_COMMIT, commitTs)
            self.assertTimestampsEqual(sess.query_timestamp('get=commit'), str(commitTs))
            sess.commit_transaction('commit_timestamp=' + self.timestamp_str(commitTs))
        except wiredtiger.WiredTigerError as e:
            res = e
        # self.assertEquals(res, res_expected)
        self.check_response(res, err_code)
    
    def abort_transaction(self, sess, tid, res_expected, err_code):
        res,sret = None,None
        try:
            sess.rollback_transaction()
        except wiredtiger.WiredTigerError as e:
            res = e
        self.assertEquals(res, None)

    def prepare_transaction(self, sess, prepareTs, res_expected, err_code):
        res,sret = None,None
        try:
            sess.prepare_transaction('prepare_timestamp=' + self.timestamp_str(prepareTs))
            self.assertTimestampsEqual(sess.query_timestamp('get=prepare'), str(prepareTs))
        except wiredtiger.WiredTigerError as e:
            res = e
        # self.assertEquals(res, None)
        self.check_response(res, err_code)

    def commit_prepared_transaction(self, sess, commitTs, durableTs, res_expected, err_code):
        res,sret = None,None
        try:
            sess.commit_transaction('commit_timestamp=' + self.timestamp_str(commitTs) + ',durable_timestamp=' + self.timestamp_str(durableTs))
        except wiredtiger.WiredTigerError as e:
            res = e
        self.check_response(res, err_code)

    # TODO: Make use of this.
    def set_oldest_timestamp(self, ts, err_code):
        try:
            self.conn.set_timestamp('oldest_timestamp='+self.timestamp_str(ts))
        except wiredtiger.WiredTigerError as e:
            res = e
        self.check_response(res, err_code)

    def truncate(self, sess, key1, key2, res_expected, err_code):
        lo_cursor = sess.open_cursor(self.uri)
        hi_cursor = sess.open_cursor(self.uri)
        lo_cursor.set_key(key1)
        hi_cursor.set_key(key2)
        lo_cursor.search()
        hi_cursor.search()
        try:
            err = sess.truncate(None, lo_cursor, hi_cursor, None)
        except wiredtiger.WiredTigerError as e:
            if wiredtiger.wiredtiger_strerror(wiredtiger.WT_ROLLBACK) in str(e):
                err = WT_ROLLBACK
            elif wiredtiger.wiredtiger_strerror(wiredtiger.WT_PREPARE_CONFLICT) in str(e):
                err = WT_PREPARE_CONFLICT
            else:
                raise e
        lo_cursor.close()
        hi_cursor.close()
    def test_trace_0(self):
        self.test_setup()
        sess_t1 = self.conn.open_session();sess_t2 = self.conn.open_session();sess_t3 = self.conn.open_session()

        self.begin_transaction("t2", sess_t2, 1, "false", None, "OK")
        self.transaction_write("t2", "k1", None, "OK")
        self.transaction_write("t2", "k2", None, "OK")
        self.transaction_read("t2", "k1", "t2", None, "OK")
        self.transaction_read("t2", "k2", "t2", None, "OK")
        self.commit_transaction(sess_t2, "t2", 2, None, "OK")
        self.check_timestamps(all_durable=2, stable_ts=None, oldest_ts=None)
        self.begin_transaction("t1", sess_t1, 2, "false", None, "OK")
        self.check_timestamps(all_durable=2, stable_ts=None, oldest_ts=None)
        self.transaction_write("t1", "k1", None, "OK")
        self.check_timestamps(all_durable=2, stable_ts=None, oldest_ts=None)
        self.transaction_write("t1", "k2", None, "OK")
        self.check_timestamps(all_durable=2, stable_ts=None, oldest_ts=None)
        self.transaction_read("t1", "k1", "t1", None, "OK")
        self.check_timestamps(all_durable=2, stable_ts=None, oldest_ts=None)
        self.transaction_read("t1", "k2", "t1", None, "OK")
        self.check_timestamps(all_durable=2, stable_ts=None, oldest_ts=None)
        self.commit_transaction(sess_t1, "t1", 3, None, "OK")
        self.check_timestamps(all_durable=3, stable_ts=None, oldest_ts=None)

        self.debug_info()
        [self.cursors[c].close() for c in self.cursors]

    def test_trace_1(self):
        self.test_setup()
        sess_t1 = self.conn.open_session();sess_t2 = self.conn.open_session();sess_t3 = self.conn.open_session()

        self.begin_transaction("t3", sess_t3, 1, "false", None, "OK")
        self.transaction_write("t3", "k1", None, "OK")
        self.commit_transaction(sess_t3, "t3", 2, None, "OK")


        self.begin_transaction("t1", sess_t1, 2, "false", None, "OK")
        self.begin_transaction("t2", sess_t2, 2, "false", None, "OK")
        
        # self.transaction_write("t1", "k1", None, "OK")
        # self.transaction_write("t1", "k2", None, "OK")
        # self.transaction_read("t1", "k1", "t1", None, "OK")
        # self.transaction_read("t1", "k2", "t1", None, "OK")


        self.transaction_write("t2", "k1", None, "OK")


        self.cursors["t1"].set_key("k1")
        self.cursors["t1"].read_stable()
        sret = self.cursors["t1"].search()

        # print(sret)


        self.commit_transaction(sess_t1, "t1", 3, None, "OK")
        self.commit_transaction(sess_t2, "t2", 4, None, "OK")
        # self.check_timestamps(all_durable=2, stable_ts=None, oldest_ts=None)
        # self.begin_transaction("t2", sess_t2, 2, "false", None, "OK")
        # self.check_timestamps(all_durable=2, stable_ts=None, oldest_ts=None)
        # self.transaction_write("t2", "k1", None, "OK")
        # self.check_timestamps(all_durable=2, stable_ts=None, oldest_ts=None)
        # self.transaction_write("t2", "k2", None, "OK")
        # self.check_timestamps(all_durable=2, stable_ts=None, oldest_ts=None)
        # self.transaction_read("t2", "k2", "t2", None, "OK")
        # self.check_timestamps(all_durable=2, stable_ts=None, oldest_ts=None)
        # self.transaction_read("t2", "k1", "t2", None, "OK")
        # self.check_timestamps(all_durable=2, stable_ts=None, oldest_ts=None)
        # self.commit_transaction(sess_t2, "t2", 3, None, "OK")
        # self.check_timestamps(all_durable=3, stable_ts=None, oldest_ts=None)

        self.debug_info()
        [self.cursors[c].close() for c in self.cursors]

    def test_trace_2(self):
        self.test_setup()
        sess_t1 = self.conn.open_session();sess_t2 = self.conn.open_session();sess_t3 = self.conn.open_session()

        self.begin_transaction("t1", sess_t1, 1, "false", None, "OK")
        self.transaction_write("t1", "k1", None, "OK")
        self.transaction_write("t1", "k2", None, "OK")
        self.transaction_read("t1", "k1", "t1", None, "OK")
        self.transaction_read("t1", "k2", "t1", None, "OK")
        self.commit_transaction(sess_t1, "t1", 2, None, "OK")
        self.check_timestamps(all_durable=2, stable_ts=None, oldest_ts=None)
        self.begin_transaction("t2", sess_t2, 2, "false", None, "OK")
        self.check_timestamps(all_durable=2, stable_ts=None, oldest_ts=None)
        self.transaction_write("t2", "k2", None, "OK")
        self.check_timestamps(all_durable=2, stable_ts=None, oldest_ts=None)
        self.transaction_read("t2", "k1", "t1", None, "OK")
        self.check_timestamps(all_durable=2, stable_ts=None, oldest_ts=None)
        self.transaction_read("t2", "k2", "t2", None, "OK")
        self.check_timestamps(all_durable=2, stable_ts=None, oldest_ts=None)
        self.commit_transaction(sess_t2, "t2", 3, None, "OK")
        self.check_timestamps(all_durable=3, stable_ts=None, oldest_ts=None)

        self.debug_info()
        [self.cursors[c].close() for c in self.cursors]

    def test_trace_3(self):
        self.test_setup()
        sess_t1 = self.conn.open_session();sess_t2 = self.conn.open_session();sess_t3 = self.conn.open_session()

        self.begin_transaction("t1", sess_t1, 1, "false", None, "OK")
        self.transaction_write("t1", "k1", None, "OK")
        self.transaction_write("t1", "k2", None, "OK")
        self.transaction_read("t1", "k1", "t1", None, "OK")
        self.transaction_read("t1", "k2", "t1", None, "OK")
        self.commit_transaction(sess_t1, "t1", 2, None, "OK")
        self.check_timestamps(all_durable=2, stable_ts=None, oldest_ts=None)
        self.begin_transaction("t2", sess_t2, 2, "false", None, "OK")
        self.check_timestamps(all_durable=2, stable_ts=None, oldest_ts=None)
        self.transaction_write("t2", "k1", None, "OK")
        self.check_timestamps(all_durable=2, stable_ts=None, oldest_ts=None)
        self.transaction_write("t2", "k2", None, "OK")
        self.check_timestamps(all_durable=2, stable_ts=None, oldest_ts=None)
        self.transaction_read("t2", "k1", "t2", None, "OK")
        self.check_timestamps(all_durable=2, stable_ts=None, oldest_ts=None)
        self.commit_transaction(sess_t2, "t2", 3, None, "OK")
        self.check_timestamps(all_durable=3, stable_ts=None, oldest_ts=None)

        self.debug_info()
        [self.cursors[c].close() for c in self.cursors]

    def test_trace_4(self):
        self.test_setup()
        sess_t1 = self.conn.open_session();sess_t2 = self.conn.open_session();sess_t3 = self.conn.open_session()

        self.begin_transaction("t1", sess_t1, 1, "false", None, "OK")
        self.transaction_write("t1", "k1", None, "OK")
        self.transaction_write("t1", "k2", None, "OK")
        self.transaction_read("t1", "k1", "t1", None, "OK")
        self.transaction_read("t1", "k2", "t1", None, "OK")
        self.commit_transaction(sess_t1, "t1", 3, None, "OK")
        self.check_timestamps(all_durable=3, stable_ts=None, oldest_ts=None)
        self.begin_transaction("t2", sess_t2, 3, "false", None, "OK")
        self.check_timestamps(all_durable=3, stable_ts=None, oldest_ts=None)
        self.transaction_write("t2", "k1", None, "OK")
        self.check_timestamps(all_durable=3, stable_ts=None, oldest_ts=None)
        self.transaction_write("t2", "k2", None, "OK")
        self.check_timestamps(all_durable=3, stable_ts=None, oldest_ts=None)
        self.transaction_read("t2", "k1", "t2", None, "OK")
        self.check_timestamps(all_durable=3, stable_ts=None, oldest_ts=None)
        self.transaction_read("t2", "k2", "t2", None, "OK")
        self.check_timestamps(all_durable=3, stable_ts=None, oldest_ts=None)

        self.debug_info()
        [self.cursors[c].close() for c in self.cursors]

    def test_trace_5(self):
        self.test_setup()
        sess_t1 = self.conn.open_session();sess_t2 = self.conn.open_session();sess_t3 = self.conn.open_session()

        self.begin_transaction("t2", sess_t2, 2, "false", None, "OK")
        self.transaction_write("t2", "k1", None, "OK")
        self.transaction_write("t2", "k2", None, "OK")
        self.transaction_read("t2", "k1", "t2", None, "OK")
        self.transaction_read("t2", "k2", "t2", None, "OK")
        self.commit_transaction(sess_t2, "t2", 3, None, "OK")
        self.check_timestamps(all_durable=3, stable_ts=None, oldest_ts=None)
        self.begin_transaction("t1", sess_t1, 3, "false", None, "OK")
        self.check_timestamps(all_durable=3, stable_ts=None, oldest_ts=None)
        self.transaction_write("t1", "k1", None, "OK")
        self.check_timestamps(all_durable=3, stable_ts=None, oldest_ts=None)
        self.transaction_write("t1", "k2", None, "OK")
        self.check_timestamps(all_durable=3, stable_ts=None, oldest_ts=None)
        self.transaction_read("t1", "k1", "t1", None, "OK")
        self.check_timestamps(all_durable=3, stable_ts=None, oldest_ts=None)
        self.transaction_read("t1", "k2", "t1", None, "OK")
        self.check_timestamps(all_durable=3, stable_ts=None, oldest_ts=None)

        self.debug_info()
        [self.cursors[c].close() for c in self.cursors]

    def test_trace_6(self):
        self.test_setup()
        sess_t1 = self.conn.open_session();sess_t2 = self.conn.open_session();sess_t3 = self.conn.open_session()

        self.begin_transaction("t1", sess_t1, 1, "false", None, "OK")
        self.transaction_write("t1", "k1", None, "OK")
        self.transaction_write("t1", "k2", None, "OK")
        self.transaction_read("t1", "k1", "t1", None, "OK")
        self.commit_transaction(sess_t1, "t1", 2, None, "OK")
        self.check_timestamps(all_durable=2, stable_ts=None, oldest_ts=None)
        self.begin_transaction("t2", sess_t2, 2, "false", None, "OK")
        self.check_timestamps(all_durable=2, stable_ts=None, oldest_ts=None)
        self.transaction_write("t2", "k1", None, "OK")
        self.check_timestamps(all_durable=2, stable_ts=None, oldest_ts=None)
        self.transaction_read("t2", "k1", "t2", None, "OK")
        self.check_timestamps(all_durable=2, stable_ts=None, oldest_ts=None)
        self.transaction_write("t2", "k2", None, "OK")
        self.check_timestamps(all_durable=2, stable_ts=None, oldest_ts=None)
        self.transaction_read("t2", "k2", "t2", None, "OK")
        self.check_timestamps(all_durable=2, stable_ts=None, oldest_ts=None)
        self.commit_transaction(sess_t2, "t2", 3, None, "OK")
        self.check_timestamps(all_durable=3, stable_ts=None, oldest_ts=None)

        self.debug_info()
        [self.cursors[c].close() for c in self.cursors]

    def test_trace_7(self):
        self.test_setup()
        sess_t1 = self.conn.open_session();sess_t2 = self.conn.open_session();sess_t3 = self.conn.open_session()

        self.begin_transaction("t1", sess_t1, 1, "false", None, "OK")
        self.transaction_write("t1", "k1", None, "OK")
        self.transaction_write("t1", "k2", None, "OK")
        self.transaction_read("t1", "k1", "t1", None, "OK")
        self.transaction_read("t1", "k2", "t1", None, "OK")
        self.commit_transaction(sess_t1, "t1", 2, None, "OK")
        self.check_timestamps(all_durable=2, stable_ts=None, oldest_ts=None)
        self.begin_transaction("t2", sess_t2, 3, "false", None, "OK")
        self.check_timestamps(all_durable=2, stable_ts=None, oldest_ts=None)
        self.transaction_write("t2", "k1", None, "OK")
        self.check_timestamps(all_durable=2, stable_ts=None, oldest_ts=None)
        self.transaction_write("t2", "k2", None, "OK")
        self.check_timestamps(all_durable=2, stable_ts=None, oldest_ts=None)
        self.transaction_read("t2", "k1", "t2", None, "OK")
        self.check_timestamps(all_durable=2, stable_ts=None, oldest_ts=None)
        self.transaction_read("t2", "k2", "t2", None, "OK")
        self.check_timestamps(all_durable=2, stable_ts=None, oldest_ts=None)