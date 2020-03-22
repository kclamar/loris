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

## Docker Image installation (Skip everything above)
###### Stop all docker processes (specially datajoint), prune all volumes and delete all docker images. Make sure nothng is running on ports 1234 and 3366

```
cd loris
sudo docker-compose up
```
You might an error something like in the logs
## **IGNORE IT**

##### pymysql.err.OperationalError: (2003, "Can't connect to MySQL server on 'mysql' ([Errno 111] Connection refused)")
### Final working app
![](images/get_result.png)
![](images/get_result2.png)
