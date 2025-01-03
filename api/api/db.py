from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)
from .models import LongUrl, ShortUrl, UrlMapping, User
from sqlalchemy import select
from datetime import datetime
from .logger import configure_logger
from loguru import logger
from dotenv import load_dotenv
from .auth.auth_handler import get_password_hash
import os


load_dotenv()

configure_logger()


class DataBase:
    def __init__(self) -> None:
        database_url = f"postgresql+asyncpg://{os.environ["DB_USERNAME"]}:{os.environ["DB_PASSWORD"]}@{os.environ["DB_HOST"]}:{os.environ["DB_PORT"]}/{os.environ["DB_NAME"]}"
        self.async_engine = create_async_engine(database_url, echo=True, future=True)
        self.async_session = async_sessionmaker(
            bind=self.async_engine, class_=AsyncSession, expire_on_commit=False
        )

    async def __aenter__(self):
        self.session = self.async_session()
        return self

    async def get_long_url(self, short_value: str) -> None | str:
        try:
            logger.debug(f'Start get_long_url, params: {short_value}')
            result = await self.session.execute(
                select(LongUrl)
                .join(UrlMapping)
                .join(ShortUrl)
                .where(ShortUrl.short_value == short_value)
            )
            long_url = result.scalars().first()

            if long_url is not None:
                return_value = str(long_url.long_value)
                logger.debug(f'long_url is not None, returned: {return_value}')
                return return_value
            logger.debug('long_url is None, returned: None')
        except Exception as e:
            logger.error(f'An error occurred while fetching long URL: {e}')

    async def get_expiration(self, short_value: str) -> None | int:
        try:
            logger.debug(f'Start get_expiration, params: {short_value}')
            result = await self.session.execute(
                select(UrlMapping)
                .join(ShortUrl)
                .where(ShortUrl.short_value == short_value)
            )
            url_mapping = result.scalars().first()

            if url_mapping is not None:
                expiration, date = url_mapping.expiration, url_mapping.date
                create_time = date.hour
                current_time = datetime.now().time().hour
                return_value = max(int((create_time + expiration) - current_time), 0)
                logger.debug(f'expiration is not None, returned: {return_value}')
                return return_value
            logger.debug('expiration is None, returned: None')
        except Exception as e:
            logger.error(f'An error occurred while fetching long URL: {e}')

    async def create_user(self):
        logger.debug(f'Start create user recording to database with params: {self}')
        try:
            pass
        except Exception as e:
            logger.error(f'Error when create user recording to database: {e}')

    async def get_user(self, username: str):
        logger.debug('Start search user to database')
        try:
            result = await self.session.execute(
                select(User).where(User.username == username)
            )
            return result.scalars().first()
        except Exception as e:
            logger.error(f'Error when get user to database: {e}')

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        await self.session.aclose()
