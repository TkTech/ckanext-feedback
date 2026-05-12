from setuptools import setup

setup(
    message_extractors={
        "ckanext": [
            ("**.py", "python", None),
            ("**/templates/**.html", "ckan", None),
        ],
    },
)