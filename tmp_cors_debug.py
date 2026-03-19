import inspect
from starlette.middleware.cors import CORSMiddleware
print(inspect.getsource(CORSMiddleware.is_allowed_origin))
