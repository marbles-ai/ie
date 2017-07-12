from EC2 import *

# Check what's running and stopped
def get_status(ec2):

    # Check running instances:
    print "--- Running Instances ---"
    running = ec2.running()
    print(running)
    print "--- Stopped Instances ---"
    stopped = ec2.stopped()
    print(stopped)

if __name__ == "__main__":

    # First start by checking the status of the instances and start them
    ec2 = EC2()

    # Get the status
    get_status(ec2)

    # To stop an instance
    #ec2.stop('i-0947507900f47f445')

    # To see the existing VPCs and their status
    print("--- VPCs and their status ---")
    print(ec2.get_vpcs())
    print("--- Security Groups ---")
    print(ec2.get_security_groups())






