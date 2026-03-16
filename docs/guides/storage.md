# File Storage & Assets 📁

Eden provides a unified file storage abstraction that allows you to swap between local storage and cloud providers seamlessly.

## Overview

The storage system is built around **Backends**. You can configure a default backend for your application and use it via the standard API.

### Features
- Unified API: `save()`, `url()`, `delete()`.
- Multi-backend support: Local disk, S3, Supabase.
- Secure URLs: Automatic generation of public or presigned private URLs.
- Orphan handling: Automatic cleanup of files on model deletion.

---

## Installation

Storage backends beyond the local filesystem are available as an optional extra:

```bash
pip install eden-framework[storage]
```

---

## Configuration

### Local Storage
Great for development or single-server deployments.

```python
from eden.storage import LocalStorageBackend

storage = LocalStorageBackend(path="/var/uploads")
```

### Amazon S3
The industry standard for scalable object storage.

```python
from eden.storage import S3StorageBackend

storage = S3StorageBackend(
    bucket="my-app-bucket",
    region="us-east-1",
    # Uses AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY from environment
)
```

### Supabase Storage
Perfect for applications already using the Supabase ecosystem.

```python
from eden.storage import SupabaseStorageBackend

storage = SupabaseStorageBackend(
    url="https://xxxx.supabase.co",
    key="anon-key",
    bucket="my-bucket"
)
```

---

## Basic Usage

### Saving Files
You can save raw content or file-like objects (e.g., from an HTMX upload).

```python
# From a request file
key = await storage.save(
    content=request.files['upload'],
    name="profile.jpg",
    folder="users"
)
# Returns: "users/profile_a1b2c3de.jpg"
```

### Retrieving URLs
Eden handles the differences between public and private bucket URLs for you.

```python
# Get a public URL
url = storage.url(key) 
# https://bucket.s3.amazonaws.com/users/profile.jpg
```

### Private Files & Presigned URLs
For sensitive documents, use presigned URLs that expire after a set time.

```python
presigned_url = await storage.get_presigned_url(
    key="private/contract.pdf",
    expires_in=3600  # 1 hour
)
```

### Deleting Files
```python
await storage.delete(key)
```

---

## ORM Integration

Eden models can automatically manage file fields using the `File` type.

```python
from eden.db import Model, f
from typing import Optional

class User(Model):
    name: str = f()
    avatar_key: Optional[str] = f()  # Store the storage key
    
    @property
    def avatar_url(self):
        if not self.avatar_key:
            return "/static/default-avatar.png"
        return app.storage.url(self.avatar_key)
```

---

## Asset Pipeline

Eden manages static assets (CSS, JS, Images) separately from user-uploaded content.

### Static Files
Place your static assets in the `static/` directory. They are automatically served by Eden during development.

### Asset Manifest
In production, use the `eden assets build` command to bundle and version your assets for optimal performance.

---

**Next Steps**: [Background Tasks](background-tasks.md)
