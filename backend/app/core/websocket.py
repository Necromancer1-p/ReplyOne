import os
import json
import logging
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.core.security import verify_access_token
import redis.asyncio as aioredis

logger = logging.getLogger("replyone.websocket")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Global variables for Redis connection
redis_client = None
redis_online = False

async def init_redis():
    """Attempts to connect to Redis with a short timeout. Sets redis_online accordingly."""
    global redis_client, redis_online
    logger.info("Initializing Redis check...")
    try:
        redis_client = aioredis.from_url(
            REDIS_URL, 
            decode_responses=True,
            socket_connect_timeout=0.5,
            socket_timeout=0.5
        )
        await redis_client.ping()
        redis_online = True
        logger.info("Successfully connected to Redis. Redis Pub/Sub enabled.")
    except Exception as e:
        redis_client = None
        redis_online = False
        logger.warning(f"Redis is unreachable: {e}. Falling back to direct in-memory pubsub.")

class ConnectionManager:
    def __init__(self):
        # Maps tenant_id -> list of WebSocket connections
        self.active_connections: dict[int, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, tenant_id: int):
        await websocket.accept()
        if tenant_id not in self.active_connections:
            self.active_connections[tenant_id] = []
        self.active_connections[tenant_id].append(websocket)
        logger.info(f"WebSocket connected for tenant {tenant_id}. Total connections for tenant: {len(self.active_connections[tenant_id])}")

    def disconnect(self, websocket: WebSocket, tenant_id: int):
        if tenant_id in self.active_connections:
            if websocket in self.active_connections[tenant_id]:
                self.active_connections[tenant_id].remove(websocket)
            if not self.active_connections[tenant_id]:
                del self.active_connections[tenant_id]
        logger.info(f"WebSocket disconnected for tenant {tenant_id}")

    async def broadcast_to_tenant(self, tenant_id: int, event_type: str, data: dict):
        if tenant_id in self.active_connections:
            payload = {
                "type": event_type,
                "data": data
            }
            logger.debug(f"Broadcasting event {event_type} to tenant {tenant_id}")
            
            # Extract customer session from event payload if present for security filtering
            event_session_id = data.get("customer_session_id")
            if not event_session_id and "customer" in data:
                cust_info = data.get("customer")
                if isinstance(cust_info, dict):
                    event_session_id = cust_info.get("external_user_id")

            dead_connections = []
            for connection in self.active_connections[tenant_id]:
                try:
                    client_session_id = getattr(connection, "state_session_id", None)
                    # If this connection is a website customer widget connection
                    if client_session_id is not None:
                        # Only send if the event is meant for this customer session
                        if event_session_id == client_session_id:
                            await connection.send_json(payload)
                    else:
                        # Agent/owner dashboard connection receives all tenant events
                        await connection.send_json(payload)
                except Exception as e:
                    logger.warning(f"Failed to send websocket message: {e}")
                    dead_connections.append(connection)
            
            # Clean up any dead connections we encountered
            for dead in dead_connections:
                self.disconnect(dead, tenant_id)

manager = ConnectionManager()
router = APIRouter()

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket, 
    token: str = Query(None),
    session_id: str = Query(None),
    tenant_id: int = Query(None)
):
    authenticated = False
    resolved_tenant_id = None
    client_label = "unknown"

    if token:
        payload = verify_access_token(token)
        if payload:
            resolved_tenant_id = int(payload.get("tid"))
            client_label = f"agent_{payload.get('sub')}"
            authenticated = True
        else:
            logger.warning("WebSocket connection rejected: invalid or expired JWT token.")
            await websocket.close(code=1008)
            return
    elif session_id and tenant_id:
        # A website widget customer connection identified by session_id and tenant_id
        resolved_tenant_id = int(tenant_id)
        client_label = f"customer_{session_id}"
        authenticated = True
    else:
        logger.warning("WebSocket connection rejected: missing authentication credentials.")
        await websocket.close(code=1008)
        return

    if not authenticated or resolved_tenant_id is None:
        await websocket.close(code=1008)
        return
        
    # Store session details on the socket for individual message filtering
    websocket.state_session_id = session_id 
    
    await manager.connect(websocket, resolved_tenant_id)
    try:
        while True:
            # Keep connection alive, listen for ping/pong or client messages
            data = await websocket.receive_text()
            logger.debug(f"Received message from client {client_label}: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket, resolved_tenant_id)
    except Exception as e:
        logger.error(f"WebSocket error for client {client_label}: {e}", exc_info=True)
        manager.disconnect(websocket, resolved_tenant_id)

async def redis_pubsub_listener():
    """Listens to Redis Pub/Sub and broadcasts events to the appropriate tenant."""
    global redis_online
    if not redis_online or not redis_client:
        logger.warning("Redis is offline. Redis Pub/Sub listener disabled.")
        return
        
    pubsub = redis_client.pubsub()
    channel_name = "replyone:events"
    await pubsub.subscribe(channel_name)
    logger.info(f"Subscribed to Redis channel: {channel_name}")
    
    try:
        async for message in pubsub.listen():
            if message and message["type"] == "message":
                try:
                    payload = json.loads(message["data"])
                    tenant_id = payload.get("tenant_id")
                    event_type = payload.get("type")
                    data = payload.get("data")
                    if tenant_id and event_type:
                        await manager.broadcast_to_tenant(tenant_id, event_type, data)
                except Exception as ex:
                    logger.error(f"Error parsing Redis pubsub message data: {ex}", exc_info=True)
    except asyncio.CancelledError:
        logger.info("Redis pubsub listener task cancelled")
    except Exception as e:
        logger.error(f"Redis pubsub listener error: {e}", exc_info=True)
        if redis_online:
            await asyncio.sleep(5)
            asyncio.create_task(redis_pubsub_listener())

async def publish_websocket_event(tenant_id: int, event_type: str, data: dict):
    """Helper to publish websocket event. Falls back to direct in-memory broadcast if Redis is offline."""
    payload = {
        "tenant_id": tenant_id,
        "type": event_type,
        "data": data
    }
    
    # Try publishing to Redis first if online
    redis_success = False
    if redis_online and redis_client:
        try:
            await redis_client.publish("replyone:events", json.dumps(payload, default=str))
            redis_success = True
            logger.debug(f"Published event {event_type} to Redis channel replyone:events")
        except Exception as e:
            logger.warning(f"Failed to publish websocket event to Redis: {e}. Falling back to in-memory broadcast.")
            
    # Fallback to direct in-memory broadcast (for single-process runs without Redis)
    if not redis_success:
        logger.debug(f"Broadcasting event {event_type} in-memory directly to tenant {tenant_id}")
        await manager.broadcast_to_tenant(tenant_id, event_type, data)
