import boto3


class ECS:

    def __init__(self):
        self.ecs = boto3.client('ecs')

    def create_cluster(self, name):
        response = self.ecs.create_cluster(clusterName=name)
        return response

    def delete_cluster(self, name):
        response = self.ecs.delete_cluster(cluster=name)
        return response



    ################### TASKS ###################

    def start_task(self, cluster, definition, start_task, instance, group):
        response = self.ecs.start_task(cluster=cluster,
                                    taskDefinition=definition,
                                    containerInstances=instances,
                                    group=group)

        return response