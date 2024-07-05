from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="luckyrobots",
    version="0.1.0",
    description="Robotics-AI Training in Hyperrealistic Game Environments",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Devrim Yashar",
    author_email="dvrmysr@gmail.com",
    url="https://github.com/lucky-robots/lucky-robots",
    packages=find_packages(),
    install_requires=[
        "watchdog", "pyee", "Flask==2.3.2"
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.8',
)