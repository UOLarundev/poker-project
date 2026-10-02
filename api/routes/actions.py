from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from api.db import get_db
from api.schemas import GameOverView, GameView, NextHandRequest, SubmitActionRequest
from api.services import action_service

router = APIRouter(prefix="/api/hands", tags=["actions"])


@router.post("/{hand_id}/actions", response_model=GameView)
def submit_action(
    hand_id: uuid.UUID,
    body: SubmitActionRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> dict:
    try:
        result, is_replay = action_service.submit_action(
            db, hand_id, body.action_id, body.action_type, body.amount
        )
    except action_service.HandNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except (action_service.HandAlreadyOverError, action_service.NotYourTurnError) as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e
    except action_service.IllegalActionError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    if is_replay:
        response.headers["Idempotent-Replay"] = "true"
        response.status_code = status.HTTP_200_OK
    else:
        response.status_code = status.HTTP_201_CREATED
    return result


@router.post("/{hand_id}/next", response_model=GameView | GameOverView)
def next_hand(
    hand_id: uuid.UUID,
    body: NextHandRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> dict:
    try:
        result, is_replay = action_service.start_next_hand(db, hand_id, body.action_id)
    except action_service.HandNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except action_service.HandAlreadyOverError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e

    if is_replay:
        response.headers["Idempotent-Replay"] = "true"
        response.status_code = status.HTTP_200_OK
    else:
        response.status_code = status.HTTP_201_CREATED
    return result
