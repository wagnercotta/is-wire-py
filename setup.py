from setuptools import setup, find_packages

setup(
    name='is_wire',
    version='1.2.1',
    description='Python implementation of application support layer.',
    long_description=open("README.md").read().strip(),
    long_description_content_type="text/markdown",
    author='labvisio',
    author_email='labvisio.ufes@gmail.com',
    url='http://github.com/labvisio/is-wire-py',
    classifiers=[
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3 :: Only',
    ],
    license='MIT',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    zip_safe=False,
    install_requires=[
        'colorlog==3.1.4',
        'amqp==5.1.1',
        'protobuf==3.20.3',
        'opencensus==0.5.0',
        'prometheus-client==0.3.1',
    ],
)
