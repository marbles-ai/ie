import boto3
import subprocess


class ECR:

    def __init__(self):
        self.ecr = boto3.client('ecr')

    def list_images(self, repository):
        response = self.ecr.list_images(
            repositoryName=repository
        )
        print "----- Available Images -----"
        for image in response['imageIds']:
            print image

    def build_docker(self, image_name, root_directory):
        subprocess.call(['docker', 'build', '-t', image_name,
                        root_directory])

    def tag_docker(self, tag, image):
        subprocess.call(['docker', 'tag', tag, image])

    def push_docker(self, image):
        subprocess.call(['docker', 'push',
                         image])

