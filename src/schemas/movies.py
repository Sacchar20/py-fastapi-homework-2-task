import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class MovieStatusEnum(str, Enum):
    RELEASED = "Released"
    POST_PRODUCTION = "Post Production"
    IN_PRODUCTION = "In Production"


class CountryResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str = Field(..., max_length=3)
    name: Optional[str] = None


class GenreResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str = Field(..., max_length=255)


class ActorResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str = Field(..., max_length=255)


class LanguageResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str = Field(..., max_length=255)


class MovieCreate(BaseModel):
    name: str = Field(..., max_length=255)
    date: datetime.date
    score: float = Field(..., ge=0, le=100)
    overview: str
    status: MovieStatusEnum
    budget: float = Field(..., ge=0)
    revenue: float = Field(..., ge=0)
    country: str = Field(..., max_length=3, description="ISO code")
    genres: List[str]
    actors: List[str]
    languages: List[str]

    @field_validator("date")
    @classmethod
    def validate_date(cls, v: datetime.date) -> datetime.date:
        max_date = (
            datetime.date.today() + datetime.timedelta(days=365)
        )
        if v > max_date:
            raise ValueError(
                "The date must not be more than one year in the future."
            )
        return v


class MoviePatch(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    date: Optional[datetime.date] = None
    score: Optional[float] = Field(None, ge=0, le=100)
    overview: Optional[str] = None
    status: Optional[MovieStatusEnum] = None
    budget: Optional[float] = Field(None, ge=0)
    revenue: Optional[float] = Field(None, ge=0)


class MovieShortResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    date: datetime.date
    score: float
    overview: str


class MovieListResponseSchema(BaseModel):
    movies: List[MovieShortResponseSchema]
    prev_page: Optional[str] = None
    next_page: Optional[str] = None
    total_pages: int
    total_items: int


class MovieDetailResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    date: datetime.date
    score: float
    overview: str
    status: MovieStatusEnum
    budget: float
    revenue: float
    country: CountryResponseSchema
    genres: List[GenreResponseSchema]
    actors: List[ActorResponseSchema]
    languages: List[LanguageResponseSchema]
