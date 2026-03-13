import sys
print(sys.executable)
import starlette
print('starlette', starlette.__version__)
from starlette.applications import Starlette
print('Imported Starlette class', Starlette)
from eden.app import Eden
print('Eden imported successfully')
