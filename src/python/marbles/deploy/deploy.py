import sys
import time
import os
import subprocess
from EC2 import *   # Elastic Cloud Computing
from ECS import *   # Elastic Container Service
from ECR import *   # Elastic Container Registry

BASE_DIR = '/Users/tjt7a/src/ie/'


# Start the service, stop the service, and update the service
TASKS = ['start', 'stop', 'update']

# 'status']
YES = ['y', 'Y', 'YES', 'yes']
WARNING = 'WARNING: Are you sure you want to start AWS Service? : '

# ECS-Optimized AMI
#   http://docs.aws.amazon.com/AmazonECS/latest/developerguide/ecs-optimized_AMI.html
#   ami-7d664a1d

website_directory = BASE_DIR + '/site/.'
site_instance_id = 'i-01b237a02cb5d2a24'
website_task = 'website-task:2'
website_task_id = '29710003-9aa3-473d-af68-3ce9eb91b912'

infox_directiory = BASE_DIR + '/src/python/services/infox/.'
infox_instance_id = 'i-0220c9759829695f1'
infox_task = 'infox-task:1'
infox_task_id = '4aa8bd46-4f5a-430c-a017-7763d511fed4'

ccg_directory = BASE_DIR + '/src/python/services/ccgparser/.'
ccg_instance_id = 'i-0cf2672035e37dfbf'
ccg_task = 'ccg-task:1'
# Need to complete
ccg_task_id = None

newsreader_directory = BASE_DIR + '/src/python/services/newsreader/.'
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

        elif task == 'update':

            # ---- Update the docker image ----
            ecr = ECR()

            # Print available images
            ecr.list_images('marbles-website')

            print("IMPORTANT: Retrieve AWS Login command and log in")
            print("\t Make sure that Docker is running on your machine")
            print("\taws ecr get-login --no-include-email --region us-west-1")
            print("\t Then copy-paste the command to log in")

            if str(raw_input("Have you logged in?")) not in YES:
                print "You decided not to log in"
                exit(0)
            else:
                # Build docker image
                ecr.build_docker('marbles-website', website_directory)

                # Tag the docker image
                ecr.tag_docker('marbles-website:latest',
                               '763510959652.dkr.ecr.us-west-1.amazonaws.com/marbles-website:latest')

                # Push the docker image
                ecr.push_docker('763510959652.dkr.ecr.us-west-1.amazonaws.com/marbles-website:latest')

                # Print available images
                ecr.list_images('marbles-website')

                print("Done updating the website image!")


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

        elif task == 'update':

            # ---- Update the docker image ----
            ecr = ECR()

            # Print available images
            ecr.list_images('marbles-infox')

            print("IMPORTANT: Retrieve AWS Login command and log in")
            print("\t Make sure that Docker is running on your machine")
            print("\taws ecr get-login --no-include-email --region us-west-1")
            print("\t Then copy-paste the command to log in")

            if str(raw_input("Have you logged in?")) not in YES:
                print "You decided not to log in"
                exit(0)
            else:
                # Build docker image
                ecr.build_docker('marbles-infox', infox_directiory)

                # Tag the docker image
                ecr.tag_docker('marbles-infox:latest',
                               '763510959652.dkr.ecr.us-west-1.amazonaws.com/marbles-infox:latest')

                # Push the docker image
                ecr.push_docker('763510959652.dkr.ecr.us-west-1.amazonaws.com/marbles-infox:latest')

                # Print available images
                ecr.list_images('marbles-infox')

                print("Done updating the marbles-infox image!")

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

            print "Starting ccg task"
            ecs = ECS()
            print ecs.run_task('ccg-task:2')

        elif task == 'stop':

            # ---- Stop the Website Task ---- #

            if str(raw_input('WARNING: Stop? ')) not in YES:
                print("You decided not to stop the ccg task")
                exit(0)
            else:
                print("Stopping ccg task")

            ecs = ECS()
            ecs.stop_task('29710003-9aa3-473d-af68-3ce9eb91b912')

            # ---- Wait for the Task to Stop ---- $
            print "Waiting for the task to stop"
            time.sleep(20)

            # Stop EC2 Instance
            ec2 = EC2()
            print ec2.stop(ccg_instance_id)

        elif task == 'update':

            # ---- Update the docker image ----
            ecr = ECR()

            # Print available images
            ecr.list_images('marbles-ccg')

            print("IMPORTANT: Retrieve AWS Login command and log in")
            print("\t Make sure that Docker is running on your machine")
            print("\taws ecr get-login --no-include-email --region us-west-1")
            print("\t Then copy-paste the command to log in")

            if str(raw_input("Have you logged in?")) not in YES:
                print "You decided not to log in"
                exit(0)
            else:
                # Build docker image
                ecr.build_docker('marbles-ccg', ccg_directiory)

                # Tag the docker image
                ecr.tag_docker('marbles-ccg:latest',
                               '763510959652.dkr.ecr.us-west-1.amazonaws.com/marbles-ccg:latest')

                # Push the docker image
                ecr.push_docker('763510959652.dkr.ecr.us-west-1.amazonaws.com/marbles-ccg:latest')

                # Print available images
                ecr.list_images('marbles-ccg')

                print("Done updating the marbles-ccg image!")

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

        elif task == 'update':

            # ---- Update the docker image ----
            ecr = ECR()

            # Print available images
            ecr.list_images('marbles-newsreader')

            print("IMPORTANT: Retrieve AWS Login command and log in")
            print("\t Make sure that Docker is running on your machine")
            print("\taws ecr get-login --no-include-email --region us-west-1")
            print("\t Then copy-paste the command to log in")

            if str(raw_input("Have you logged in?")) not in YES:
                print "You decided not to log in"
                exit(0)
            else:
                # Build docker image
                ecr.build_docker('marbles-newsreader', newsreader_directiory)

                # Tag the docker image
                ecr.tag_docker('marbles-newsreader:latest',
                               '763510959652.dkr.ecr.us-west-1.amazonaws.com/marbles-newsreader:latest')

                # Push the docker image
                ecr.push_docker('763510959652.dkr.ecr.us-west-1.amazonaws.com/marbles-newsreader:latest')

                # Print available images
                ecr.list_images('marbles-newsreader')

                print("Done updating the marbles-newsreader image!")
