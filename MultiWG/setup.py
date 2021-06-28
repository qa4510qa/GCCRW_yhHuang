from setuptools import setup

setup(name='MultiWG',
      version='2.0.2',
      description='Multi-site stochastic weather generator',
      url='',
      author='Chung-Yi Lin',
      author_email='philip928lin@gmail.com',
      license='NotOpenYet',
      packages=['MultiWG'],
      install_requires = ['numpy', 'pandas', 'scipy', 'matplotlib', 'statsmodels','tqdm'],
      zip_safe=False)