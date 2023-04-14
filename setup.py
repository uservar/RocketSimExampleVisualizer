from setuptools import setup
import platform

with open("README.md", "r") as readme_file:
    long_description = readme_file.read()

with open("requirements.txt", "r") as req_file:
    requirements = req_file.readlines()
    print(requirements)
    if platform.system() == "Windows":
        python_version_minor = int(platform.python_version_tuple()[1])
        if python_version_minor < 11:
            requirements.append("sleep_until")

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
