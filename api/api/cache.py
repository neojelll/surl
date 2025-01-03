from redis.asyncio import Redis
from api.logger import configure_logger
from dotenv import load_dotenv
from loguru import logger
import os


load_dotenv()

configure_logger()


async def ttl() -> int:
    try:
        result = os.environ['CACHE_TTL']
        logger.debug('successfully obtained the value of the environment variable')
        return int(result)
    except Exception as e:
        logger.warning(f'CACHE_TTL environment variable error: {e}')
        return 3600


class Cache:
    def __init__(self) -> None:
        self.cache = Redis(
            host=os.environ['CACHE_HOST'],
            port=int(os.environ['CACHE_PORT']),
            decode_responses=True,
        )

    async def __aenter__(self):
        return self

    async def check(self, short_url) -> None | str:
        try:
            logger.debug(f'Start cache get with: {short_url}')
            return_value = await self.cache.get(short_url)
            logger.debug(f'returned: {return_value}')
            return return_value
        except Exception as e:
            logger.debug(f'Error when get data with cache: {e}')

    async def set(self, short_url, long_url, expiration) -> None:
        try:
            exp = min(await ttl(), expiration)

            logger.debug(f'Start cache set with: {short_url, long_url, exp}')
            await self.cache.set(short_url, long_url, ex=exp)
            logger.debug('Sucsessfully set to cache')
        except Exception as e:
            logger.error(f'Error when set in cache: {e}')

    async def create_recording_with_refresh(self, username, refresh_token):
        logger.debug(
            f'Start create recording with refresh token to cache with params: {username}, {refresh_token}'
        )
        try:
            await self.cache.set(refresh_token, username, ex=3600 * 24 * 7)
            logger.debug('Create recording with refresh token was successful')
        except Exception as e:
            logger.error(
                f'Error when create recording with refresh token to cache: {e}'
            )

    async def check_refresh_token(self, refresh_token):
        logger.debug(f'Start check refresh token in cache with params: {refresh_token}')
        try:
            return_value = await self.cache.get(refresh_token)
            logger.debug(
                f'Check refresh token in cache was successful, return value: {return_value}'
            )
            return return_value
        except Exception as e:
            logger.error(f'Error when check refresh token in cache: {e}')

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        await self.cache.aclose()
