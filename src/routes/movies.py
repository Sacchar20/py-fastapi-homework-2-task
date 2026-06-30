import math
from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from pydantic import ValidationError
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from database import get_db, MovieModel
from database.models import CountryModel, GenreModel, ActorModel, LanguageModel
from schemas.movies import (
    MovieDetailSchema,
    MovieListResponseSchema,
)
from schemas import MessageResponseSchema

router = APIRouter()


@router.get("/", response_model=MovieListResponseSchema)
async def get_movies(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
):
    total_query = select(func.count()).select_from(MovieModel)
    total_items_res = await db.execute(total_query)
    total_items = total_items_res.scalar() or 0

    if total_items == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No movies found.",
        )

    total_pages = math.ceil(total_items / per_page)

    if page > total_pages and total_pages > 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No movies found.",
        )

    offset = (page - 1) * per_page
    movies_query = (
        select(MovieModel)
        .order_by(MovieModel.id.desc())
        .offset(offset)
        .limit(per_page)
    )
    movies_res = await db.execute(movies_query)
    movies = movies_res.scalars().all()

    base_url = "/theater/movies/"
    prev_page = (
        f"{base_url}?page={page - 1}&per_page={per_page}"
        if page > 1
        else None
    )
    next_page = (
        f"{base_url}?page={page + 1}&per_page={per_page}"
        if page < total_pages
        else None
    )

    return {
        "movies": movies,
        "prev_page": prev_page,
        "next_page": next_page,
        "total_pages": total_pages,
        "total_items": total_items,
    }


@router.post(
    "/",
    response_model=MovieDetailSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_movie(
    body: dict = Body(...), db: AsyncSession = Depends(get_db)
):
    try:
        name = body.get("name")
        date = body.get("date")
        score = body.get("score")
        overview = body.get("overview")
        status_val = body.get("status")
        budget = body.get("budget")
        revenue = body.get("revenue")
        country = body.get("country")
        genres = body.get("genres", [])
        actors = body.get("actors", [])
        languages = body.get("languages", [])
        if not name or not date or not country:
            raise ValueError
    except (ValidationError, TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid input data.",
        )

    exist_query = select(MovieModel).where(
        MovieModel.name == name,
        MovieModel.date == date,
    )
    exist_res = await db.execute(exist_query)
    if exist_res.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"A movie with the name '{name}' "
                f"and release date '{date}' already exists."
            ),
        )

    country_query = select(CountryModel).where(
        CountryModel.code == country
    )
    country_res = await db.execute(country_query)
    country_obj = country_res.scalar_one_or_none()

    if not country_obj:
        country_obj = CountryModel(code=country, name=None)
        db.add(country_obj)
        await db.flush()

    genre_objects = []
    for g_name in genres:
        g_query = select(GenreModel).where(GenreModel.name == g_name)
        db_res = await db.execute(g_query)
        g_obj = db_res.scalar_one_or_none()
        if not g_obj:
            g_obj = GenreModel(name=g_name)
            db.add(g_obj)
        genre_objects.append(g_obj)

    actor_objects = []
    for a_name in actors:
        a_query = select(ActorModel).where(ActorModel.name == a_name)
        db_res = await db.execute(a_query)
        a_obj = db_res.scalar_one_or_none()
        if not a_obj:
            a_obj = ActorModel(name=a_name)
            db.add(a_obj)
        actor_objects.append(a_obj)

    lang_objects = []
    for l_name in languages:
        l_query = select(LanguageModel).where(LanguageModel.name == l_name)
        db_res = await db.execute(l_query)
        l_obj = db_res.scalar_one_or_none()
        if not l_obj:
            l_obj = LanguageModel(name=l_name)
            db.add(l_obj)
        lang_objects.append(l_obj)

    await db.flush()

    new_movie = MovieModel(
        name=name,
        date=date,
        score=score,
        overview=overview,
        status=status_val,
        budget=budget,
        revenue=revenue,
        country_id=country_obj.id,
        genres=genre_objects,
        actors=actor_objects,
        languages=lang_objects,
    )

    db.add(new_movie)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Movie already exists.",
        )

    await db.refresh(new_movie)
    return new_movie


@router.get(
    "/{movie_id}/", response_model=MovieDetailSchema
)
async def get_movie(
    movie_id: int, db: AsyncSession = Depends(get_db)
):
    query = (
        select(MovieModel)
        .options(
            joinedload(MovieModel.country),
            joinedload(MovieModel.genres),
            joinedload(MovieModel.actors),
            joinedload(MovieModel.languages),
        )
        .where(MovieModel.id == movie_id)
    )
    res = await db.execute(query)
    movie = res.scalar_one_or_none()

    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie with the given ID was not found.",
        )
    return movie


@router.delete(
    "/{movie_id}/", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_movie(
    movie_id: int, db: AsyncSession = Depends(get_db)
):
    query = select(MovieModel).where(MovieModel.id == movie_id)
    res = await db.execute(query)
    movie = res.scalar_one_or_none()

    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie with the given ID was not found.",
        )

    await db.delete(movie)
    await db.commit()


@router.patch("/{movie_id}/", response_model=MessageResponseSchema)
async def update_movie(
    movie_id: int,
    body: dict = Body(...),
    db: AsyncSession = Depends(get_db),
):
    if not isinstance(body, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid input data.",
        )

    query = select(MovieModel).where(MovieModel.id == movie_id)
    res = await db.execute(query)
    movie = res.scalar_one_or_none()

    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie with the given ID was not found.",
        )

    for key, value in body.items():
        if hasattr(movie, key):
            setattr(movie, key, value)

    await db.commit()
    return {"message": "Movie updated successfully."}
