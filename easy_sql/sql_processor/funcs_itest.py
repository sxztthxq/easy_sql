import json
import unittest
from typing import Tuple

from easy_sql.base_test import TEST_PG_URL, TEST_CH_URL
from easy_sql.local_spark import LocalSpark
from easy_sql.sql_processor import Step, FuncRunner
from easy_sql.sql_processor.backend import Partition, SparkTable
from easy_sql.sql_processor.backend.base import Col, Backend
from easy_sql.sql_processor.backend.rdb import RdbBackend
from easy_sql.sql_processor.context import ProcessorContext, VarsContext, TemplatesContext
from easy_sql.sql_processor.funcs_common import ColumnFuncs, TableFuncs, AlertFunc, Alerter
from easy_sql.sql_processor.funcs_rdb import PartitionFuncs
from easy_sql.sql_processor.funcs_spark import PartitionFuncs as SparkPartitionFuncs, CacheFuncs, ParallelismFuncs, IOFuncs
from easy_sql.sql_processor.step import ReportCollector


class FuncsRdbTest(unittest.TestCase):
    test_table_name = 't.func_test'

    def test_funcs_pg(self):
        from easy_sql.sql_processor.backend.postgres import PostgresBackend
        backend = PostgresBackend(TEST_PG_URL)
        int_type, str_type, pt_type = 'int', 'text', 'text'
        self.run_test(backend, (int_type, str_type, pt_type))

    def test_funcs_ch(self):
        from easy_sql.sql_processor.backend.clickhouse import ChBackend
        backend = ChBackend(TEST_CH_URL)
        int_type, str_type, pt_type = 'Nullable(Int32)', 'String', 'String'
        self.run_test(backend, (int_type, str_type, pt_type))

    def test_funcs_spark(self):
        from easy_sql.sql_processor.backend.spark import SparkBackend
        backend = SparkBackend(LocalSpark.get())
        int_type, str_type, pt_type = 'int', 'string', 'string'
        self.run_test(backend, (int_type, str_type, pt_type))

        cf = CacheFuncs(backend.spark)
        backend.create_cache_table(SparkTable(backend.exec_native_sql(f'select * from {self.test_table_name}')), 'tc')
        self.assertEqual(backend.exec_sql('select count(1) from tc').collect()[0][0], 2)
        cf.unpersist('tc')

        pf = ParallelismFuncs(backend.spark)
        self.assertEqual(backend.exec_sql('select count(1) from tc').collect()[0][0], 2)
        pf.coalesce('tc', '1')
        self.assertEqual(backend.exec_sql('select count(1) from tc').collect()[0][0], 2)
        pf.repartition('tc', '2')
        self.assertEqual(backend.exec_sql('select count(1) from tc').collect()[0][0], 2)
        pf.repartition_by_column('tc', 'pt')
        self.assertEqual(backend.exec_sql('select count(1) from tc').collect()[0][0], 2)
        pf.set_shuffle_partitions('2')
        self.assertEqual(backend.exec_sql('select count(1) from tc').collect()[0][0], 2)

        iof = IOFuncs(backend.spark)
        iof.write_csv('tc', 'file:///tmp/easysql-ut/test_write_csv')
        iof.rename_csv_output('file:///tmp/easysql-ut/test_write_csv', '/tmp/easysql-ut/test_write.csv')
        iof.write_json_local('tc', '/tmp/easysql-ut/test_write.json')
        self.assertEqual(len(json.loads(open('/tmp/easysql-ut/test_write.json').read())), 2)
        json.dump({'a': '0'}, open('/tmp/easysql-ut/test_write.json', 'w'))
        iof.update_json_local(ProcessorContext(VarsContext({'a': 1}, {'b': [1, 2]}), TemplatesContext()),
                              'a,', 'b', '', '/tmp/easysql-ut/test_write.json')
        self.assertEqual(json.loads(open('/tmp/easysql-ut/test_write.json').read())['a'], 1)
        self.assertEqual(json.loads(open('/tmp/easysql-ut/test_write.json').read())['b'], [1, 2])
        iof.update_json_local(ProcessorContext(VarsContext({'a': 2}, {'b': [1, 2]}), TemplatesContext()),
                              'a,', '', 'c.d', '/tmp/easysql-ut/test_write.json')
        self.assertEqual(json.loads(open('/tmp/easysql-ut/test_write.json').read())['c']['d']['a'], 2)

    def run_test(self, backend: Backend, types: Tuple[str, str, str]):
        try:
            self._run_test(backend, types)
        finally:
            backend.clean()

    def _run_test(self, backend: Backend, types: Tuple[str, str, str]):
        table_name = self.test_table_name

        int_type, str_type, pt_type = types
        if isinstance(backend, RdbBackend):
            backend.exec_native_sql(backend.sql_dialect.drop_db_sql('t'))
        backend.create_table_with_data(table_name,
                                       [['1', 1, '2022-01-01'], ['2', None, '2022-01-02']],
                                       [Col('id', str_type), Col('val', int_type), Col('pt', pt_type)],
                                       [Partition(field='pt')])

        pf = PartitionFuncs(backend) if isinstance(backend, RdbBackend) else SparkPartitionFuncs(backend)

        class _ReportCollector(ReportCollector):
            def collect_report(self, step: 'Step', status: str = None, message: str = None):
                pass

        step = Step('1', _ReportCollector(), FuncRunner({'bool': lambda x: x == '1'}),
                    select_sql='select 0 as a')

        self.assertEqual(pf.get_first_partition(table_name), '2022-01-01')
        self.assertTrue(pf.is_first_partition(table_name, '2022-01-01'))
        self.assertTrue(pf.is_not_first_partition(table_name, '2022-01-02'))
        self.assertTrue(pf.partition_exists(table_name, '2022-01-02'))
        self.assertFalse(pf.partition_exists(table_name, '2022-01-03'))
        self.assertTrue(pf.partition_not_exists(table_name, '2022-01-03'))
        self.assertTrue(pf.ensure_partition_or_first_partition_exists(step, table_name, '2022-01-01'))
        self.assertTrue(pf.ensure_partition_or_first_partition_exists(step, table_name, '2022-01-02'))
        self.assertTrue(pf.ensure_partition_exists(step, table_name, '2022-01-01'))
        self.assertFalse(pf.previous_partition_exists(table_name, '2022-01-01'))
        self.assertTrue(pf.previous_partition_exists(table_name, '2022-01-03'))
        self.assertFalse(pf.ensure_partition_exists(step, table_name, '2022-01-03'))
        self.assertTrue(pf.ensure_dwd_partition_exists(step, table_name, '2022-01-01', 'id'))
        self.assertFalse(pf.ensure_dwd_partition_exists(step, table_name, '2022-01-02', 'val'))
        self.assertEqual(pf.get_partition_or_first_partition(table_name, '2021-01-02'), '2022-01-01')
        self.assertEqual(pf.get_partition_or_first_partition(table_name, '2022-01-02'), '2022-01-02')
        self.assertEqual(pf.get_first_partition_optional(table_name), '2022-01-01')
        self.assertEqual(pf.get_last_partition(table_name), '2022-01-02')
        self.assertEqual(pf.get_partition_cols(table_name), ['pt'])
        self.assertEqual(pf.get_partition_col(table_name), 'pt')
        self.assertTrue(pf.has_partition_col(table_name))

        f = ColumnFuncs(backend)
        self.assertEqual(f.all_cols_with_exclusion_expr(table_name, 'pt'), 'func_test.id, func_test.val')
        self.assertEqual(f.all_cols_without_one_expr(table_name, 'pt'), 'func_test.id, func_test.val')

        f = TableFuncs(backend)

        self.assertFalse(f.ensure_no_null_data_in_table(step, table_name))
        self.assertTrue(f.ensure_no_null_data_in_table(step, table_name, "id='1'"))
        self.assertTrue(f.check_not_null_column_in_table(step, table_name, 'id'))
        self.assertFalse(f.check_not_null_column_in_table(step, table_name, 'val'))
        self.assertTrue(f.check_not_null_column_in_table(step, table_name, 'val', "id='1'"))

        class _Alerter(Alerter):

            def __init__(self):
                self.alert_msg = None

            def send_alert(self, msg: str, mentioned_users: str = ''):
                self.alert_msg = msg

        alerter = _Alerter()
        f = AlertFunc(backend, alerter)
        f.alert(step, ProcessorContext(VarsContext({'a': 1}), TemplatesContext()), 'test', 'bool({a})', 'result: {a}', 'a,b,c')
        self.assertTrue(alerter.alert_msg is not None)
