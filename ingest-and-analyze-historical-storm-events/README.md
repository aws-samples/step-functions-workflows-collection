
# Distributed Map - Ingest and Analyze Historical Storm Events

This application will create a State Machine with AWS Lambda, AWS Glue crawler, Amazon Athena services to ingest and read weather related data files.
The weather files are in zipped format and can be obtained from the website - https://www1.ncdc.noaa.gov/pub/data/swdi/stormevents/csvfiles/. AWS Lambda function decompresses these zipped files and put them in appropriate S3 folders in a S3 bucket with a success. AWS Glue crawler is used to determine and define the schema of these decompressed files with a success. Athena is used to query this data using standard SQL in a table format with a success and the file is stored in Amazon S3 folder where the query results are stored. The user can view the end results from this Amazon S3 folder.


## Requirements

## Deployment Instructions

This project is set up like a standard Python project.  The initialization
process also creates a virtualenv within this project, stored under the `.venv`
directory.  To create the virtualenv it assumes that there is a `python3`
(or `python` for Windows) executable in your path with access to the `venv`
package. If for any reason the automatic creation of the virtualenv fails,
you can create the virtualenv manually.

To manually create a virtualenv on MacOS and Linux:

```
$ python3 -m venv .venv
```

After the init process completes, and the virtualenv is created, you can use the following
step to activate your virtualenv.

```
$ source .venv/bin/activate
```

If you are a Windows platform, you would activate the virtualenv like this:

```
% .venv\Scripts\activate.bat
```

Once the virtualenv is activated, you can install the required dependencies.

```
$ pip install -r requirements.txt
```

At this point you can now synthesize the CloudFormation template for this code.

```
$ cdk synth
```

To add additional dependencies, for example other CDK libraries, just add
them to your `setup.py` file and rerun the `pip install -r requirements.txt`
command.

## Useful commands

 * `cdk ls`          list all stacks in the app
 * `cdk synth`       emits the synthesized CloudFormation template
 * `cdk deploy`      deploy this stack to your default AWS account/region
 * `cdk diff`        compare deployed stack with current state
 * `cdk docs`        open CDK documentation


## How it works

Create raw_source 
![image](./resources/stepfunctions_graph.png)

