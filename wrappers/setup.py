from setuptools import setup, Extension
from pybind11.setup_helpers import Pybind11Extension, build_ext

ext_modules = [
    Pybind11Extension(
        "redisstore",
        ["binding.cpp", "redis_store.cpp"],  # Include redis_store.cpp
        include_dirs=["./"],
        extra_compile_args=["-std=c++17"],
    ),
]

setup(
    name="redistore",
    version="0.1",
    author="Your Name",
    author_email="your.email@example.com",
    description="Python bindings for Redis Store C++ library",
    ext_modules=ext_modules,
    cmdclass={"build_ext": build_ext},
    zip_safe=False,
    python_requires=">=3.8",
)
