import datetime
from sqlalchemy import BigInteger, String, Boolean, DateTime, Integer, ForeignKey
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from config import DATABASE_URL

# Настраиваем асинхронный движок базы данных
engine = create_async_engine(DATABASE_URL, echo=True)
async_session = async_sessionmaker(engine, expire_on_commit=False)

# Базовый класс для моделей
class Base(DeclarativeBase):
    pass

# Таблица пользователей сервиса (Пункт 45 ТЗ)
class User(Base):
    __tablename__ = "users"
    
    tg_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str | None] = mapped_column(String(32), nullable=True)
    has_access: Mapped[bool] = mapped_column(Boolean, default=False)
    access_until: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    
    total_slots: Mapped[int] = mapped_column(Integer, default=0)
    used_slots: Mapped[int] = mapped_column(Integer, default=0)
    
    # Уровень Анти-отслежки: 'none', 'shield', 'control', 'full_spy' (Пункт 17 ТЗ)
    anti_track_level: Mapped[str] = mapped_column(String(20), default="none")

# Функция для первоначального создания таблиц в PostgreSQL
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
