#!/usr/bin/env bash

[ "x$AWS_ACCESS_KEY_ID" != "x" ] || exit 1
[ "x$AWS_SECRET_ACCESS_KEY" != "x" ] || exit 1
[ "x$AWS_DEFAULT_REGION" != "x" ] || AWS_DEFAULT_REGION="us-west-1"

echo "[plugins]" > /var/awslogs/etc/aws.conf
echo "cwlogs = cwlogs" >> /var/awslogs/etc/aws.conf
echo "" >> /var/awslogs/etc/aws.conf
echo "[default]" >> /var/awslogs/etc/aws.conf
echo "region = $AWS_DEFAULT_REGION" >> /var/awslogs/etc/aws.conf
echo "aws_access_key_id = $AWS_ACCESS_KEY_ID" >> /var/awslogs/etc/aws.conf
echo "aws_secret_access_key = $AWS_SECRET_ACCESS_KEY" >> /var/awslogs/etc/aws.conf
