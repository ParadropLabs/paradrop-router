from setuptools import setup, find_packages

setup(
    name="paradrop-router",
    version="0.14",
    description="Paradrop wireless router",
    url="https://paradrop.org",

    project_urls = {
        "Documentation": "https://paradrop.readthedocs.io/en/latest/",
        "Homepage": "https://paradrop.org",
        "Source": "https://github.com/ParadropLabs/paradrop-router",
    },

    packages=find_packages(),

    entry_points={
        "console_scripts": [
            "router = router.main:main"
        ]
    }
)
