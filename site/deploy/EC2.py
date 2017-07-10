import boto3
from botocore.exceptions import ClientError


# Class for EC2 functions
class EC2:

    def __init__(self):
        self.ec2 = boto3.client('ec2')

    def describe(self):
        return self.ec2.describe_instances()

    # Start an instance
    def start(self, instance_id):
        try:
            self.ec2.start_instance(InstanceIds=[instance_id],
                                    DryRun=True)
        except ClientError as ce:
            if 'DryRunOperation' not in str(ce):
                raise

        try:
            response = self.ec2.start_instance(InstanceIds=[instance_id],
                                               DryRun=False)
            return response

        except ClientError as ce:
            print(ce)

    # Stop an instance
    def stop(self, instance_id):
        try:
            self.ec2.stop_instances(InstanceIds=[instance_id],
                                    DryRun=True)
        except ClientError as ce:
            if 'DryRunOperation' not in str(ce):
                raise

        try:
            response = self.ec2.stop_instances(InstanceIds=[instance_id],
                                               DryRun=False)
            return response
        except ClientError as ce:
            print(ce)

    # Reboot an instance
    def reboot(self, instance_id):
        try:
            self.ec2.reboot_instances(InstanceIds=['INSTANCE_ID'],
                                      DryRun=True)
        except ClientError as ce:
            if 'DryRunOperation' not in str(ce):
                print("Don't have permissions to reboot")
                raise

        try:
            response = self.ec2.reboot_instances(InstanceIds=['INSTANCE_ID'],
                                                 DryRun=True)
            print("Success: ", response)
        except ClientError as ce:
            print("Error: ", ce)

    # Get VPC id
    def get_vpcs(self):
        return self.ec2.describe_vpcs()

    # Create security group
    def create_security_group(self, group_name, description, vpc, permissions):
        try:
            response = self.ec2.create_security_group(GroupName=group_name,
                                                      Description=description,
                                                      VpcId=vpc)
            group_id = response['GroupId']
            print('Security Group Created %s in vpc %s.' % (group_id, vpc))

            data = self.ec2.authorize_security_group_ingress(GroupId=group_id,
                                                             IpPermissions=permissions)

            print("Ingress set %s" % data)
        except ClientError as ce:
            print("Failed to create security group: ", ce)

    # Get security group information
    def get_security_group(self, group_id):
        try:
            response = self.ec2.describe_security_groups(GroupIds=[group_id])
            return response
        except ClientError as ce:
            print("Failed to return security groups: ", ce)