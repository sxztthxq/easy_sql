from enum import Enum
from typing import Dict, Callable, List, Tuple, Any, Union

__all__ = [
    'Backend', 'Table', 'Row', 'TableMeta', 'Partition', 'SaveMode'
]


class Col:

    def __init__(self, name: str, type: str):
        self.name, self.type = name, type

    def as_dict(self) -> Dict[str, str]:
        return {'name': self.name, 'type': self.type}


class Backend:

    @property
    def is_spark_backend(self):
        return str(self.__class__) == "<class 'easy_sql.sql_processor.backend.spark.SparkBackend'>"

    @property
    def is_postgres_backend(self):
        return str(self.__class__) == "<class 'easy_sql.sql_processor.backend.rdb.RdbBackend'>" \
            and self.is_pg

    @property
    def is_clickhouse_backend(self):
        return str(self.__class__) == "<class 'easy_sql.sql_processor.backend.rdb.RdbBackend'>" \
            and self.is_ch

    @property
    def is_bigquery_backend(self):
        return str(self.__class__) == "<class 'easy_sql.sql_processor.backend.rdb.RdbBackend'>" \
               and self.is_bq

    def reset(self):
        raise NotImplementedError()

    def init_udfs(self, *args, **kwargs):
        raise NotImplementedError()

    def register_udfs(self, funcs: Dict[str, Callable]):
        raise NotImplementedError()

    def create_empty_table(self):
        raise NotImplementedError()

    def exec_native_sql(self, sql: str) -> Any:
        raise NotImplementedError()

    def exec_sql(self, sql: str) -> 'Table':
        raise NotImplementedError()

    def temp_tables(self) -> List[str]:
        raise NotImplementedError()

    def clear_cache(self):
        raise NotImplementedError()

    def clear_temp_tables(self, exclude: List[str] = None):
        raise NotImplementedError()

    def create_temp_table(self, table: 'Table', name: str):
        raise NotImplementedError()

    def create_cache_table(self, table: 'Table', name: str):
        raise NotImplementedError()

    def broadcast_table(self, table: 'Table', name: str):
        raise NotImplementedError()

    def table_exists(self, table: 'TableMeta'):
        pass

    def refresh_table_partitions(self, table: 'TableMeta'):
        raise NotImplementedError()

    def save_table(self, source_table: 'TableMeta', target_table: 'TableMeta', save_mode: 'SaveMode', create_target_table: bool):
        raise NotImplementedError()

    def clean(self):
        raise NotImplementedError()

    def create_table_with_data(self, full_table_name: str, values: List[List[Any]], schema: Union['StructType', List[Col]], partitions: List['Partition']):
        raise NotImplementedError()

    def create_temp_table_with_data(self, table_name: str, values: List[List[Any]], schema: Union['StructType', List[Col]]):
        raise NotImplementedError()


class Partition:
    def __init__(self, field: str, value=None):
        self.field = field
        self.value = value

    def __repr__(self):
        return f"Partition(field={self.field}, value={self.value}"

    def __str__(self):
        return f'{self.field}={self.value}'

    def __eq__(self, other):
        if not isinstance(other, Partition):
            return False
        return self.field == other.field and self.value == other.value

    def __hash__(self):
        return str(self).__hash__()


class SaveMode(Enum):
    overwrite = 0,
    append = 1


class TableMeta:

    def __init__(self, table_name: str, partitions: List[Partition] = None):
        self.table_name = table_name
        self.partitions = partitions or []
        self.dbname, self.pure_table_name = self.__parse_table_name()

    def __repr__(self):
        return f"TableMeta(table_name={self.table_name}" \
               f", partitions={self.partitions}" \
               f", dbname={self.dbname}" \
               f", pure_table_name={self.pure_table_name})"

    def update_partitions(self, partitions: List[Partition]) -> 'TableMeta':
        self.partitions = partitions
        return self

    def clone_with_name(self, table_name: str) -> 'TableMeta':
        return TableMeta(table_name, self.partitions)

    def clone_with_partitions(self, partitions: List[Partition]) -> 'TableMeta':
        return TableMeta(self.table_name, partitions)

    def __parse_table_name(self) -> Tuple[str, str]:
        if self.table_name.find('.') != -1:
            if len(self.table_name.split('.')) != 2:
                raise Exception(f'table_name must be like DB_NAME.TABLE_NAME, found: {self.table_name}')
            dbname = self.table_name[:self.table_name.find('.')]
            pure_table_name = self.table_name[self.table_name.find('.') + 1:]
        else:
            dbname, pure_table_name = None, self.table_name
        return dbname, pure_table_name

    def has_partitions(self):
        return len(self.partitions) > 0

    def has_dynamic_partition(self):
        return any([pt.value is None for pt in self.partitions])

    def get_full_table_name(self, temp_db: str = None):
        return f'{self.dbname or temp_db}.{self.pure_table_name}'


class Table:

    def is_empty(self) -> bool:
        raise NotImplementedError()

    def field_names(self) -> List[str]:
        raise NotImplementedError()

    def first(self) -> 'Row':
        raise NotImplementedError()

    def limit(self, count: int) -> 'Table':
        raise NotImplementedError()

    def with_column(self, name: str, value: any) -> 'Table':
        raise NotImplementedError()

    def collect(self) -> List['Row']:
        raise NotImplementedError()

    def show(self, count: int):
        raise NotImplementedError()

    def count(self) -> int:
        raise NotImplementedError()


class Row:

    def as_dict(self) -> Dict[str, Any]:
        raise NotImplementedError()

    def __str__(self):
        raise NotImplementedError()

    def __getitem__(self, i):
        raise NotImplementedError()

    def as_tuple(self) -> Tuple:
        raise NotImplementedError()
