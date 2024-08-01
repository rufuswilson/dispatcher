from distutils.core import setup

setup(
    name="pydispatcher",
    maintainer="marsou75",
    maintainer_email="marsou75@gmail.com",
    description="A library for event-driven programming, extracted from Django",
    packages=[
        "dispatcher",
    ],
    version="1.0.0",
    url="https://github.com/xiachufang/dispatcher",
    install_requires=["asgiref"],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "License :: OSI Approved :: BSD License",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
)
