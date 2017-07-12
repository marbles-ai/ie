import boto3


class ECS:

    def __init__(self):
        self.ecs = boto3.client('ecs')

    # Describe passed clusters
    def describe_cluster(self, clusters):
        response = self.ecs.describe_clusters(
            clusters = clusters
        )
        return response

    def list_clusters(self):
        # Do stuff

    def describe_container_instances(self, cluster, containerInstance):
        response = self.ecs.describe_container_instances(
            cluster = cluster,
            containerInstance = containerInstance
        )
        return response

    def create_cluster(self, name):
        response = self.ecs.create_cluster(clusterName=name)
        return response

    # Can't delete a cluster without first deregistering the containers from it
    def delete_cluster(self, name):
        response = self.ecs.delete_cluster(cluster=name)
        return response

    # Deregister an ECS container instance from a cluster; this cluster can't run tasks anymore
    def deregister_container_instance(self, cluster, containerInstance):
        response = self.ecs.register_container_instance(
            cluster = cluster,
            containerInstance = containerInstance
        )


    def list_services(self):
        # Do stuff

    def describe_services(self):
        # do stuff

    # Run & maintain a number of tasks
    def create_service(self, cluster, serviceName, taskDefinition, loadBalancers, desiredCount, ct, role):
        response = self.ecs.create_services(
            cluster=cluster,
            serviceName=serviceName,
            taskDefinition=taskDefinition,
            loadBalancers=loadBalancers,
            desiredCount=desiredCount,
            clientToken=ct,
            role=role
        )
        return response

    # Delete a service from within a cluster
    def delete_service(self, cluster, service):
        response = self.ecs.delete_service(
            cluster = cluster,
            service = service
        )





    ################### TASKS ###################

    def describe_task_definitions(self):
        # Do stuff

    def describe_tasks(self):
        # Do sdtuff

    def list_tasks(self):
        # Do stuff

    def list_task_definitions(self):
        # Do stuff

    def start_task(self, cluster, definition, start_task, instance, group):
        response = self.ecs.start_task(cluster=cluster,
                                    taskDefinition=definition,
                                    containerInstances=instances,
                                    group=group)
        return response

    def run_task(self):
        # do stuff

    def stop_task(self):
        # do stuff

    def deregister_task_definition(self, taskDefinition):
        response = self.ecs.deregister_task_definition(
            taskDefinition=taskDefinition
        )
        return response

