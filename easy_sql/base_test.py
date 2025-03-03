import os
import uuid
from datetime import datetime
from typing import Dict, List

from pyspark.sql import SparkSession

from easy_sql.sql_processor.backend.rdb import SqlExpr
from easy_sql.sql_processor import SqlProcessor
from .local_spark import LocalSpark
from .logger import log_time


def should_run_integration_test(key: str = None):
    if key is None or key in ['pg', 'ch', 'mc', 'bq']:
        return False
    return False


TEST_PG_URL = os.environ.get('PG_URL', 'postgresql://postgres:123456@testpg:15432/postgres')
TEST_CH_URL = os.environ.get('CLICKHOUSE_URL', 'clickhouse+native://default@testch:30123')
TEST_BQ_URL = os.environ.get('BQ_URL', 'bigquery://')

__partition_col_converter__ = lambda col: \
    f"PARSE_DATE('%Y-%m', {col}) as {col}" if col in ['data_month', ":data_month"] else f"CAST({col} as DATE)"
__partition_value_converter__ = lambda col, value: \
    datetime.strptime(value, '%Y-%m').date() if col == 'data_month' else datetime.strptime(value, '%Y-%m-%d').date()
__column_sql_type_converter__ = lambda backend_type, col_name, col_type: \
    'DATE' if col_name in ['di', 'dt', 'data_date', 'data_month'] else None
__partition_expr__ = lambda backend_type, partition_col: \
    f'DATE_TRUNC({partition_col}, MONTH)' if backend_type == 'bigqiery' and partition_col == 'data_month' else partition_col
bigquery_sql_expr = SqlExpr(column_sql_type_converter=__column_sql_type_converter__,
                            partition_col_converter=__partition_col_converter__, partition_value_converter=__partition_value_converter__,
                            partition_expr=__partition_expr__)

dt = lambda dt_s: datetime.strptime(dt_s, '%Y-%m-%d %H:%M:%S')

date = lambda s: datetime.strptime(s, '%Y-%m-%d').date()


def dt_zone(dt_s: str, formate='%Y-%m-%d %H:%M:%S', timezone=None):
    if timezone is None:
        return datetime.strptime(dt_s, formate)
    else:
        return datetime.strptime(dt_s, formate).replace(tzinfo=timezone)


next_id = lambda: str(uuid.uuid1()).replace('-', '')


@log_time
def run_sql(sql: str, result_table: str,
            funcs: dict = None, variables: dict = None, dry_run: bool = False,
            spark: SparkSession = None, spark_conf: Dict = None) -> List:
    spark = spark or LocalSpark.get(spark_conf)
    processor = SqlProcessor(spark, sql, [], variables or {})
    processor.func_runner.register_funcs(funcs or {})
    processor.run(dry_run=dry_run)
    return spark.sql(f'select * from {result_table}').collect()
