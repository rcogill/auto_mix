## AutoMix: Automatic Generation of Beatmatched Playlists 

This repository contains a collection of scripts that will generate a beatmatched and mixed collection of mp3 files from a given collection of input mp3 files and a description of the desired mix. The mix description is specified as a YAML file with a format described in the section [Mix Description File](#mix-description-file).

These scripts can be used in several ways. If all required dependecies are installed, a mix can be generated at the command line by using the script `mix.py` in the `src` directory. The exact usage of this script is:

`python mix.py --playlist_file FILE.YAML --directory DIR`

Here FILE.YAML is the YAML-formatted mix description file and DIR is the directory containing the playlist file and all input mp3 files to be mixed.

This repository contains a Dockerfile which can be used to build a container image that contains all required dependencies to run `mix.py`. Specifically, this container can be built by running  `docker build -t auto_mix .` to build the container image, then `docker run -it auto_mix bash` to run an interactive terminal session in this container. If all input files required to build a mix are trasferred to the container, then `mix.py` could be run within the container.

However, our *real* goal here is to provide all components required to implement a mix generation service. Users upload a zip archive containing their audio files and mix description file, and the service returns a zip file containing the beatmatched and mixed audo files. This is still a work-in-progress, and the current components and architecture are described in the section [Mix Generation Service](#mix-generation-service).

### Mix Description File

The mix description file is a YAML file that specifies the sequence of songs to be mixed and details of the mix entry and exit points. A sample called `playlist.yaml` is included in this repository. This YAML file contains a list of songs, with the following fields specified for each:
* `track` : This is the name of the audio file associated with the track.
* `mix_in` : This specifies the timing of the mix's entry point into this track. The fields `start` and `end` specify the times that crossfading into this track starts and ends. The field `beats` specifies the number of beats between `start` and `end`.
* `mix_out` : This specifies the timing of the mix's exit point from this track. The fields `start` and `end` specify the times that crossfading out of this track starts and ends. The field `beats` specifies the number of beats between `start` and `end`.

The fields `mix_in` and `mix_out` are optional. In general, `mix_in` is not specified for the first track in the set and `mix_out` is not specified for the last tranck in the set. If either is not specified for any intermediate tracks, mix will simply transition into the next track without crossfading or beatmatching. 

### Mix Generation Service

Some of the components required to provide mix generation as a service are provided here. These components can be deployed on Amazon Web Services using S3, SQS, EC2, and Lambda instances. The overall architecture works as follows:
* A user can drop a zip file containing audio files and a mix description file into an S3 bucket.
* When this event occurs, a Lambda function is triggered that places a message in an SQS queue. Among other metadata, this message contains the name of the zip file that was just placed in the queue. 
* A worker EC2 instance runs a process that continually polls the SQS queue waiting for mix jobs to arrive. When this process receives a new message from the queue, it copies the zip file from the S3 bucket, processes the mix, creates a new zip file containing the mixed audio files, and places this new zip file back in the S3 bucket.

This is still a work in progress, but some components required to implement this are provided in the repository and described below. One thing that is still missing is a script that can programmatically provision and configure the infrastructure on AWS needed to run this. 

The specific components that implement this are the following:
* `queue_process.py` : This script runs on an ec2 instance (optionally with a Docker container). This script continually polls the queue specified within `conf.yaml` for new jobs to process. When a new job arrives, this script calls `mix_worker.py` to generate the mix.
* `mix_lambda.py` : This simple Lambda function is responsible for inserting new messages into the SQS queue when new files are placed in the S3 bucket. The queue URL is retrieved from an environment variable which must be set when configuring the Lambda function.