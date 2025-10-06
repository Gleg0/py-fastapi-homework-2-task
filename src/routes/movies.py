from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi_pagination.ext.sqlalchemy import apaginate
from fastapi_pagination import Params
from sqlalchemy.orm import joinedload

from database import get_db, MovieModel
from database.models import CountryModel, GenreModel, ActorModel, LanguageModel
from schemas.movies import MoviesPage, MovieResponseSchema, MovieCreateSchema, MovieDetailResponseSchema, \
    MovieUpdateSchema

router = APIRouter(prefix="/movies", tags=["Movies"])


@router.get("/", response_model=MoviesPage)
async def get_movies(
        db: AsyncSession = Depends(get_db),
        page: int = Query(1, ge=1),
        per_page: int = Query(10, ge=1, le=20)
):
    params = Params(page=page, size=per_page)
    stmt = select(MovieModel).order_by(MovieModel.id.desc())
    page = await apaginate(db, stmt, params)

    if page.total == 0 or not page.items:
        raise HTTPException(status_code=404, detail="No movies found.")

    return {
        "movies": page.items,
        "prev_page": f"/theater/movies/?page={page.page - 1}&per_page={page.size}" if page.page > 1 else None,
        "next_page": f"/theater/movies/?page={page.page + 1}&per_page={page.size}" if page.page < page.pages else None,
        "total_pages": page.pages,
        "total_items": page.total,
    }


@router.post("/", response_model=MovieResponseSchema, status_code=201)
async def create_movie(
        movie: MovieCreateSchema,
        db: AsyncSession = Depends(get_db)
):
    stmt = select(MovieModel).where(MovieModel.name == movie.name, MovieModel.date == movie.date)
    result = await db.execute(stmt)
    existing_movie = result.scalar_one_or_none()
    if existing_movie:
        raise HTTPException(
            status_code=409,
            detail=f"A movie with the name '{movie.name}' and release date '{movie.date}' already exists."
        )

    country_stmt = select(CountryModel).where(CountryModel.code == movie.country)
    result = await db.execute(country_stmt)
    country_obj = result.scalar_one_or_none()
    if not country_obj:
        country_obj = CountryModel(code=movie.country)
        db.add(country_obj)
        await db.flush()

    genre_objs = []
    for genre_name in movie.genres:
        stmt = select(GenreModel).where(GenreModel.name == genre_name)
        result = await db.execute(stmt)
        genre = result.scalar_one_or_none()
        if not genre:
            genre = GenreModel(name=genre_name)
            db.add(genre)
            await db.flush()
        genre_objs.append(genre)

    actor_objs = []
    for actor_name in movie.actors:
        stmt = select(ActorModel).where(ActorModel.name == actor_name)
        result = await db.execute(stmt)
        actor = result.scalar_one_or_none()
        if not actor:
            actor = ActorModel(name=actor_name)
            db.add(actor)
            await db.flush()
        actor_objs.append(actor)

    language_objs = []
    for lang_name in movie.languages:
        stmt = select(LanguageModel).where(LanguageModel.name == lang_name)
        result = await db.execute(stmt)
        lang = result.scalar_one_or_none()
        if not lang:
            lang = LanguageModel(name=lang_name)
            db.add(lang)
            await db.flush()
        language_objs.append(lang)

    new_movie = MovieModel(
        name=movie.name,
        date=movie.date,
        score=movie.score,
        overview=movie.overview,
        status=movie.status.value if hasattr(movie.status, "value") else movie.status,
        budget=movie.budget,
        revenue=movie.revenue,
        country_id=country_obj.id,
        genres=genre_objs,
        actors=actor_objs,
        languages=language_objs
    )

    db.add(new_movie)
    await db.commit()
    await db.refresh(new_movie)

    return new_movie


@router.get("/{movie_id}/", response_model=MovieDetailResponseSchema)
async def get_movie(
        movie_id: int,
        db: AsyncSession = Depends(get_db)
):
    stmt = (
        select(MovieModel)
        .options(
            joinedload(MovieModel.country),
            joinedload(MovieModel.genres),
            joinedload(MovieModel.actors),
            joinedload(MovieModel.languages),
        )
        .where(MovieModel.id == movie_id)
    )
    result = await db.execute(stmt)
    movie = result.scalars().first()

    if not movie:
        raise HTTPException(status_code=404, detail="Movie with the given ID was not found.")

    return MovieDetailResponseSchema.model_validate(movie)


@router.delete("/{movie_id}/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_movie(movie_id: int, db: AsyncSession = Depends(get_db)):
    stmt = select(MovieModel).where(MovieModel.id == movie_id)
    result = await db.execute(stmt)
    movie = result.scalar_one_or_none()

    if not movie:
        raise HTTPException(status_code=404, detail="Movie with the given ID was not found.")

    await db.delete(movie)
    await db.commit()


@router.patch("/{movie_id}/", status_code=status.HTTP_200_OK)
async def update_movie(movie_id: int, update_data: MovieUpdateSchema, db: AsyncSession = Depends(get_db)):
    stmt = select(MovieModel).where(MovieModel.id == movie_id)
    result = await db.execute(stmt)
    movie = result.scalar_one_or_none()

    if not movie:
        raise HTTPException(status_code=404, detail="Movie with the given ID was not found.")

    try:
        for field, value in update_data.model_dump(exclude_unset=True).items():
            setattr(movie, field, value)

        await db.commit()
        await db.refresh(movie)
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Invalid input data.")

    return {"detail": "Movie updated successfully."}
