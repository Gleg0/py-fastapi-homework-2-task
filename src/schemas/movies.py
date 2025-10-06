from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator
from datetime import date, timedelta

from database.models import MovieStatusEnum


class MovieBaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: str = Field(max_length=255)
    date: date
    score: float = Field(ge=0, le=100)
    overview: str

    @field_validator("date")
    @classmethod
    def date_not_too_far(cls, value: date) -> date:
        if value > date.today() + timedelta(days=365):
            raise ValueError("Release date cannot be more than 1 year in the future")
        return value


class MovieResponseSchema(MovieBaseSchema):
    id: int


class MoviesPage(BaseModel):
    movies: List[MovieResponseSchema]
    prev_page: Optional[str]
    next_page: Optional[str]
    total_pages: int
    total_items: int


class MovieCreateSchema(MovieBaseSchema):
    status: MovieStatusEnum
    budget: float = Field(ge=0)
    revenue: float = Field(ge=0)
    country: str = Field(max_length=3)
    genres: List[str] = Field(default_factory=list)
    actors: List[str] = Field(default_factory=list)
    languages: List[str] = Field(default_factory=list)


class CountryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    name: Optional[str]


class GenreResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


class ActorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


class LanguageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


class MovieDetailResponseSchema(MovieResponseSchema):
    model_config = ConfigDict(from_attributes=True)
    status: MovieStatusEnum
    budget: float
    revenue: float
    country: CountryResponse
    genres: List[GenreResponse]
    actors: List[ActorResponse]
    languages: List[LanguageResponse]


class MovieUpdateSchema(BaseModel):
    name: Optional[str] = None
    date: Optional[date] = None
    score: Optional[float] = Field(None, ge=0, le=100)
    overview: Optional[str] = None
    status: Optional[MovieStatusEnum] = None
    budget: Optional[float] = Field(None, ge=0)
    revenue: Optional[float] = Field(None, ge=0)
