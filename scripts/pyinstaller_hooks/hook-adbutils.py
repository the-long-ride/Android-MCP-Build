"""PyInstaller hook for adbutils: use the host's installed ADB.

The standard PyInstaller contributed hook bundles adbutils/binaries/adb.exe.
For this build we explicitly do NOT package that executable. Android-MCP
resolves the host's ADB using ANDROID_MCP_ADB_PATH or PATH and publishes the
resolved location as ADBUTILS_ADB_PATH before uiautomator2 connects.
"""

# Keep the optional package import available for adbutils, but do not
# collect the vendor-shipped adb.exe as a data file.
hiddenimports = ["adbutils.binaries"]
datas = []
