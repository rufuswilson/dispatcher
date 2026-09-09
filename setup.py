from setuptools import setup

setup(
    name="dispatcher",
    maintainer="marsou75",
    maintainer_email="marsou75@gmail.com",
    description="A library for event-driven programming, extracted from Django",
    packages=[
        "dispatcher",
    ],
    version="1.1.0",
    url="https://github.com/rufuswilson/dispatcher",
    install_requires=["asgiref"],
    package_data={"dispatcher": ["dispatcher.pyi", "py.typed"]},
    python_requires=">=3.11",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Programming Language :: Python :: 3.14",
        "License :: OSI Approved :: BSD License",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
)
