# Quick start

## First ETL with Easy SQL

(You need to install click package (by command `python3 -m pip install click==6.7`) before run the commands below.)

### For spark backend

Create a file named `sample_etl.spark.sql` with content as below:

```sql
-- prepare-sql: drop database if exists sample cascade
-- prepare-sql: create database sample
-- prepare-sql: create table sample.test as select 1 as id, '1' as val

-- target=variables
select true as __create_output_table__

-- target=variables
select 1 as a

-- target=log.a
select '${a}' as a

-- target=log.test_log
select 1 as some_log

-- target=check.should_equal
select 1 as actual, 1 as expected

-- target=temp.result
select
    ${a} as id, ${a} + 1 as val
union all
select id, val from sample.test

-- target=output.sample.result
select * from result

-- target=log.sample_result
select * from sample.result
```

Run it with command:

```bash
bash -c "$(python3 -m easy_sql.data_process -f sample_etl.spark.sql -p)"
```

### For postgres backend

You need to start a postgres instance first.

If you have docker, run the command below:

```bash
docker run -d --name postgres -p 5432:5432 -e POSTGRES_PASSWORD=123456 postgres
```

Create a file named `sample_etl.postgres.sql` with content as the test file [here](https://github.com/easysql/easy_sql/blob/main/test/sample_etl.postgres.sql).

Run it with command:

```bash
PG_URL=postgresql://postgres:123456@localhost:5432/postgres python3 -m easy_sql.data_process -f sample_etl.postgres.sql
```

### For clickhouse backend

You need to start a clickhouse instance first.

If you have docker, run the command below:

```bash
docker run -d --name clickhouse -p 9000:9000 yandex/clickhouse-server:20.12.5.18
```

Create a file named `sample_etl.clickhouse.sql` with content as the test file [here](https://github.com/easysql/easy_sql/blob/main/test/sample_etl.clickhouse.sql).

Run it with command:

```bash
CLICKHOUSE_URL=clickhouse+native://default@localhost:9000 python3 -m easy_sql.data_process -f sample_etl.clickhouse.sql
```

### For other backends

The usage is similar, please refer to API.

## Run ETL in your code

Easy SQL can be used as a very light-weight library. If you'd like to run ETL programmatically in your code.
Please refer to the code snippets below:

```python
from pyspark.sql import SparkSession

from easy_sql.sql_processor import SqlProcessor
from easy_sql.sql_processor.backend import SparkBackend

if __name__ == '__main__':
    spark = SparkSession.builder.enableHiveSupport().getOrCreate()
    backend = SparkBackend(spark)
    sql = '''
-- target=log.some_log
select 1 as a
    '''
    sql_processor = SqlProcessor(backend, sql)
    sql_processor.run()
```

More sample code about other backends could be referred [here](https://github.com/easysql/easy_sql/blob/main/test/sample_data_process.py)
