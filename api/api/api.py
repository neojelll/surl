from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2AuthorizationCodeBearer
from loguru import logger
import httpx
import os
import uuid
from urllib.parse import urlparse

from .cache import Cache
from .db import DataBase
from .logger import configure_logger
from .message_broker import BrokerConsumer, BrokerProducer
from .schemas import ShortURLRequestSchema, ShortURLAuthRequestSchema


configure_logger()


load_dotenv()


CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
REDIRECT_URL = os.getenv('REDIRECT_URL')


async def is_valid_url(url: str) -> bool:
    logger.debug(f'Start is_valid_url with params: {repr(url)}')
    parsed_url = urlparse(url)
    return_value = bool(parsed_url.netloc)
    logger.debug(f'Completed is_valid_url return value: {repr(return_value)}')
    return return_value


app = FastAPI(title='SURL API')


oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl=f'https://oauth.yandex.ru/authorize',
    tokenUrl='https://oauth.yandex.ru/token',
)


@app.get('/login', tags=['auth'])
async def login():
    authorization_url = f'https://oauth.yandex.ru/authorize?response_type=code&client_id={CLIENT_ID}&redirect_url={REDIRECT_URL}'
    return RedirectResponse(url=authorization_url)


@app.get('/auth/callback', tags=['auth'])
async def auth_callback(code: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            'https://oauth.yandex.ru/token',
            data={
                'code': code,
                'client_id': CLIENT_ID,
                'client_secret': CLIENT_SECRET,
                'grant_type': 'authorization_code',
                'redirect_url': REDIRECT_URL,
            },
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
        )
        response_data = response.json()
        return response_data


@app.get('/auth/refresh', tags=['auth'])
async def refresh_access_token(refresh_token: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            'https://oauth.yandex.ru/token',
            data={
                'grant_type': 'refresh_token',
                'client_id': CLIENT_ID,
                'client_secret': CLIENT_SECRET,
                'refresh_token': refresh_token,
            },
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
        )
        response_data = response.json()
        if response.status_code != 200 or 'access_token' not in response_data:
            logger.error(
                'Failed to refresh access token', extra={'response': response_data}
            )
            raise HTTPException(
                status_code=response.status_code,
                detail='Failed to refresh access token',
            )
        access_token = response_data['access_token']
        new_refresh_token = response_data.get('refresh_token')
        return_value = {
            'access-token': access_token,
            'refresh-token': new_refresh_token,
        }
        return return_value
    

@app.post('/v1/url/shorten', tags=['shortener'])
async def send_data_not_auth(data: ShortURLRequestSchema):
    logger.debug(f'Start send_data_not_auth with params: {repr(data)}')
    long_url = data.url
    if not await is_valid_url(long_url):
        logger.error('Error send_data_not_auth: Invalid URL')


@app.post('/auth/v1/url/shorten', tags=['shortener'])
async def send_data_auth(
    data: ShortURLAuthRequestSchema, token: str = Depends(oauth2_scheme)
) -> dict[str, str]:
    logger.debug(f'Start send_data_auth with params: {repr(data)}')
    long_url = data.url
    if not await is_valid_url(long_url):
        logger.error('Error send_data: Invalid URL')
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail='Invalid URL'
        )
    task_num = uuid.uuid5(uuid.NAMESPACE_DNS, urlparse(long_url).netloc)
    task = {'task': str(task_num)}
    data_dict: dict = data.model_dump()
    data_dict.update(task)
    logger.debug(f'data_dict: {data_dict}')
    async with BrokerProducer() as broker:
        await broker.send_data(data_dict)
    logger.debug(f'Completed send_data, returned: {repr(task)}')
    return task


@app.get('/v1/url/shorten', tags=['shortener'])
async def get_short_url(task_num: str) -> dict[str, str]:
    logger.debug(f'Start get_short_url, params: {task_num}')
    async with BrokerConsumer() as broker:
        short_url = await broker.consume_data(task_num)
        if short_url is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail='URL is not found'
            )
    return_value = {'short_url': f'{short_url}'}
    logger.debug(f'Completed get_short_url, returned: {repr(return_value)}')
    return return_value


@app.get('/{short_url}', tags=['shortener'])
async def redirect_request(short_url: str) -> RedirectResponse:
    logger.debug(f'Start redirect_request, params: {repr(short_url)}')
    async with Cache() as cache:
        check = await cache.check(short_url)
        if check is not None:
            long_url = check
        else:
            async with DataBase() as database:
                long_url = await database.get_long_url(short_url)
                expiration = await database.get_expiration(short_url)
            if long_url is None or expiration is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail='URL is not valid'
                )
            await cache.set(short_url, long_url, expiration)
    logger.debug(f'Completed redirect_request, returned: Redirect to {repr(long_url)}')
    return RedirectResponse(url=long_url, status_code=status.HTTP_302_FOUND)
