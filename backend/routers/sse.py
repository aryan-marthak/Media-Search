"""
Server-Sent Events (SSE) router for real-time updates.
"""
import asyncio
import json
from fastapi import APIRouter, Depends, Request, Query, HTTPException, status
from sse_starlette.sse import EventSourceResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models import User
from auth.jwt import decode_token
from services.events import event_bus, StatusEvent

router = APIRouter()


async def get_user_from_token(token: str, db: AsyncSession) -> User:
    """Validate token and return user (for SSE which can't use headers)."""
    payload = decode_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return user


async def event_generator(user_id: str, request: Request):
    """Generate SSE events for a user."""
    queue = event_bus.subscribe(user_id)
    
    try:
        while True:
            # Check if client disconnected
            if await request.is_disconnected():
                break
            
            try:
                # Wait for event with timeout
                event = await asyncio.wait_for(queue.get(), timeout=30.0)
                
                yield {
                    "event": "status_update",
                    "data": json.dumps({
                        "image_id": event.image_id,
                        "status": event.status,
                        "error": event.error
                    })
                }
            except asyncio.TimeoutError:
                # Send heartbeat to keep connection alive
                yield {"event": "heartbeat", "data": "ping"}
                
    finally:
        event_bus.unsubscribe(user_id, queue)


@router.get("/stream")
async def sse_stream(
    request: Request,
    token: str = Query(..., description="JWT access token"),
    db: AsyncSession = Depends(get_db)
):
    """
    Server-Sent Events endpoint for real-time status updates.
    
    Connect to this endpoint to receive updates when image processing
    status changes, instead of polling individual image statuses.
    
    Note: Token is passed as query parameter since EventSource doesn't
    support custom headers.
    """
    user = await get_user_from_token(token, db)
    
    return EventSourceResponse(
        event_generator(str(user.id), request),
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable nginx buffering if present
            "Access-Control-Allow-Origin": "http://localhost:5173",
            "Access-Control-Allow-Credentials": "true"
        }
    )
