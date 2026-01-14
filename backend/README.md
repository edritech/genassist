# GenAssist Backend

## Overview

This is the backend for GenAssist, organized as a modular microservice architecture. The backend is structured to support both current monolith operations and future microservice separation.

## Structure

```
backend/
├── shared/                    # Shared/common code (schemas, cache, config, gateways, etc.)
│   ├── cache/                 # Redis/caching utilities
│   ├── config/                # Configuration utilities
│   ├── exceptions/            # Shared exception types/handlers
│   ├── gateways/              # Service-to-service gateway clients (e.g. core auth)
│   ├── http/                  # Internal HTTP client helpers
│   └── schemas/               # Shared Pydantic models
│
├── services/                  # Microservices
│   ├── core/                  # Core API service
│   │   ├── app/               # Application code (API, modules, services, etc.)
│   │   ├── Dockerfile         # Service Dockerfile
│   │   └── requirements-*.txt # Service dependencies (main/app/rag)
│   ├── gateway/               # API gateway / edge service
│   │   ├── app/               # FastAPI app entrypoint + routing
│   │   ├── Dockerfile         # Service Dockerfile
│   │   └── requirements.txt   # Service dependencies
│   └── websocket/             # WebSocket service
│       ├── app/               # Application code
│       ├── Dockerfile         # Service Dockerfile
│       └── requirements.txt   # Service dependencies
│
├── scripts/                   # Local helper scripts for running services
│   ├── start-core-svc.sh
│   ├── start-gateway.sh
│   └── start-websocket.sh
│
├── infra/                     # Infrastructure as code for backend
│   ├── main.tf
│   └── backend.tf
│
└── docs-site/                 # Backend developer documentation (Docusaurus)
```

## Shared Module

The `shared/` directory contains common code used across multiple services:

