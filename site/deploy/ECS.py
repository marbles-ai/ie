import boto3


class ECS:

    def __init__(self):
        self.ecs = boto3.client('ecs')

    # ---- CLUSTERS ----

    def list_clusters(self):
        response = self.ecs.list_clusters()
        return response

    def describe_clusters(self, clusters):
        response = self.ecs.describe_clusters(clusters=clusters)
        return response

    def create_cluster(self, name):
        response = self.ecs.create_cluster(clusterName=name)
        return response

    def delete_cluster(self, name):
        response = self.ecs.delete_cluster(cluster=name)
        return response

    # ---- CONTAINERS ----

    def list_container_instances(self, cluster, nextToken, maxResults):
        response = self.ecs.list_container_instances(
            cluster=cluster,
            nextToken=nextToken,
            maxResults=maxResults)
        return response

    def describe_container_instance(self, cluster, containerInstance):
        response = self.ecs.describe_container_instance(cluster=cluster, containerInstance=containerInstance)
        return response

    # ---- TASKS ----

    def list_tasks(self):
        response = self.ecs.list_tasks()
        return response

    def list_task_definitions(self):
        response = self.ecs.list_task_definitions()
        return response

    def describe_tasks(self, cluster, tasks):
        response = self.ecs.describe_tasks(
            cluster=cluster,
            tasks=tasks)
        return response

    def describe_task_definitions(self, task_definition):
        response = self.ecs.describe_task_definition(
            taskDefinition=task_definition)
        return response

    def start_task(self, cluster, definition, start_task, instances):
        response = self.ecs.start_task(cluster=cluster,
                                       taskDefinition=definition,
                                       containerInstances=instances)
        return response

    def run_task(self, taskDefinition):
        response = self.ecs.run_task(
            taskDefinition=taskDefinition,
            count=1
        )
        return response

    def stop_task(self, task):
        response = self.ecs.stop_task(
            task=task
        )
        return response
