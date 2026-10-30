from setuptools import setup, find_packages
import pathlib

here = pathlib.Path(__file__).parent.resolve()
long_description = (here / 'README.md').read_text(encoding='utf-8') if (here / 'README.md').exists() else None

setup(
    name='mobmess',
    version='0.1.0',
    description='Identifies evolutionary relations among mobile genetic elements, e.g. identify plasmid systems.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/michaelkyu/mobmess',
    author='Michael Ku Yu', 
    author_email='michaelkuyu@gmail.com',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Science/Research',
        'Topic :: Scientific/Engineering :: Bio-Informatics',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3.13',
        'Programming Language :: Python :: 3 :: Only',
    ],
    keywords='mobile genetic elements, plasmid, metagenomics',
    packages=find_packages(),
    python_requires='>=3.10',
    install_requires=[
        'numpy',
        'pandas',
        'scipy',
        'scikit-learn',
        'igraph',
        'numba',
        'blosc',
    ], 
    extras_require={
        'visualize': [
            'matplotlib',
            'seaborn',
            'pypdf',
            'jinja2',
        ],
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'mobmess=mobmess.mobmess_script:run',
        ],
    },
    project_urls={
        'Source': 'https://github.com/michaelkyu/mobmess/',
    },
)
