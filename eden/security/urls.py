import urllib.parse
from eden.requests import Request

def is_safe_url(url: str, request: Request) -> bool:
    """
    Ensure a URL is safe to redirect to.
    
    A URL is considered safe if it is a relative path or if it 
    matches the scheme and host of the current request.
    """
    if not url:
        return False
        
    # Unquote and strip whitespace to prevent bypasses like '  /next' or '%20/next'
    url = urllib.parse.unquote(url.strip())
    
    # Check if relative path (starts with / but not //)
    if url.startswith('/') and not url.startswith('//'):
        return True
        
    # Full URL case - must match request host
    parts = urllib.parse.urlparse(url)
    if not parts.netloc:
        # If no netloc (host), it's either an invalid URL or relative
        return parts.path.startswith('/')
        
    # Check against host
    host = request.headers.get("host", "")
    if parts.netloc == host:
        return True
        
    return False
