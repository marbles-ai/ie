import sys
from EC2 import *
from ECS import *

TASKS = ['start', 'stop', 'status']
YES = ['y', 'Y', 'YES', 'yes']
WARNING = 'WARNING: Are you sure you want to start AWS Service?'

# ECS-Optimized AMI
#   http://docs.aws.amazon.com/AmazonECS/latest/developerguide/ecs-optimized_AMI.html
#   ami-7d664a1d

site_instance_id = 'i-01b237a02cb5d2a24'
# infox_instance_id = 'infox instance id'
# ccg_instance_id = 'ccg instance id'
# news_instance_id = 'news reader instance id'

if __name__ == "__main__":

    service = sys.argv[1]
    task = sys.argv[2]
    argument = None

    if len(sys.argv) > 3:
        argument = sys.argv[3]

    if task not in TASKS:
        print("Available Tasks: ", TASKS)

    # ---- For the website ---- #

    if service in ['site', 'website']:

        if task == 'start':

            if str(raw_input(WARNING)) not in YES:
                print("You decided not to start AWS services")
                exit(0)
            else:
                print("Starting AWS services")

            # Start EC2 Instance
            ec2 = EC2()
            print ec2.start(site_instance_id)

        elif task == 'stop':

            print("Stopping AWS services")
            # Stop EC2 Instance
            ec2 = EC2()
            print ec2.stop(site_instance_id)

    # ---- For the infox service ---- #

    elif service in ['infox']:

        if task == 'start':

            if str(raw_input(WARNING)) not in YES:
                print("You decided not to start AWS services")
                exit(0)
            else:
                print("Starting AWS services")

            # Start EC2 Instance
            ec2 = EC2()
            print ec2.start(infox_instance_id)

        elif task == 'stop':

            print("Stopping AWS service")

            ec2 = EC2()
            print ec2.stop(infox_instance_id)

    # ---- For the ccgparser ---- #

    elif service in ['ccg', 'ccgparser']:

        if task == 'start':

            if str(raw_input(WARNING)) not in YES:
                print("You decided not to start AWS services")
                exit(0)
            else:
                print("Starting AWS service")

            # Start EC2 Instance
            ec2 = EC2()
            print ec2.start(ccg_instance_id)

        elif task == 'stop':

            print("Stopping AWS service")

            ec2 = EC2()
            print ec2.stop(ccg_instance_id)


