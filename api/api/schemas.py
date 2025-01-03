from pydantic import BaseModel, Field


class ShortURLAuthRequestSchema(BaseModel):
    url: str = Field(...)
    prefix: str = ''
    expiration: int = 24

    class Config:
        json_schema_extra = {
            'example': {
                'url': 'https://shorten.com',
                'prefix': 'shortener',
                'expiration': 48,
            }
        }


class ShortURLRequestSchema(BaseModel):
    url: str = Field(...)
    expiration: int = 24

    class Config:
        json_schema_extra = {
            'example': {
                'url': 'https://shorten.com',
                'expiration': 48,
            }
        }
