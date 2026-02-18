# DecisionVault Backend - L3 Architecture (Implementation Specifications)

## Document Purpose

This document provides granular implementation-level details including class diagrams, method signatures, data structures, algorithms, and code-level specifications for the DecisionVault backend system.

---

## Table of Contents

1. [Core Module Implementation](#1-core-module-implementation)
2. [API Module Implementation](#2-api-module-implementation)
3. [Ingestion Module Implementation](#3-ingestion-module-implementation)
4. [Verification Module Implementation](#4-verification-module-implementation)
5. [Workers Module Implementation](#5-workers-module-implementation)
6. [Database Schema Specifications](#6-database-schema-specifications)
7. [API Contract Specifications](#7-api-contract-specifications)
8. [Message Queue Specifications](#8-message-queue-specifications)
9. [Cache Implementation Details](#9-cache-implementation-details)
10. [Error Handling Specifications](#10-error-handling-specifications)
11. [Testing Strategy](#11-testing-strategy)
12. [Performance Considerations](#12-performance-considerations)

---

## 1. Core Module Implementation

### 1.1 Settings Module - Detailed Configuration

#### 1.1.1 Base Directory Resolution

```python
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
# Resolves to: /path/to/decisionvault/backend
```

#### 1.1.2 Security Settings

```python
# WARNING: Replace in production
SECRET_KEY = "django-insecure-%mt%33hfjg=x4_&ft@-lw2!infzg0(6r5dd47^kls2=a8c@^8%"

DEBUG = True  # Set to False in production

ALLOWED_HOSTS = []  # Configure: ['api.decisionvault.com', 'localhost']
```

#### 1.1.3 Installed Apps (Current State)

```python
INSTALLED_APPS = [
    # Django Contrib
    "django.contrib.admin",           # Admin interface
    "django.contrib.auth",            # Authentication system
    "django.contrib.contenttypes",    # Content type framework
    "django.contrib.sessions",        # Session management
    "django.contrib.messages",        # Messaging framework
    "django.contrib.staticfiles",     # Static file management
    
    # Local Apps (TO BE ADDED)
    # "api",
    # "ingestion",
    # "verification",
    # "workers",
    
    # Third-party (TO BE ADDED)
    # "rest_framework",
]
```

#### 1.1.4 Middleware Execution Order

```python
MIDDLEWARE = [
    # Security layer
    "django.middleware.security.SecurityMiddleware",
    
    # Session management
    "django.contrib.sessions.middleware.SessionMiddleware",
    
    # HTTP utilities
    "django.middleware.common.CommonMiddleware",
    
    # CSRF protection
    "django.middleware.csrf.CsrfViewMiddleware",
    
    # Authentication
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    
    # User messages
    "django.contrib.messages.middleware.MessageMiddleware",
    
    # UI security
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
```

**Middleware Request/Response Flow:**

```
REQUEST PHASE (top → bottom):
┌─────────────────────────────────────────────────┐
│ 1. SecurityMiddleware                           │
│    - Sets X-Content-Type-Options: nosniff       │
│    - Sets X-XSS-Protection: 1; mode=block       │
│    - Redirects HTTP → HTTPS (if SSL enabled)    │
└────────────────────┬────────────────────────────┘
                     ▼
┌─────────────────────────────────────────────────┐
│ 2. SessionMiddleware                            │
│    - Loads session from cache/DB                │
│    - Attaches request.session                   │
└────────────────────┬────────────────────────────┘
                     ▼
┌─────────────────────────────────────────────────┐
│ 3. CommonMiddleware                             │
│    - Sets ETag headers                          │
│    - Handles Conditional GET                    │
│    - Manages Content-Type                       │
└────────────────────┬────────────────────────────┘
                     ▼
┌─────────────────────────────────────────────────┐
│ 4. CsrfViewMiddleware                           │
│    - Validates CSRF token on unsafe methods     │
│    - Sets csrf_token cookie                     │
└────────────────────┬────────────────────────────┘
                     ▼
┌─────────────────────────────────────────────────┐
│ 5. AuthenticationMiddleware                     │
│    - Loads user from session                    │
│    - Attaches request.user                      │
└────────────────────┬────────────────────────────┘
                     ▼
┌─────────────────────────────────────────────────┐
│ 6. MessageMiddleware                            │
│    - Manages flash messages                     │
│    - Attaches request.messages                  │
└────────────────────┬────────────────────────────┘
                     ▼
┌─────────────────────────────────────────────────┐
│ 7. XFrameOptionsMiddleware                      │
│    - Sets X-Frame-Options: DENY                 │
└────────────────────┬────────────────────────────┘
                     ▼
              VIEW HANDLER
                     │
RESPONSE PHASE (bottom → top):
                     ▼
┌─────────────────────────────────────────────────┐
│ Response processing (reverse order)             │
└─────────────────────────────────────────────────┘
```

### 1.2 RabbitMQ Client - Implementation Details

#### 1.2.1 Class Implementation

```python
# core/rabbitmq.py
import pika
import json
from typing import Dict, Any


class RabbitMQClient:
    """
    Synchronous RabbitMQ client for publishing messages.
    
    Thread Safety: NOT thread-safe. Create separate instances per thread.
    Connection Type: Blocking (synchronous)
    """
    
    QUEUE_NAME = "decision_tasks"
    DELIVERY_MODE = 2  # Persistent
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 5672,
        virtual_host: str = "/",
        credentials: Optional[pika.PlainCredentials] = None
    ):
        """
        Initialize RabbitMQ connection.
        
        Args:
            host: RabbitMQ server hostname
            port: RabbitMQ server port
            virtual_host: Virtual host path
            credentials: Optional authentication credentials
        """
        self._connection: Optional[pika.BlockingConnection] = None
        self._channel: Optional[pika.channel.Channel] = None
        
        # Build connection parameters
        self._params = pika.ConnectionParameters(
            host=host,
            port=port,
            virtual_host=virtual_host,
            credentials=credentials,
            heartbeat=600,
            blocked_connection_timeout=300,
        )
        
        # Establish connection
        self._connect()
        self._declare_queue()
    
    def _connect(self) -> None:
        """Establish blocking connection to RabbitMQ."""
        self._connection = pika.BlockingConnection(self._params)
        self._channel = self._connection.channel()
        
        # Enable publisher confirms for reliability
        self._channel.confirm_delivery()
    
    def _declare_queue(self) -> None:
        """Declare durable queue."""
        self._channel.queue_declare(
            queue=self.QUEUE_NAME,
            durable=True,
            arguments={
                'x-message-ttl': 86400000,  # 24 hours in milliseconds
                'x-max-length': 10000,       # Max queue size
            }
        )
    
    def publish(self, data: Dict[str, Any]) -> bool:
        """
        Publish message to decision_tasks queue.
        
        Args:
            data: Message payload (will be JSON serialized)
            
        Returns:
            True if message was confirmed by broker
            
        Raises:
            pika.exceptions.UnroutableError: If message cannot be routed
            pika.exceptions.AMQPConnectionError: If connection fails
        """
        if self._connection is None or self._connection.is_closed:
            self._connect()
            self._declare_queue()
        
        body = json.dumps(data, default=str)
        
        properties = pika.BasicProperties(
            content_type='application/json',
            delivery_mode=self.DELIVERY_MODE,
            timestamp=int(time.time()),
        )
        
        try:
            return self._channel.basic_publish(
                exchange='',
                routing_key=self.QUEUE_NAME,
                body=body,
                properties=properties,
                mandatory=True,
            )
        except pika.exceptions.UnroutableError:
            logger.error(f"Message unroutable: {data}")
            raise
    
    def close(self) -> None:
        """Gracefully close connection."""
        if self._channel and not self._channel.is_closed:
            self._channel.close()
        if self._connection and not self._connection.is_closed:
            self._connection.close()
    
    def __enter__(self) -> 'RabbitMQClient':
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit with cleanup."""
        self.close()
```

#### 1.2.2 Usage Example

```python
# Using context manager (recommended)
with RabbitMQClient() as mq:
    mq.publish({
        "task_id": "uuid-123",
        "task_type": "decision.process",
        "payload": {"decision_id": 42},
        "timestamp": "2026-02-18T10:30:00Z"
    })

# Manual lifecycle management
mq = RabbitMQClient()
try:
    mq.publish({"type": "test", "message": "Hello"})
finally:
    mq.close()
```

### 1.3 URL Configuration - Implementation

#### 1.3.1 Current URLs

```python
# core/urls.py
from django.contrib import admin
from django.urls import path

urlpatterns = [
    path('admin/', admin.site.urls),
]
```

#### 1.3.2 Proposed URL Structure

```python
# core/urls.py (PROPOSED)
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    
    # API v1
    path('api/v1/', include('api.urls', namespace='api-v1')),
    
    # Ingestion
    path('api/v1/ingestion/', include('ingestion.urls', namespace='ingestion')),
    
    # Verification
    path('api/v1/verification/', include('verification.urls', namespace='verification')),
    
    # Workers
    path('api/v1/workers/', include('workers.urls', namespace='workers')),
]

# Debug mode static/media serving
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

### 1.4 WSGI Application

```python
# core/wsgi.py
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

application = get_wsgi_application()
```

**Gunicorn Configuration:**

```python
# gunicorn.conf.py
bind = "0.0.0.0:8000"
workers = 3  # Formula: (2 x CPU cores) + 1
timeout = 120  # seconds
keepalive = 5  # seconds

# Logging
accesslog = "-"  # stdout
errorlog = "-"   # stdout
loglevel = "info"

# Process naming
proc_name = "decisionvault"

# Disable control socket
control_socket = None
```

### 1.5 ASGI Application

```python
# core/asgi.py
import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

application = get_asgi_application()
```

---

## 2. API Module Implementation

### 2.1 Models (To Implement)

```python
# api/models.py
from django.db import models
from django.utils import timezone
from typing import Optional


class DecisionStatus(models.TextChoices):
    """Decision lifecycle states."""
    PENDING = 'pending', 'Pending'
    PROCESSING = 'processing', 'Processing'
    COMPLETED = 'completed', 'Completed'
    FAILED = 'failed', 'Failed'
    CANCELLED = 'cancelled', 'Cancelled'


class Decision(models.Model):
    """
    Core decision entity.
    
    Represents a decision request with input parameters,
    processing status, and output results.
    """
    
    id = models.UUIDField(primary_key=True, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    # Input data
    input_data = models.JSONField(default=dict)
    
    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=DecisionStatus.choices,
        default=DecisionStatus.PENDING
    )
    
    # Output data
    result = models.JSONField(null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        db_table = 'api_decision'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self) -> str:
        return f"Decision {self.id} - {self.status}"
    
    def mark_completed(self, result: dict) -> None:
        """Mark decision as completed with result."""
        self.status = DecisionStatus.COMPLETED
        self.result = result
        self.processed_at = timezone.now()
        self.save(update_fields=['status', 'result', 'processed_at', 'updated_at'])
    
    def mark_failed(self, error: str) -> None:
        """Mark decision as failed with error message."""
        self.status = DecisionStatus.FAILED
        self.error_message = error
        self.processed_at = timezone.now()
        self.save(update_fields=['status', 'error_message', 'processed_at', 'updated_at'])
```

### 2.2 Serializers (To Implement)

```python
# api/serializers.py
from rest_framework import serializers
from .models import Decision, DecisionStatus


class DecisionSerializer(serializers.ModelSerializer):
    """Serializer for Decision model."""
    
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    
    class Meta:
        model = Decision
        fields = [
            'id',
            'name',
            'description',
            'input_data',
            'status',
            'status_display',
            'result',
            'error_message',
            'created_at',
            'updated_at',
            'processed_at',
            'metadata',
        ]
        read_only_fields = [
            'id',
            'status',
            'result',
            'error_message',
            'created_at',
            'updated_at',
            'processed_at',
        ]


class DecisionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating decisions."""
    
    class Meta:
        model = Decision
        fields = ['name', 'description', 'input_data', 'metadata']
```

### 2.3 Views (To Implement)

```python
# api/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.core.cache import cache

from .models import Decision
from .serializers import DecisionSerializer, DecisionCreateSerializer
from core.rabbitmq import RabbitMQClient


class DecisionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing decisions.
    
    list:
        Return a list of all decisions.
    
    retrieve:
        Return a specific decision by ID.
    
    create:
        Create a new decision and queue for processing.
    
    update:
        Update an existing decision.
    
    destroy:
        Delete a decision.
    """
    
    queryset = Decision.objects.all()
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return DecisionCreateSerializer
        return DecisionSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Create decision
        decision = serializer.save()
        
        # Queue for processing
        with RabbitMQClient() as mq:
            mq.publish({
                "task_id": str(decision.id),
                "task_type": "decision.process",
                "payload": {
                    "decision_id": str(decision.id),
                    "input_data": decision.input_data,
                },
            })
        
        headers = self.get_success_headers(serializer.data)
        return Response(
            DecisionSerializer(decision).data,
            status=status.HTTP_201_CREATED,
            headers=headers
        )
    
    @action(detail=True, methods=['get'])
    def result(self, request, pk=None):
        """Get decision result with caching."""
        decision = self.get_object()
        
        # Check cache
        cache_key = f"decision_result:{decision.id}"
        cached_result = cache.get(cache_key)
        
        if cached_result:
            return Response({
                "data": cached_result,
                "cached": True
            })
        
        if decision.status != DecisionStatus.COMPLETED:
            return Response({
                "error": "Decision not yet completed",
                "status": decision.status
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Cache for 5 minutes
        cache.set(cache_key, decision.result, timeout=300)
        
        return Response({
            "data": decision.result,
            "cached": False
        })
```

---

## 3. Ingestion Module Implementation

### 3.1 Models (To Implement)

```python
# ingestion/models.py
from django.db import models


class IngestionSource(models.TextChoices):
    """Supported ingestion sources."""
    API = 'api', 'API Upload'
    FILE = 'file', 'File Upload'
    WEBHOOK = 'webhook', 'Webhook'
    SCHEDULED = 'scheduled', 'Scheduled Import'


class IngestionStatus(models.TextChoices):
    """Ingestion job states."""
    PENDING = 'pending', 'Pending'
    VALIDATING = 'validating', 'Validating'
    PROCESSING = 'processing', 'Processing'
    COMPLETED = 'completed', 'Completed'
    FAILED = 'failed', 'Failed'


class IngestionJob(models.Model):
    """
    Tracks data ingestion jobs.
    """
    
    id = models.UUIDField(primary_key=True, editable=False)
    source = models.CharField(
        max_length=20,
        choices=IngestionSource.choices
    )
    status = models.CharField(
        max_length=20,
        choices=IngestionStatus.choices,
        default=IngestionStatus.PENDING
    )
    
    # Raw payload
    raw_data = models.JSONField()
    
    # Validation
    validation_errors = models.JSONField(default=list, blank=True)
    
    # Processing
    records_processed = models.IntegerField(default=0)
    records_failed = models.IntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        db_table = 'ingestion_job'
        ordering = ['-created_at']
```

### 3.2 Services (To Implement)

```python
# ingestion/services.py
from typing import Dict, Any, List
from django.core.cache import cache
import hashlib


class IngestionService:
    """
    Business logic for data ingestion.
    """
    
    CACHE_PREFIX = "ingestion:"
    CACHE_TTL = 3600  # 1 hour
    
    @classmethod
    def validate_payload(cls, data: Dict[str, Any]) -> List[str]:
        """
        Validate incoming payload structure.
        
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        if not isinstance(data, dict):
            errors.append("Payload must be a JSON object")
            return errors
        
        # Add custom validation rules
        if 'records' not in data:
            errors.append("Missing required field: records")
        
        return errors
    
    @classmethod
    def deduplicate(cls, data: Dict[str, Any]) -> str:
        """
        Generate deduplication hash for payload.
        
        Returns:
            SHA256 hash of canonical JSON representation
        """
        import json
        canonical = json.dumps(data, sort_keys=True)
        return hashlib.sha256(canonical.encode()).hexdigest()
    
    @classmethod
    def is_duplicate(cls, data: Dict[str, Any]) -> bool:
        """Check if payload is a duplicate within TTL window."""
        data_hash = cls.deduplicate(data)
        cache_key = f"{cls.CACHE_PREFIX}dedup:{data_hash}"
        return cache.get(cache_key) is not None
    
    @classmethod
    def mark_processed(cls, data: Dict[str, Any]) -> None:
        """Mark payload as processed for deduplication."""
        data_hash = cls.deduplicate(data)
        cache_key = f"{cls.CACHE_PREFIX}dedup:{data_hash}"
        cache.set(cache_key, True, timeout=cls.CACHE_TTL)
```

---

## 4. Verification Module Implementation

### 4.1 Models (To Implement)

```python
# verification/models.py
from django.db import models


class VerificationResult(models.Model):
    """
    Stores verification results for ingested data.
    """
    
    id = models.UUIDField(primary_key=True, editable=False)
    ingestion_job = models.ForeignKey(
        'ingestion.IngestionJob',
        on_delete=models.CASCADE,
        related_name='verifications'
    )
    
    # Result
    passed = models.BooleanField()
    score = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    
    # Details
    checks_performed = models.JSONField(default=list)
    failures = models.JSONField(default=list)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'verification_result'
```

### 4.2 Validators (To Implement)

```python
# verification/validators.py
from typing import Dict, Any, List, Callable


class BaseValidator:
    """Base class for all validators."""
    
    name: str = "base_validator"
    
    def validate(self, data: Dict[str, Any]) -> tuple[bool, str]:
        """
        Validate data.
        
        Returns:
            Tuple of (passed, error_message)
        """
        raise NotImplementedError


class SchemaValidator(BaseValidator):
    """Validates data against expected schema."""
    
    name = "schema_validator"
    
    def __init__(self, schema: Dict[str, Any]):
        self.schema = schema
    
    def validate(self, data: Dict[str, Any]) -> tuple[bool, str]:
        if not isinstance(data, dict):
            return False, "Data must be a dictionary"
        
        for field, field_type in self.schema.items():
            if field not in data:
                return False, f"Missing required field: {field}"
            if not isinstance(data[field], field_type):
                return False, f"Invalid type for field: {field}"
        
        return True, ""


class BusinessRuleValidator(BaseValidator):
    """Validates business rules."""
    
    name = "business_rule_validator"
    
    def __init__(self, rules: List[Callable[[Dict], bool]]):
        self.rules = rules
    
    def validate(self, data: Dict[str, Any]) -> tuple[bool, str]:
        for i, rule in enumerate(self.rules):
            try:
                if not rule(data):
                    return False, f"Business rule {i+1} failed"
            except Exception as e:
                return False, f"Business rule {i+1} error: {str(e)}"
        
        return True, ""
```

---

## 5. Workers Module Implementation

### 5.1 Consumer Implementation (To Implement)

```python
# workers/consumers.py
import pika
import json
import logging
from typing import Callable, Dict, Any

logger = logging.getLogger(__name__)


class TaskConsumer:
    """
    RabbitMQ consumer for processing async tasks.
    """
    
    QUEUE_NAME = "decision_tasks"
    PREFETCH_COUNT = 1  # Fair dispatch
    
    def __init__(self, task_handlers: Dict[str, Callable]):
        """
        Initialize consumer with task handlers.
        
        Args:
            task_handlers: Dict mapping task_type to handler function
        """
        self.task_handlers = task_handlers
        self.connection: pika.BlockingConnection = None
        self.channel: pika.channel.Channel = None
    
    def connect(self, host: str = "localhost", port: int = 5672) -> None:
        """Establish connection to RabbitMQ."""
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=host,
                port=port,
                heartbeat=600,
            )
        )
        self.channel = self.connection.channel()
        
        # QoS - fair dispatch
        self.channel.basic_qos(prefetch_count=self.PREFETCH_COUNT)
    
    def start_consuming(self) -> None:
        """Start consuming messages."""
        self.channel.basic_consume(
            queue=self.QUEUE_NAME,
            on_message_callback=self._on_message,
        )
        
        logger.info(f"Starting consumer on queue: {self.QUEUE_NAME}")
        self.channel.start_consuming()
    
    def _on_message(
        self,
        channel: pika.channel.Channel,
        method: pika.spec.Basic.Deliver,
        properties: pika.BasicProperties,
        body: bytes
    ) -> None:
        """
        Handle incoming message.
        """
        try:
            message = json.loads(body.decode('utf-8'))
            task_type = message.get('task_type')
            
            logger.info(f"Received task: {task_type}")
            
            if task_type not in self.task_handlers:
                logger.error(f"Unknown task type: {task_type}")
                channel.basic_nack(method.delivery_tag, requeue=False)
                return
            
            # Execute handler
            handler = self.task_handlers[task_type]
            handler(message)
            
            # Acknowledge
            channel.basic_ack(method.delivery_tag)
            logger.info(f"Task completed: {task_type}")
            
        except Exception as e:
            logger.exception(f"Task failed: {e}")
            # Nack and requeue
            channel.basic_nack(method.delivery_tag, requeue=True)
    
    def close(self) -> None:
        """Close connection."""
        if self.channel:
            self.channel.close()
        if self.connection:
            self.connection.close()
```

### 5.2 Task Handlers (To Implement)

```python
# workers/tasks.py
from api.models import Decision, DecisionStatus
from core.rabbitmq import RabbitMQClient


def process_decision_task(message: dict) -> None:
    """
    Process a decision task.
    
    Args:
        message: Task message with decision_id and input_data
    """
    from api.services import DecisionEngine
    
    decision_id = message['payload']['decision_id']
    input_data = message['payload']['input_data']
    
    try:
        decision = Decision.objects.get(id=decision_id)
        decision.status = DecisionStatus.PROCESSING
        decision.save(update_fields=['status'])
        
        # Execute decision engine
        engine = DecisionEngine()
        result = engine.execute(input_data)
        
        decision.mark_completed(result)
        
    except Exception as e:
        if decision:
            decision.mark_failed(str(e))
        raise
```

---

## 6. Database Schema Specifications

### 6.1 Entity Relationship Diagram

```
┌─────────────────────────┐
│      api_decision       │
├─────────────────────────┤
│ PK id (UUID)            │
│    name (VARCHAR)       │
│    description (TEXT)   │
│    input_data (JSON)    │
│    status (VARCHAR)     │
│    result (JSON)        │
│    error_message (TEXT) │
│    created_at (TIMESTAMP│
│    updated_at (TIMESTAMP│
│    processed_at (TIMEST │
│    metadata (JSON)      │
└─────────────────────────┘

┌─────────────────────────┐
│    ingestion_job        │
├─────────────────────────┤
│ PK id (UUID)            │
│    source (VARCHAR)     │
│    status (VARCHAR)     │
│    raw_data (JSON)      │
│    validation_errors    │
│    records_processed    │
│    records_failed       │
│    created_at           │
│    started_at           │
│    completed_at         │
│    metadata             │
└─────────────────────────┘
          │
          │ 1:N
          ▼
┌─────────────────────────┐
│  verification_result    │
├─────────────────────────┤
│ PK id (UUID)            │
│ FK ingestion_job_id     │
│    passed (BOOLEAN)     │
│    score (DECIMAL)      │
│    checks_performed     │
│    failures             │
│    created_at           │
└─────────────────────────┘

┌─────────────────────────┐
│     workers_job         │
├─────────────────────────┤
│ PK id (UUID)            │
│    task_type (VARCHAR)  │
│    status (VARCHAR)     │
│    payload (JSON)       │
│    result (JSON)        │
│    retry_count (INT)    │
│    created_at           │
│    started_at           │
│    completed_at         │
└─────────────────────────┘
```

### 6.2 Index Strategy

| Table | Index | Type | Purpose |
|-------|-------|------|---------|
| `api_decision` | `status` | B-Tree | Filter by status |
| `api_decision` | `created_at` | B-Tree | Ordering, range queries |
| `ingestion_job` | `status` | B-Tree | Filter pending jobs |
| `ingestion_job` | `created_at` | B-Tree | Time-based queries |
| `verification_result` | `ingestion_job_id` | B-Tree | FK lookup |

---

## 7. API Contract Specifications

### 7.1 Decision API

#### 7.1.1 Create Decision

```http
POST /api/v1/decisions/
Content-Type: application/json
Authorization: Bearer <token>

Request:
{
    "name": "string (required, max 255)",
    "description": "string (optional)",
    "input_data": {
        "key": "value"
    },
    "metadata": {}
}

Response (201 Created):
{
    "id": "uuid",
    "name": "string",
    "status": "pending",
    "created_at": "ISO8601 timestamp"
}
```

#### 7.1.2 Get Decision

```http
GET /api/v1/decisions/{id}/
Authorization: Bearer <token>

Response (200 OK):
{
    "id": "uuid",
    "name": "string",
    "status": "completed",
    "result": {},
    "created_at": "ISO8601",
    "processed_at": "ISO8601"
}
```

#### 7.1.3 Get Decision Result (Cached)

```http
GET /api/v1/decisions/{id}/result/
Authorization: Bearer <token>

Response (200 OK):
{
    "data": {},
    "cached": true
}
```

---

## 8. Message Queue Specifications

### 8.1 Message Schema

```json
{
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["task_id", "task_type", "payload"],
    "properties": {
        "task_id": {
            "type": "string",
            "format": "uuid",
            "description": "Unique task identifier"
        },
        "task_type": {
            "type": "string",
            "enum": ["decision.process", "data.validate", "report.generate"]
        },
        "payload": {
            "type": "object",
            "description": "Task-specific data"
        },
        "timestamp": {
            "type": "integer",
            "description": "Unix timestamp"
        },
        "priority": {
            "type": "integer",
            "default": 0,
            "minimum": 0,
            "maximum": 10
        }
    }
}
```

### 8.2 Queue Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| `x-message-ttl` | 86400000 | Message expires after 24h |
| `x-max-length` | 10000 | Max messages in queue |
| `x-overflow` | reject-publish | Reject when full |

---

## 9. Cache Implementation Details

### 9.1 Key Naming Convention

```
Format: <module>:<entity>:<identifier>:<purpose>

Examples:
- decision:result:<uuid>
- ingestion:dedup:<hash>
- session:<session_id>
- ratelimit:<user_id>:<endpoint>
```

### 9.2 TTL Configuration

| Cache Type | TTL | Rationale |
|------------|-----|-----------|
| Decision Result | 300s | Short-term, frequently accessed |
| Ingestion Dedup | 3600s | Prevent duplicates within hour |
| Session | 1209600s (2 weeks) | Django default |
| Rate Limit | 60s | Per-minute limiting |

---

## 10. Error Handling Specifications

### 10.1 Exception Hierarchy

```python
class DecisionVaultError(Exception):
    """Base exception for all application errors."""
    status_code = 500


class ValidationError(DecisionVaultError):
    """Data validation failed."""
    status_code = 400


class NotFoundError(DecisionVaultError):
    """Resource not found."""
    status_code = 404


class DuplicateError(DecisionVaultError):
    """Duplicate resource."""
    status_code = 409


class QueueError(DecisionVaultError):
    """RabbitMQ operation failed."""
    status_code = 503


class CacheError(DecisionVaultError):
    """Redis operation failed."""
    status_code = 503
```

### 10.2 Error Response Format

```json
{
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "Human-readable message",
        "details": [
            {"field": "name", "message": "This field is required"}
        ],
        "timestamp": "2026-02-18T10:30:00Z",
        "request_id": "uuid"
    }
}
```

---

## 11. Testing Strategy

### 11.1 Test Pyramid

```
           /\
          /  \      E2E Tests (10%)
         /----\     - API integration
        /      \    - Full workflow
       /--------\   
      /          \  Integration Tests (30%)
     /------------\- Database, RabbitMQ, Redis
    /              \
   /----------------\- Unit Tests (60%)
  /                 \- Models, Services, Validators
 /--------------------\
```

### 11.2 Test Structure

```
backend/
├── api/
│   ├── tests/
│   │   ├── test_models.py
│   │   ├── test_serializers.py
│   │   ├── test_views.py
│   │   └── test_services.py
├── core/
│   ├── tests/
│   │   ├── test_rabbitmq.py
│   │   └── test_cache.py
```

### 11.3 Test Commands

```bash
# Run all tests
python manage.py test

# Run specific module
python manage.py test api.tests.test_views

# With coverage
coverage run manage.py test
coverage report
```

---

## 12. Performance Considerations

### 12.1 Database Optimization

```python
# Use select_related for FK
Decision.objects.select_related('user').all()

# Use prefetch_related for M2M/Reverse FK
IngestionJob.objects.prefetch_related('verifications').all()

# Use only() for partial fetch
Decision.objects.only('id', 'status').all()

# Add database indexes
class Meta:
    indexes = [
        models.Index(fields=['status', 'created_at']),
    ]
```

### 12.2 Caching Strategy

```python
from django.core.cache import cache
from django.views.decorators.cache import cache_page

# Low-level cache API
def get_decision_result(decision_id):
    cache_key = f"decision:result:{decision_id}"
    result = cache.get(cache_key)
    if result is None:
        result = compute_result(decision_id)
        cache.set(cache_key, result, timeout=300)
    return result

# View-level caching
@cache_page(60 * 5)
def decision_list_view(request):
    ...
```

### 12.3 Async Processing

```python
# Offload to RabbitMQ instead of synchronous
# BAD: Synchronous processing
def create_decision(request):
    decision = Decision.objects.create(...)
    result = process_decision(decision)  # Slow!
    return Response(result)

# GOOD: Async processing
def create_decision(request):
    decision = Decision.objects.create(...)
    with RabbitMQClient() as mq:
        mq.publish({"task_id": str(decision.id), ...})
    return Response({"status": "queued"})
```

---

**Document Version**: 1.0  
**Last Updated**: 2026-02-18  
**Related**: [L1 Overview](./ARCHITECTURE_L1_OVERVIEW.md) | [L2 Detailed](./ARCHITECTURE_L2_DETAILED.md)
