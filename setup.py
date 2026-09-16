"""Build py2app : `python3 setup.py py2app -A` (mode alias, cf. README).

Produit un vrai exécutable compilé comme binaire principal du bundle, pour
que macOS puisse identifier et autoriser l'app correctement (TCC micro),
contrairement au lanceur shell qui exec'ait un python3 externe.
"""

from setuptools import setup

APP = ["launcher.py"]
DATA_FILES = []
OPTIONS = {
    "argv_emulation": False,
    "iconfile": "app/icon.icns",
    "packages": ["app"],
    "plist": {
        "CFBundleName": "Cahier",
        "CFBundleDisplayName": "Cahier",
        "CFBundleIdentifier": "com.aaronatlan.cahier",
        "CFBundleShortVersionString": "1.0",
        "CFBundleVersion": "1.0",
        "LSMinimumSystemVersion": "11.0",
        "NSHighResolutionCapable": True,
        "NSMicrophoneUsageDescription": "Cahier a besoin du micro pour enregistrer tes cours.",
        "LSApplicationCategoryType": "public.app-category.education",
    },
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
