#!/usr/bin/env bash

HAVE_ENV_CREDENTIALS=1
[ "x$AWS_ACCESS_KEY_ID" != "x" ] || HAVE_ENV_CREDENTIALS=0
[ "x$AWS_SECRET_ACCESS_KEY" != "x" ] || HAVE_ENV_CREDENTIALS=0
[ "x$AWS_DEFAULT_REGION" != "x" ] || AWS_DEFAULT_REGION="us-west-1"

if [ $HAVE_ENV_CREDENTIALS -eq 1 ]; then
	echo "[plugins]" > /var/awslogs/etc/aws.conf
	echo "cwlogs = cwlogs" >> /var/awslogs/etc/aws.conf
	echo "" >> /var/awslogs/etc/aws.conf
	echo "[default]" >> /var/awslogs/etc/aws.conf
	echo "region = $AWS_DEFAULT_REGION" >> /var/awslogs/etc/aws.conf
	echo "aws_access_key_id = $AWS_ACCESS_KEY_ID" >> /var/awslogs/etc/aws.conf
	echo "aws_secret_access_key = $AWS_SECRET_ACCESS_KEY" >> /var/awslogs/etc/aws.conf
elif [ -e ~/.aws/credentials ]; then
	echo "[plugins]" > /var/awslogs/etc/aws.conf
	echo "cwlogs = cwlogs" >> /var/awslogs/etc/aws.conf
	cat ~/.aws/credentials >> /var/awslogs/etc/aws.conf
	echo "region = $AWS_DEFAULT_REGION" >> /var/awslogs/etc/aws.conf
fi
