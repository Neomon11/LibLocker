"""
База данных для LibLocker Server
SQLAlchemy модели
"""
import os
from contextlib import contextmanager
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
import enum

Base = declarative_base()


class ClientStatusEnum(enum.Enum):
    """Статус клиента"""
    OFFLINE = "offline"
    ONLINE = "online"
    IN_SESSION = "in_session"
    BLOCKED = "blocked"


class SessionStatusEnum(enum.Enum):
    """Статус сессии"""
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ClientModel(Base):
    """Модель клиента в БД"""
    __tablename__ = 'clients'

    id = Column(Integer, primary_key=True, autoincrement=True)
    hwid = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    ip_address = Column(String(45))
    mac_address = Column(String(17))
    status = Column(String(20), default='offline')
    last_seen = Column(DateTime, default=datetime.now)
    created_at = Column(DateTime, default=datetime.now)

    # Связи
    sessions = relationship("SessionModel", back_populates="client", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Client(id={self.id}, name='{self.name}', hwid='{self.hwid}')>"


class SessionModel(Base):
    """Модель сессии в БД"""
    __tablename__ = 'sessions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    client_id = Column(Integer, ForeignKey('clients.id'), nullable=False)
    start_time = Column(DateTime, default=datetime.now, nullable=False)
    end_time = Column(DateTime)
    duration_minutes = Column(Integer, default=0)  # Запланированная длительность
    actual_duration = Column(Integer)  # Фактическая длительность в минутах
    is_unlimited = Column(Boolean, default=False)
    cost = Column(Float, default=0.0)
    cost_per_hour = Column(Float, default=0.0)  # Стоимость руб./час
    free_mode = Column(Boolean, default=True)  # Бесплатный режим
    status = Column(String(20), default='active')

    # Связи
    client = relationship("ClientModel", back_populates="sessions")

    def __repr__(self):
        return f"<Session(id={self.id}, client_id={self.client_id}, status='{self.status}')>"


class SettingsModel(Base):
    """Модель настроек сервера"""
    __tablename__ = 'settings'

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(String(500))
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def __repr__(self):
        return f"<Settings(key='{self.key}', value='{self.value}')>"


class Database:
    """Класс для работы с базой данных"""

    def __init__(self, db_path: str = "data/liblocker.db"):
        """Инициализация БД"""
        # Если путь относительный, преобразуем в абсолютный
        if not os.path.isabs(db_path):
            from .utils import get_data_directory
            # Получаем только имя файла, игнорируя 'data/' в начале
            db_filename = os.path.basename(db_path)
            data_dir = get_data_directory()
            db_path = os.path.join(data_dir, db_filename)
        else:
            # Для абсолютных путей создаем родительскую директорию, если не существует
            parent_dir = os.path.dirname(db_path)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)
        
        self.engine = create_engine(f'sqlite:///{db_path}', echo=False)
        Base.metadata.create_all(self.engine)
        self._migrate_database()
        self.Session = sessionmaker(bind=self.engine)

    def _migrate_database(self):
        """Применить миграции к существующей базе данных"""
        from sqlalchemy import inspect, text
        
        inspector = inspect(self.engine)
        
        # Проверяем таблицу sessions
        if 'sessions' in inspector.get_table_names():
            columns = {col['name'] for col in inspector.get_columns('sessions')}
            
            # Добавляем отсутствующие колонки в одной транзакции
            with self.engine.connect() as conn:
                if 'cost_per_hour' not in columns:
                    conn.execute(text('ALTER TABLE sessions ADD COLUMN cost_per_hour FLOAT DEFAULT 0.0'))
                
                if 'free_mode' not in columns:
                    conn.execute(text('ALTER TABLE sessions ADD COLUMN free_mode BOOLEAN DEFAULT 1'))
                
                conn.commit()
    
    def get_session(self) -> Session:
        """Получить сессию БД"""
        return self.Session()
    
    @contextmanager
    def session_scope(self):
        """
        Контекстный менеджер для автоматического управления сессией БД.
        
        Автоматически выполняет commit при успешном завершении блока кода
        и rollback в случае исключения. Всегда закрывает сессию после использования.
        
        Использование:
            with db.session_scope() as session:
                client = session.query(ClientModel).first()
                client.name = "New Name"
                # commit выполнится автоматически
        
        Yields:
            Session: Объект сессии SQLAlchemy
        """
        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception:
            # Откатываем изменения при любых ошибках
            session.rollback()
            raise
        finally:
            session.close()

    def close(self) -> None:
        """Закрыть соединение"""
        self.engine.dispose()

