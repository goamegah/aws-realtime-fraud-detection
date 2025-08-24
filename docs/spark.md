# PySpark installation and configuration guide
## Windows
Install WSL and Ubuntu via Microsoft Store.

To work in optimal conditions, I recommend VScode with the Remote Development plugin.

Once WSL and Ubuntu are installed, all subsequent steps will be performed in the Ubuntu terminal.
## Installation
### MacOS

```shell
brew install apache-spark
```
### Ubuntu
1. **Download Apache Spark**
    - Go to the [Apache Spark download page](https://spark.apache.org/downloads.html) and follow the instructions for 
   your preferred version.

2. **Extract and move Spark**

```bash
$ tar -xzf spark-<version>-bin-hadoop<version>.tgz
$ sudo mv spark-<version>-bin-hadoop<version> /opt/spark
```

3. **Verify Spark directory**

```bash
$ ls /opt/spark
bin   data      jars        LICENSE   NOTICE  R          RELEASE  yarn
conf  examples  kubernetes  licenses  python  terraform.md  sbin
```
You should see directories like `bin`, `conf`, `jars`, `python`, etc.

4. **Set environment variables**

Add the following lines to your `~/.bashrc`:
```bash
$ export PYSPARK_PYTHON=/usr/bin/python3 # or your preferred Python version path
$ export SPARK_HOME=/opt/spark
$ export PYTHONPATH=$SPARK_HOME/python:$SPARK_HOME/python/lib/py4j-0.10.9-src.zip # for Spark 3.5.5
$ export PATH=$PATH:$SPARK_HOME/bin
```
Reload your shell:
```bash
$ source ~/.bashrc
```

5. **Install Java (OpenJDK 11)**

```bash
sudo apt install openjdk-11-jdk -y
```

6. **Verify Spark installation**

```bash
$SPARK_HOME/bin/pyspark --version
```

## Notes

- Adjust paths and versions as needed.
- For more details, refer to the [official Spark documentation](https://spark.apache.org/docs/latest/).
- Ensure your Python and Java versions are compatible with your Spark version.