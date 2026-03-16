# Logging & Telemetry 📊

Eden provides a unified logging interface that integrates standard Python logging with modern observability tools.

## The Eden Logger

Access the pre-configured logger anywhere in your application. It supports structured logging (JSON) for production and pretty-printed logs for development.

```python
from eden import logger

@app.get("/process")
async def process(request):
    logger.info("Processing request", extra={"user_id": request.user.id})
    
    try:
        # business logic
        pass
    except Exception as e:
        logger.error("Processing failed", exc_info=True)
```

---

## Log Levels

- **DEBUG**: Fine-grained informational events (mostly for developers).
- **INFO**: Confirmation that things are working as expected.
- **WARNING**: Indication that something unexpected happened (e.g., 'disk space low').
- **ERROR**: Due to a more serious problem, the software has not been able to perform some function.
- **CRITICAL**: A serious error, indicating that the program itself may be unable to continue running.

---

## Configuration

Customize your logging behavior in `eden.json`:

```json
{
    "logging": {
        "level": "INFO",
        "format": "json",
        "handlers": ["console", "file"],
        "file_path": "logs/eden.log"
    }
}
```

### Formatters
- `pretty`: Easy to read in a terminal (colors included!).
- `json`: Structured data for Logstash, Datadog, or Google Cloud Logging.

---

## Performance Telemetry

Eden automatically tracks the execution time of various components.

### ORM Profiling
Log slow queries that exceed a certain threshold.
```json
{
    "db": {
        "slow_query_threshold": 0.5
    }
}
```

### Request Timing
Enable the `telemetry` middleware to see a breakdown of where request time is spent.

```python
app.add_middleware("telemetry")
```
Output in logs:
`[TELEMETRY] GET /dashboard - 150ms (ORM: 40ms, Templates: 30ms, Auth: 5ms)`

---

## External Integration

Eden makes it easy to ship logs to external services.

### Sentry Integration
```python
from eden.extras import sentry

sentry.init(
    dsn="https://your-dsn@sentry.io/123",
    environment="production"
)
```

### OpenTelemetry
For enterprise-scale tracing, Eden supports OpenTelemetry out of the box.
```bash
pip install eden-framework[otel]
```

---

**Next Steps**: [Deployment Guide](deployment.md)
