from setuptools import setup, find_packages

with open("requirements.txt") as f:
    install_requires = f.read().strip("\n").split("\n")

setup(
    name="hr_master",
    version="15.0.0",
    description="HR Master - AI-powered candidate sourcing and ranking system for ERPNext v15+",
    author="HR Master Team",
    author_email="info@hrmaster.com",
    packages=find_packages(),
    include_package_data=True,
    install_requires=install_requires,
    python_requires=">=3.11",
)
