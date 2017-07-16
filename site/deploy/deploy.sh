# A cluster is a name that resolves to a set of member hosts
# 	When an ECS host comes online, it starts an agent that connects to the ECS service and registers with a named cluster.
#	A task is a “run once” container, and a service is a container that should be restarted if it stops.


# Push the image to our AWS repository
aws ecr get-login --no-include-email --region us-west-1

# Build the image
docker build -t marbles-website .

# Tag the image to be pushed
docker tag marbles-website:latest 763510959652.dkr.ecr.us-west-1.amazonaws.com/marbles-website:latest

# Now push the image to the repo
docker push 763510959652.dkr.ecr.us-west-1.amazonaws.com/marbles-website:latest

# Configure your ecs-cli with the correct user profile
ecs-cli configure --profile default --cluster marbles

# Run instance with ECS-Optimized AMI
aws ec2 run-instances --image-id ami-7d664a1d --security-group-ids sg-e5ad4e83 --count 1 --iam-instance-profile Name=ecsInstanceRole --instance-type t2.micro --key-name website-keypair-us-west --query 'Instances[0].InstanceId'
# Returns: "i-06dfe980116174c78"

# This will stop the instance
aws ec2 stop-instances --instance-ids i-06dfe980116174c78
# and return a json message indicating that it's being stopped

# Will return the ip address
# aws ec2 describe-instances --instance-ids i-06dfe980116174c78 --query 'Reservations[0].Instances[0].PublicIpAddress'

# To SSH in to the instance
# ssh -i ~/Downloads/website-keypair-us-west.pem ec2-user@54.219.175.172

# Run a task on the defined cluster
# aws ecs run-task --cluster default --task-definition website-task:2 --count 1

# List tasks running on the given cluster
#  aws ecs list-tasks --cluster default

# Describe the running task:

# Stop the running task
# aws ecs stop-task --task e6eca2e6-746b-4f24-9c0b-64611616c7d9

# Create your cluster with 1 instance of type t2.micro, website keypair, security group ecs-instances-default-cluster
# ecs-cli up --force --keypair website --capability-iam --size 1 --instance-type t2.micro --security-group ecs-instances-default-cluster --vpc vpc-cc929ea9 --subnets subnet-327ca856,subnet-58cad201

# Run a task on the cluster we just threw up
aws ecs run-task --cluster marbles --task-definition website-task

# Show images available
#ecs-cli images

