# Loris
### Database and Analysis application for a Drosophila Lab (or any lab)

Loris is in development with core features still being tested and added.
Documentation for the different features will be added soon.

## Requirements

* Anaconda
* Docker

## Installation

Pull the recent version of Loris:
```
git pull https://github.com/gucky92/dreye.git
git submodule update --init --recursive
```

Create your own `config.json` file. There is a template file called `_config.json`.

Create a new conda environment using the yml file provided and install all submodules:
```
cd loris
conda env create -f loris.yml -n loris
conda activate loris
pip install -e datajoint-python/.
pip install -e .
```

If you do not have a running MySQL database yet, you can install a running SQL database using the docker-compose submodule provided by Loris:
```
cd mysql-docker/slim
sudo docker-compose up -d
```
