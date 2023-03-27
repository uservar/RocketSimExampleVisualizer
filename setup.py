from setuptools import setup

with open("README.md", "r") as readme_file:
    long_description = readme_file.read()

with open("requirements.txt", "r") as req_file:
    requirements = req_file.readlines()

setup(
    name="rocketsimvisualizer",
    version="1.0.0",
    author="uservar",
    description="A pyqtgraph visualizer for RocketSim",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/uservar/RocketSimExampleVisualizer",
    packages=["rocketsimvisualizer"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    package_data={'': ['rsvconfig-default.toml']},
    include_package_data=True
)
