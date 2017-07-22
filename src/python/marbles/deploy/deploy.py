import sys
import time
from EC2 import *
from ECS import *

TASKS = ['start', 'stop']
# 'status']
YES = ['y', 'Y', 'YES', 'yes']
WARNING = 'WARNING: Are you sure you want to start AWS Service? : '

# ECS-Optimized AMI
#   http://docs.aws.amazon.com/AmazonECS/latest/developerguide/ecs-optimized_AMI.html
#   ami-7d664a1d

site_instance_id = 'i-01b237a02cb5d2a24'
website_task = 'website-task:2'
website_task_id = '29710003-9aa3-473d-af68-3ce9eb91b912'

infox_instance_id = 'i-0220c9759829695f1'
infox_task = 'infox-task:1'
infox_task_id = '4aa8bd46-4f5a-430c-a017-7763d511fed4'

ccg_instance_id = 'i-0cf2672035e37dfbf'
ccg_task = 'ccg-task:1'
# Need to complete
ccg_task_id = None

newsreader_instance_id = 'i-0db3be783604998cb'
newsreader_task = 'newsreader-task:1'
# Need to complete
newsreader_task_id = None

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

            # ---- Start the EC2 Instance ---- #

            if str(raw_input(WARNING)) not in YES:
                print("You decided not to start AWS services")
                exit(0)
            else:
                print("Starting AWS services")

            # Start EC2 Instance
            ec2 = EC2()
            print ec2.start(site_instance_id)

            # ---- Wait for the Instance to Start ---- $
            # Make sure instance is up and running
            print "Waiting for the instance to start"
            time.sleep(20)

            # ---- Start the Task ---- #

            print "Starting website task"
            ecs = ECS()
            print ecs.run_task(website_task)

        elif task == 'stop':

            # ---- Stop the Website Task ---- #

            if str(raw_input('WARNING: Stop? ')) not in YES:
                print("You decided not to stop the website task")
                exit(0)
            else:
                print("Stopping website task")

            ecs = ECS()
            ecs.stop_task('29710003-9aa3-473d-af68-3ce9eb91b912')

            # ---- Wait for the Task to Stop ---- $
            print "Waiting for the task to stop"
            time.sleep(20)

            # Stop EC2 Instance
            ec2 = EC2()
            print ec2.stop(site_instance_id)

    # ---- For the infox service ---- #

    elif service in ['infox']:

        if task == 'start':

            # ---- Start the EC2 Instance ---- #

            if str(raw_input(WARNING)) not in YES:
                print("You decided not to start AWS services")
                exit(0)
            else:
                print("Starting AWS services")

            # Start EC2 Instance
            ec2 = EC2()
            print ec2.start(infox_instance_id)

            # ---- Wait for the Instance to Start ---- $
            # Make sure instance is up and running
            print "Waiting for the instance to start"
            time.sleep(20)

            # ---- Start the Task ---- #

            print "Starting website task"
            ecs = ECS()
            print ecs.run_task(infox_task)

        elif task == 'stop':

            # ---- Stop the Website Task ---- #

            if str(raw_input('WARNING: Stop? ')) not in YES:
                print("You decided not to stop the website task")
                exit(0)
            else:
                print("Stopping website task")

            ecs = ECS()
            print(ecs.stop_task(infox_task_id))

            # ---- Wait for the Task to Stop ---- $
            print "Waiting for the task to stop"
            time.sleep(20)

            # Stop EC2 Instance
            ec2 = EC2()
            print(ec2.stop(infox_instance_id))

    # ---- For the ccgparser ---- #

    elif service in ['ccg', 'ccgparser']:

        if task == 'start':

            # ---- Start the EC2 Instance ---- #

            if str(raw_input(WARNING)) not in YES:
                print("You decided not to start AWS services")
                exit(0)
            else:
                print("Starting AWS services")

            # Start EC2 Instance
            ec2 = EC2()
            print ec2.start(ccg_instance_id)

            # ---- Wait for the Instance to Start ---- $
            # Make sure instance is up and running
            print "Waiting for the instance to start"
            time.sleep(20)

            # ---- Start the Task ---- #

            print "Starting website task"
            ecs = ECS()
            print ecs.run_task('website-task:2')

        elif task == 'stop':

            # ---- Stop the Website Task ---- #

            if str(raw_input('WARNING: Stop? ')) not in YES:
                print("You decided not to stop the website task")
                exit(0)
            else:
                print("Stopping website task")

            ecs = ECS()
            ecs.stop_task('29710003-9aa3-473d-af68-3ce9eb91b912')

            # ---- Wait for the Task to Stop ---- $
            print "Waiting for the task to stop"
            time.sleep(20)

            # Stop EC2 Instance
            ec2 = EC2()
            print ec2.stop(site_instance_id)

# ---- For the newsreader ---- #

    elif service in ['news', 'newsreader']:

        if task == 'start':

            # ---- Start the EC2 Instance ---- #

            if str(raw_input(WARNING)) not in YES:
                print("You decided not to start AWS services")
                exit(0)
            else:
                print("Starting AWS services")

            # Start EC2 Instance
            ec2 = EC2()
            print ec2.start(newsreader_instance_id)

            # ---- Wait for the Instance to Start ---- $
            # Make sure instance is up and running
            print "Waiting for the instance to start"
            time.sleep(20)

            # ---- Start the Task ---- #

            print "Starting website task"
            ecs = ECS()
            print ecs.run_task(newsreader_task)

        elif task == 'stop':

            # ---- Stop the Website Task ---- #

            if str(raw_input('WARNING: Stop? ')) not in YES:
                print("You decided not to stop the website task")
                exit(0)
            else:
                print("Stopping Newsreader task")

            ecs = ECS()
            ecs.stop_task(newsreader_task_id)

            # ---- Wait for the Task to Stop ---- $
            print "Waiting for the task to stop"
            time.sleep(20)

            # Stop EC2 Instance
            ec2 = EC2()
            print ec2.stop(newsreader_instance_id)
