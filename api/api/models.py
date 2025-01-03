from sqlalchemy import Column, Integer, String, ForeignKey, TIMESTAMP
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.ext.asyncio import AsyncAttrs


class Base(AsyncAttrs, DeclarativeBase):
    pass


class LongUrl(Base):
    __tablename__ = 'long_url'
    long_id = Column(Integer, primary_key=True)
    long_value = Column(String(250), unique=True, nullable=False)


class ShortUrl(Base):
    __tablename__ = 'short_url'
    short_id = Column(Integer, primary_key=True)
    short_value = Column(String(250), nullable=False)


class UrlMapping(Base):
    __tablename__ = 'url_mapping'
    short_id = Column(Integer, ForeignKey('short_url.short_id'), primary_key=True)
    short_url = relationship('ShortUrl', backref='url_mappings')
    long_id = Column(Integer, ForeignKey('long_url.long_id'), nullable=False)
    long_url = relationship('LongUrl', backref='url_mappings')
    expiration = Column(Integer, nullable=False)
    date = Column(TIMESTAMP, nullable=False)


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(20), unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