- **cache/**: Redis and caching utilities
  - Unified Redis connection manager
  - Pub/Sub support
  - General caching operations

- **config/**: Configuration utilities
  - Base settings classes
  - Application configuration and validation

- **exceptions/**: Shared exception types and helpers
  - Common exception base classes
  - Reusable error utilities

- **gateways/**: Service-to-service gateway clients
  - Core auth gateway for delegating authentication to the core service
  - HTTP-based integration points between services

- **http/**: Internal HTTP client helpers
  - Internal service client abstraction
  - Common configuration for internal requests

- **schemas/**: Shared data models
  - API key and auth-related models
  - User and role models
  - Other cross-service Pydantic schemas

## Services

### Core Service (`services/core/`)

The main API service providing:
- REST API endpoints
- Business logic
- Database operations
- Celery task processing
- Multi-tenant support

### Gateway Service (`services/gateway/`)

The edge/gateway service providing:
- HTTP entrypoint in front of backend services
- Routing and delegation to the core service
- Place to centralize cross-cutting concerns at the edge (auth, logging, etc.)

### WebSocket Service (`services/websocket/`)

Real-time communication service providing:
- WebSocket connections
- Message broadcasting
- Redis Pub/Sub integration
- Multi-tenant support

## Getting Started

### Prerequisites

- Python 3.11+
- PostgreSQL
- Redis
- Docker (optional, for containerized deployment)

### Virtual Environment Activation
```bash
  Mac/Linux:
  python3.12 -m venv genassist_env
  source genassist_env/bin/activate
```

### Installation
1. **Install shared module dependencies**:
```bash
  cd backend/shared
  pip install -r requirements.txt
```

2. **Install core service dependencies**:
```bash
  cd backend/services/core
  pip install -r requirements-main.txt
  pip install -r requirements-app.txt
  pip install -r requirements-rag.txt

```

3. **Install websocket service dependencies**:
```bash
  cd backend/services/websocket
  pip install -r requirements.txt
```

### Running Services

#### Core Service

```bash
cd backend/services/core
python run.py
```

#### WebSocket Service

```bash
cd backend/services/websocket
python -m app.main
```

### Docker Deployment

#### Development

For local development, use `docker-compose.dev.yml`:

```bash
docker-compose -f docker-compose.dev.yml up --build
```

**Note**: The build context for services is set to `backend/` directory to allow access to the `shared/` module. This means:
- Services can access shared code
- Shared module is copied to `/src/shared` in containers
- PYTHONPATH should include `/src` (already handled in Dockerfiles)

#### Production

For production, see `docker-compose.yml` in the root directory. It uses pre-built images from a registry.

**Build Context Configuration**:
```yaml
# docker-compose.dev.yml
app:
  build:
    context: ./backend                    # Context is backend/ directory
    dockerfile: services/core/Dockerfile  # Path relative to context
```

## Using Shared Modules

### Authentication

```python
from shared.auth import socket_auth, SocketAuthConfig
from shared.schemas.socket_principal import SocketPrincipal

# Configure authentication
config = SocketAuthConfig(
    jwt_secret_key="your-secret-key",
    api_key_validator=my_api_key_validator,
    multi_tenant_enabled=True
)

# Use in WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(
    principal: SocketPrincipal = Depends(
        socket_auth(["read:conversations"], config=config)
    )
):
    ...
```

### Redis Manager

```python
from shared.cache.redis_manager import RedisManager

# Initialize Redis manager
redis_manager = RedisManager(
    redis_url="redis://localhost:6379",
    max_connections=20
)
await redis_manager.initialize()

# Use for Pub/Sub
await redis_manager.publish("channel", "message")
pubsub = await redis_manager.psubscribe("pattern:*")

# Use for caching
await redis_manager.set("key", "value", ex=3600)
value = await redis_manager.get("key")
```

### Tenant Management

```python
from shared.tenant.scope import set_tenant_context, get_tenant_context
from shared.tenant.resolver import TenantResolver

# Set tenant context
set_tenant_context("tenant-123")

# Get current tenant
current_tenant = get_tenant_context()  # Returns "tenant-123"

# Resolve tenant from request
resolver = TenantResolver()
tenant_id = resolver.resolve(request=request, auth_payload=payload)
```

### WebSocket Connection Manager

```python
from shared.websocket.connection_manager import SocketConnectionManager, connect_websocket_to_manager

# Initialize connection manager
connection_manager = SocketConnectionManager(
    redis_manager=redis_manager,
    capture_context=True  # For FastAPI/DI environments
)
await connection_manager.initialize_redis_subscriber()

# Connect WebSocket
await connection_manager.connect(
    websocket=websocket,
    room_id="room-123",
    user_id=user_id,
    permissions=["read:conversations"],
    tenant_id="tenant-1"
)

# Broadcast message
await connection_manager.broadcast(
    room_id="room-123",
    msg_type="message",
    current_user_id=user_id,
    payload={"text": "Hello"},
    tenant_id="tenant-1"
)
```

### Exception Handling

```python
from shared.exceptions.socket_errors import send_socket_error, SocketErrorBuilder
from shared.exceptions.handlers import init_error_handlers

# Send WebSocket error
await send_socket_error(
    websocket=websocket,
    error_key="AUTHENTICATION_FAILED",
    message="Invalid credentials",
    error_code=4001
)

# Use error builder
builder = SocketErrorBuilder(websocket)
await builder.with_key("ERROR_KEY").with_message("Error message").send()

# Initialize HTTP exception handlers
init_error_handlers(app, app_exception_handler=handle_app_exception)
```

## Migration Guide

For detailed migration instructions from the old structure to the new shared module structure, see [SHARED_MODULE_MIGRATION.md](SHARED_MODULE_MIGRATION.md).

## Design Principles

1. **No Service-Specific Dependencies**: Shared code should not import from `services/`
2. **Flexible Interfaces**: Support both DI-based and standalone usage patterns
3. **Backward Compatibility**: Maintain existing functionality during migration
4. **Clear Boundaries**: Shared = common utilities, Services = business logic

## Development

### Adding New Shared Utilities

1. Create new module in appropriate `shared/` subdirectory
2. Ensure no dependencies on service-specific code
3. Update `shared/requirements.txt` if new dependencies needed
4. Document usage in this README

### Adding New Services

1. Create new directory in `services/`
2. Create service structure (`app/`, `Dockerfile`, `requirements.txt`)
3. Use shared modules for common functionality
4. Update docker-compose.yml if needed

## Testing

Run tests for each service:

```bash
# Core service tests
cd backend/services/core
pytest

# WebSocket service tests
cd backend/services/websocket
pytest
```

## Future Considerations

- Extract services into separate repositories/packages
- Add message broker (Kafka/RabbitMQ) for inter-service communication
- Database per service when ready for full microservice split
- API Gateway for routing to services
- Service mesh for advanced networking features

## License

[Your License Here]
