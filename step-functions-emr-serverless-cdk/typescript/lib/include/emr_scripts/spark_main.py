import sys
from datetime import datetime

from pyspark.sql import SparkSession
from pyspark.sql.functions import *

if __name__ == "__main__":

    print(len(sys.argv))
    if (len(sys.argv) != 3):
        print("Spark-ETL: [input-folder] [output-folder]")
        sys.exit(0)

    spark = SparkSession\
        .builder\
        .appName("Spark-ETL")\
        .getOrCreate()

    # Read input csv dataset
    btc = spark.read.option("inferSchema", "true").option("header", "true").csv(sys.argv[1])

    # Update the dataset adding a date column
    updatedBTC = btc.withColumn("current_date", lit(datetime.now()))

    updatedBTC.printSchema()

    print(updatedBTC.show())

    print("Total number of rows: " + str(updatedBTC.count()))

    # Write the updated dataset to the output folder
    updatedBTC.write.mode("overwrite").parquet(sys.argv[2])