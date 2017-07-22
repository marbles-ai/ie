import boto3


class ECR:

    def __init__(self):
        self.ec2 = boto3.client('ecr')
