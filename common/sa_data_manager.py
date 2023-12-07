from sqlalchemy import create_engine, Column, String, MetaData, Table
from sqlalchemy import insert, select, update, delete
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.exc import OperationalError
import os
import json
import time

class SADataManager:
    def __init__(self, max_retries=3) -> None:
        self.__engine = create_engine('sqlite:///sa.db')
        self.__session_factory = sessionmaker(bind=self.__engine)
        self.__Session = scoped_session(self.__session_factory)
        self.__table_structures = {}
        self.__max_retries = max_retries

    def execute_command(self, exec_obj):
        retries = 0
        while retries < self.__max_retries:
            try:
                session = self.__Session()
                session.execute(exec_obj)
                session.commit()
                break
            except OperationalError as e:
                session.rollback()
                retries += 1
                time.sleep(0.1)  # A short delay between retries
            finally:
                session.close()
        if retries == self.__max_retries:
            raise Exception(f"Max retries reached for operation {exec_obj}")

    def setup_table(self, table_name: str) -> None:
        metadata = MetaData()
        table = Table(table_name, metadata,
                    Column('key', String(80), primary_key=True),
                    Column('value', String(10000)))
        metadata.create_all(self.__engine)
        self.__table_structures[table_name] = table
    
    def save_data(self, table_name: str, key, value) -> None:
        table = self.__table_structures.get(table_name)
        data = self.get_data(table_name, key)
        exec_obj = None
        if data is not None:
            exec_obj = update(table).values(value = value)\
                                        .where(table.c.key == key)
        else:
            self.setup_table(table_name)
            exec_obj = insert(self.__table_structures[table_name])\
                .values(key = key, value = value)
        
        self.execute_command(exec_obj)
        # TODO: Should the connection be closed?
    
    def add_data(self, table_name: str, key, value) -> None:
        table = self.__table_structures.get(table_name)
        data = self.get_data(table_name, key)
        result = []
        exec_obj = None
        if data is not None:
            result = json.loads(data)
            result.append(value)
            result = json.dumps(result)
            exec_obj = update(table).values(value = result)\
                                        .where(table.c.key == key)
        else:
            self.setup_table(table_name)
            exec_obj = insert(self.__table_structures[table_name])\
                .values(key = key, value = f'[{value}]')
        
        self.execute_command(exec_obj)
        
    
    
    def remove_data(self, table_name: str, key) -> None:
        table = self.__table_structures.get(table_name)
        if table is None:
            return
        delete_obj = delete(table).where(table.c.key == key)
        
        self.execute_command(delete_obj)
    
    def get_data(self, table_name: str, key):
        table = self.__table_structures.get(table_name)
        data = None
        if table is not None:
            connection = self.__engine.connect()
            select_obj = select(table)\
                       .where(table.c.key == key)
            data = connection.execute(select_obj).fetchone()
            connection.close()
        return data
    
    def remove_table(self, table_name: str) -> None:
        table = self.__table_structures[table_name]
        if table is not None:
            table.drop(self.__engine)
            del self.__table_structures[table_name]

