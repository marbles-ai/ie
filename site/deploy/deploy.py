from EC2 import *

if __name__ == "__main__":
    ec2 = EC2()

    # VPCs
    #VpcId = ec2.get_vpcs()['Vpcs'][0]['VpcId']
    #ec2.get_security_groups()
    print(ec2.get_security_group("sg-e5ad4e83"))