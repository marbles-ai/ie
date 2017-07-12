import boto3
from botocore.exceptions import ClientError

# Class for EC2 functions
class EC2:


    ######################## Instances ########################
    def __init__(self):
        self.ec2r = boto3.resource('ec2')
        self.ec2c = boto3.client('ec2')


    def running(self):

        instances = self.ec2r.instances.filter(
            Filters=[{'Name': 'instance-state-name',
                      'Values': ['running']}])
        statuses = [(instance.id, instance.instance_type) for
                    instance in instances]
        return statuses

    def stopped(self):

        instances = self.ec2r.instances.filter(
            Filters=[{'Name': 'instance-state-name',
                      'Values': ['stopped']}])
        statuses = [(instance.id, instance.instance_type) for
                    instance in instances]
        return statuses

    # Create a new instance
    def create(self, ami):

        return self.ec2r.create_instances(ImageId=ami, MinCount=1, MaxCount=1)

    # Start an instance
    def start(self, instance_id):

        try:
            self.ec2r.instances.start(InstanceIds=[instance_id],
                                    DryRun=True)
        except ClientError as ce:
            if 'DryRunOperation' not in str(ce):
                raise

        try:
            response = self.ec2r.instances.start(InstanceIds=[instance_id],
                                               DryRun=False)
            return response

        except ClientError as ce:
            print(ce)

    # Stop an instance
    def stop(self, instance_id):
        try:
            self.ec2r.instances.stop(InstanceIds=[instance_id],
                                    DryRun=True)
        except ClientError as ce:
            if 'DryRunOperation' not in str(ce):
                raise

        try:
            response = self.ec2r.instances.stop(InstanceIds=[instance_id],
                                               DryRun=False)
            return response
        except ClientError as ce:
            print(ce)

    # Reboot an instance
    def reboot(self, instance_id):
        try:
            self.ec2r.instances.reboot(InstanceIds=[instance_id],
                                      DryRun=True)
        except ClientError as ce:
            if 'DryRunOperation' not in str(ce):
                print("Don't have permissions to reboot")
                raise

        try:
            response = self.ec2r.instances.reboot(InstanceIds=[instance_id],
                                                 DryRun=True)
            print("Success: ", response)
        except ClientError as ce:
            print("Error: ", ce)

    # Terminate an instance
    def terminate(self, instance_id):
        try:
            self.ec2r.instances.terminate(InstanceIds=[instance_id],
                                     DryRun=True)
        except ClientError as ce:
            if 'DryRunOperation' not in str(ce):
                raise

        try:
            response = self.ec2r.instances.terminate(InstanceIds=[instance_id],
                                                DryRun=False)
            return response
        except ClientError as ce:
            print(ce)


    ######################## VPCs ########################

    # Get VPC id
    def get_vpcs(self):
        vpcs = [(vpc['VpcId'], vpc['State']) for vpc in self.ec2c.describe_vpcs()['Vpcs']]
        return vpcs

    # Create security group
    def create_security_group(self, group_name, description, vpc, permissions):
        try:
            response = self.ec2c.create_security_group(GroupName=group_name,
                                                      Description=description,
                                                      VpcId=vpc)
            group_id = response['GroupId']
            print('Security Group Created %s in vpc %s.' % (group_id, vpc))

            data = self.ec2c.authorize_security_group_ingress(GroupId=group_id,
                                                             IpPermissions=permissions)

            print("Ingress set %s" % data)
        except ClientError as ce:
            print("Failed to create security group: ", ce)

    # Get security group information
    def get_security_groups(self):
        try:
            response = self.ec2c.describe_security_groups()
            return response['SecurityGroups']
        except ClientError as ce:
            print("Failed to return security groups: ", ce)

    ######################## TASKS ########################

    def start_task(self, cluster):
        self.ec2c.start_task(
            cluster=cluster,
            taskDefinition
        )