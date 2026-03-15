"""
Real-time File Upload Progress Tracking with WebSocket

This example demonstrates how to add real-time progress tracking to file uploads
using WebSocket connections to push progress updates to the client.

## Features
- Stream file chunks with progress callbacks
- Send progress updates via WebSocket to connected clients
- Support for large file uploads without blocking
- Atomic storage with automatic rollback on error

## Architecture
1. Client uploads file with chunked transfer
2. Server receives chunks and calls progress callback
3. Callback broadcasts progress via WebSocket
4. Client displays real-time progress bar

## Usage

In your app routes file:

```python
from eden import app, WebSocket
from eden.forms import UploadSchema, ProgressCallback
from eden.storage import StorageManager
from eden.db import FileReference
import json

# WebSocket connection tracking
upload_connections = {}


@app.websocket_route("/ps/upload/{upload_id}")
async def ws_upload_progress(websocket: WebSocket, upload_id: str):
    '''Accept WebSocket for upload progress updates.
    
    The client connects to this WebSocket when starting a file upload.
    Progress updates are received as JSON: {"bytes_written": N, "total_bytes": M}
    '''
    await websocket.accept()
    upload_connections[upload_id] = websocket
    try:
        # Keep connection open
        while True:
            await websocket.receive_text()
    except Exception:
        pass
    finally:
        upload_connections.pop(upload_id, None)
        await websocket.close()


def get_progress_callback(upload_id: str, total_bytes: int) -> ProgressCallback:
    '''Create a progress callback that broadcasts via WebSocket.
    
    Args:
        upload_id: Unique upload session ID
        total_bytes: Total bytes being uploaded
        
    Returns:
        Async callback for storage.save(callback=...)
    '''
    async def on_progress(bytes_written: int, total_bytes: int):
        """Send progress update to connected WebSocket client."""
        if upload_id in upload_connections:
            ws = upload_connections[upload_id]
            try:
                percentage = (bytes_written / total_bytes * 100) if total_bytes > 0 else 0
                await ws.send_json({
                    "bytes_written": bytes_written,
                    "total_bytes": total_bytes,
                    "percentage": percentage,
                })
            except Exception as e:
                # Client disconnected or error
                import logging
                logging.getLogger(__name__).debug(f"WS send error: {e}")
    
    return on_progress


@app.post("/api/upload")
async def upload_file(request):
    '''Handle file upload with real-time progress tracking.
    
    Request:
        multipart/form-data with file
        query param: upload_id (matches WebSocket connection)
    
    Response:
        {"status": "success", "file_path": "s3://..."}
    '''
    upload_id = request.query_params.get("upload_id")
    if not upload_id:
        return {"status": "error", "message": "Missing upload_id"}
    
    # Parse form
    form = await UploadSchema.from_request(request)
    if not form.is_valid():
        return {"status": "error", "errors": form.errors}
    
    # Get uploaded file
    file = form.files.get("document")
    if not file:
        return {"status": "error", "message": "No file provided"}
    
    # Create progress callback
    progress_callback = get_progress_callback(upload_id, file.size)
    
    try:
        # Use atomic transaction for storage + DB
        async with storage.transaction() as txn:
            # Upload with progress tracking
            file_path = await storage.get("s3").save(
                file.filename,
                file.data,
                progress_callback=progress_callback
            )
            
            # Link file to model (e.g., User avatar)
            user_id = request.user.id
            await FileReference.create_from_upload(
                model_class=User,
                model_id=user_id,
                file_path=file_path,
                storage_backend="s3"
            )
        
        return {
            "status": "success",
            "file_path": file_path,
            "filename": file.filename,
        }
    
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception("Upload failed")
        return {
            "status": "error",
            "message": "Upload failed: " + str(e),
        }
```

## Client-Side Integration

### HTML Template with Progress

```html
<!DOCTYPE html>
<html>
<body>
  <form id="upload-form" enctype="multipart/form-data">
    <input type="file" name="document" id="document" accept=".pdf,.docx" />
    <button type="submit">Upload</button>
  </form>
  
  <div id="progress" style="display:none;">
    <progress id="progress-bar" value="0" max="100" style="width:100%;"></progress>
    <span id="progress-text">0%</span>
  </div>
  
  <script src="/static/upload.js"></script>
</body>
</html>
```

### JavaScript Upload Handler

```js
// /static/upload.js
const form = document.getElementById('upload-form');
const fileInput = document.getElementById('document');
const progressDiv = document.getElementById('progress');
const progressBar = document.getElementById('progress-bar');
const progressText = document.getElementById('progress-text');

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  
  const file = fileInput.files[0];
  if (!file) return;
  
  // Generate upload ID for progress tracking
  const uploadId = 'upload_' + Math.random().toString(36).substr(2, 9);
  
  // Connect to WebSocket for progress updates
  const ws = new WebSocket(`/ps/upload/${uploadId}`);
  
  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    const percentage = Math.round(data.percentage);
    progressBar.value = percentage;
    progressText.textContent = percentage + '%';
  };
  
  ws.onerror = (error) => {
    console.error('WebSocket error:', error);
    ws.close();
  };
  
  // Upload file
  progressDiv.style.display = 'block';
  
  const formData = new FormData();
  formData.append('document', file);
  
  try {
    const response = await fetch(`/api/upload?upload_id=${uploadId}`, {
      method: 'POST',
      body: formData,
    });
    
    const result = await response.json();
    
    if (result.status === 'success') {
      console.log('Upload complete:', result.file_path);
      alert('File uploaded successfully!');
    } else {
      alert('Upload failed: ' + result.message);
    }
  } catch (error) {
    console.error('Upload error:', error);
    alert('Upload failed: ' + error.message);
  } finally {
    ws.close();
    progressDiv.style.display = 'none';
    progressBar.value = 0;
    progressText.textContent = '0%';
  }
});
```

## Alternative: Server-Sent Events (SSE)

For simpler implementations without WebSocket, use Server-Sent Events:

```python
from starlette.responses import StreamingResponse
from starlette.types import Send, Receive, Scope
import asyncio

# Track active uploads
upload_events = {}

@app.get("/api/upload-progress/{upload_id}")
async def upload_progress_sse(upload_id: str):
    '''Stream progress events to client via SSE.'''
    
    async def event_generator():
        # Wait for upload to start
        await asyncio.sleep(0.1)
        
        while upload_id in upload_events:
            data = upload_events[upload_id]
            yield f"data: {json.dumps(data)}\\n\\n"
            await asyncio.sleep(0.1)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
    )

# Update progress callback to store events
def get_progress_callback(upload_id: str, total_bytes: int):
    async def on_progress(bytes_written: int, total_bytes: int):
        percentage = (bytes_written / total_bytes * 100) if total_bytes > 0 else 0
        upload_events[upload_id] = {
            "bytes_written": bytes_written,
            "total_bytes": total_bytes,
            "percentage": percentage,
        }
    
    return on_progress
```

Client-side SSE usage:

```js
const eventSource = new EventSource(`/api/upload-progress/${uploadId}`);

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  const percentage = Math.round(data.percentage);
  progressBar.value = percentage;
  progressText.textContent = percentage + '%';
};

eventSource.onerror = () => {
  eventSource.close();
};
```

## Integration with FileField

Use FileField for consistent form rendering:

```python
class UploadSchema(Schema):
    document: Optional[bytes] = field(
        widget="file", 
        label="Upload Document",
        json_schema_extra={
            "accept": ".pdf,.docx,.txt",
            "show_progress": True,
        }
    )
```

Template usage:

```html
{{ form['document'].render_with_progress() }}
```

## Best Practices

1. **Upload ID Generation**: Use a unique ID per upload session to track progress
2. **Connection Management**: Clean up WebSocket connections when uploads complete
3. **Error Handling**: Gracefully handle connection drops and retries
4. **Timeout**: Set a timeout for stale upload connections
5. **Rate Limiting**: Limit progress update frequency (e.g., every 100ms)
6. **Atomic Transactions**: Use StorageManager.transaction() for file + DB consistency
7. **Cleanup on Failure**: Use FileReference.cleanup_by_model() on error

## Performance Tips

- Use chunked transfer for large files (>10MB)
- Throttle progress updates to reduce overhead
- Stream directly from storage backend when possible
- Consider multipart upload for cloud storage (S3)
- Use CDN for downloadable files after upload

See Also:
- eden/storage.py - StorageManager and storage backends
- eden/db/file_reference.py - FileReference model
- eden/forms.py - FileField class
- tests/test_storage_transactions.py - Atomic upload tests
"""

# This is documentation and example code. 
# Copy the route handlers into your app/__init__.py or app/routes.py
