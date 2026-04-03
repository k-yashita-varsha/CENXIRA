"""Setup configuration for keycloak_auth package."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="keycloak-auth",
    version="1.0.0",
    author="Training Portal Team",
    author_email="dev@company.com",
    description="Keycloak OIDC JWT validation with Admin API integration",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/training-portal/keycloak-auth",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
    ],
    python_requires=">=3.11",
    install_requires=[
        "fastapi>=0.104.0",
        "pydantic>=2.0.0",
        "pydantic-settings>=2.0.0",
        "requests>=2.31.0",
        "PyJWT>=2.8.0",
        "cryptography>=41.0.0",
    ],
)