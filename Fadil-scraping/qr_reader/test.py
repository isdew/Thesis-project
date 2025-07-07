import ctypes
from ctypes.util import find_library

print(find_library("zbar"))  # Should return a path like '/opt/homebrew/lib/libzbar.dylib'
