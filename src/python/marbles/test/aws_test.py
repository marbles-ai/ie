from __future__ import unicode_literals, print_function
import unittest
import os
import json
import logging
from moto import mock_s3, mock_sqs
from marbles import aws
from marbles.ie import grpc
from marbles.ie.compose import CO_NO_WIKI_SEARCH
import boto3
#from botocore.exceptions import QueueDoesNotExist


datadir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'ie', 'test', 'data')
datafiles = [
    os.path.join(datadir, '77a7e0b715396ba02b7fe12aa6c87336.json'),
    os.path.join(datadir, '774e08800dfe1aaa4598149cf5208df3.json'),
    os.path.join(datadir, 'a223515d444768b863e3a4d94b2a19a3.json'),
    os.path.join(datadir, 'c0053ac368cf2e5c2599f035f2ee4eea.json')
]


class MockedState(aws.ServiceState):
    def __init__(self, *args, **kwargs):
        super(MockedState, self).__init__(*args, **kwargs)
        self.tick = 1.0
        self.pass_on_exceptions = True

    def wait(self, seconds):
        self.tick += 1.0

    def time(self):
        self.tick += 1.0
        return self.tick


class MockedArticle(object):
    def __init__(self, fn, resp):
        self.resp = resp
        hash, _ = os.path.splitext(os.path.basename(fn))
        self.fn = '02/testsrc/this-is-a-test/' + hash

    def archive(self, scraper):
        return self.resp

    def get_aws_s3_names(self, text):
        return 'test-bucket-2017-06', self.fn


# Mock rss feeds and src
class MockedFeed(object):
    def __init__(self):
        # Mock response for Article.archive(scraper)
        self.articles = []
        for fn in datafiles:
            with open(fn, 'r') as fp:
                self.articles.append(MockedArticle(fn, json.load(fp)))

    def get_articles(self, ignore_read):
        return self.articles


class MockedNewsSource(object):
    def __init__(self):
        self.feeds = [ MockedFeed() ]
        self.scraper = None


class MockedBrowser(object):
    def get_blank(self):
        pass

    def close(self):
        pass


class TestAWS(unittest.TestCase):

    def setUp(self):
        self.mocked_src = MockedNewsSource()
        logger = logging.getLogger(__name__)
        logger.addHandler(logging.NullHandler())
        self.state = MockedState(logger)
        self.svc = grpc.CcgParserService(daemon='easysrl', logger=self.state.logger)

    def tearDown(self):
        self.svc.shutdown()

    @mock_s3
    @mock_sqs
    def test1_NewsQueueWriter(self):
        # Create AWS virtual resources
        try:
            awsres = aws.AwsNewsQueueWriterResources('default-queue')
            self.fail()
        except Exception as e:
            pass
        sqs = boto3.client('sqs')
        response = sqs.create_queue(QueueName='marbles-ai-rss-aggregator')
        self.assertTrue('QueueUrl' in response)
        s3 = boto3.client('s3')
        response = s3.create_bucket(Bucket='marbles-ai-feeds-hash')
        # Boto3 documentation says 'Location' is in the response however when mocking boto3 through moto
        # we get different keys. Not sure if this is error in moto or documentation.
        #self.assertTrue('Location' in response)
        self.assertTrue('ResponseMetadata' in response)
        self.assertTrue('HTTPStatusCode' in response['ResponseMetadata'])
        self.assertTrue(response['ResponseMetadata']['HTTPStatusCode'] == 200)

        awsres = aws.AwsNewsQueueWriterResources('default-queue')
        nqw = aws.AwsNewsQueueWriter(awsres, self.state, [self.mocked_src], MockedBrowser())
        nqw.read_all(True)
        # Check s3
        actual = [bkt.name for bkt in awsres.s3.buckets.all()]
        expected = ['test-bucket-2017-06', 'marbles-ai-feeds-hash']
        self.assertListEqual(actual, expected)
        self.assertEqual(len(nqw.hash_cache), 4)
        self.assertTrue(nqw.check_hash_exists('77a7e0b715396ba02b7fe12aa6c87336'))
        self.assertTrue(nqw.check_hash_exists('774e08800dfe1aaa4598149cf5208df3'))
        self.assertTrue(nqw.check_hash_exists('a223515d444768b863e3a4d94b2a19a3'))
        self.assertTrue(nqw.check_hash_exists('c0053ac368cf2e5c2599f035f2ee4eea'))

        # Retiring pushes out oldest
        nqw.retire_hash_cache(2)
        self.assertEqual(len(nqw.hash_cache), 2)
        self.assertTrue('a223515d444768b863e3a4d94b2a19a3' in nqw.hash_cache)
        self.assertTrue('c0053ac368cf2e5c2599f035f2ee4eea' in nqw.hash_cache)

        self.assertTrue(nqw.check_hash_exists('77a7e0b715396ba02b7fe12aa6c87336'))
        self.assertEqual(len(nqw.hash_cache), 3)
        self.assertTrue(nqw.check_hash_exists('774e08800dfe1aaa4598149cf5208df3'))
        self.assertEqual(len(nqw.hash_cache), 4)

        # Read message queue
        hashes = set(nqw.hash_cache.iterkeys())
        msgcount = 0

        for message in aws.receive_messages(awsres.news_queue, MessageAttributeNames=['All']):
            self.assertIsNotNone(message.message_attributes)
            hash = message.message_attributes.get('hash').get('StringValue')
            self.assertTrue(hash in hashes)
            hashes.remove(hash)
            message.delete()
            msgcount += 1

        self.assertEqual(msgcount, 4)


    @mock_s3
    @mock_sqs
    def test2_NewsQueueReader(self):
        # Create AWS virtual resources
        sqs = boto3.client('sqs')
        sqs.create_queue(QueueName='marbles-ai-rss-aggregator')
        sqs.create_queue(QueueName='marbles-ai-discourse-logic')
        s3 = boto3.client('s3')
        s3.create_bucket(Bucket='marbles-ai-feeds-hash')

        # Create marbles resources
        stub = self.svc.open_client()
        # AwsNewsQueueWriterResources is a subset of these so can share
        awsres = aws.AwsNewsQueueReaderResources(stub, 'default-queue', 'default-queue')

        # Write to news_queue
        nqw = aws.AwsNewsQueueWriter(awsres, self.state, [self.mocked_src], MockedBrowser())
        nqw.read_all(True)

        # Read from news_queue and write to ccg_queue
        nqr = aws.AwsNewsQueueReader(awsres, self.state, CO_NO_WIKI_SEARCH)
        nqr.run()

        # Read ccg_queue
        hashes = set(nqw.hash_cache.iterkeys())
        self.assertEqual(len(hashes), 4)
        msgcount = 0

        for message in aws.receive_messages(awsres.ccg_queue, MessageAttributeNames=['All']):
            self.assertIsNotNone(message.message_attributes)
            hash = message.message_attributes.get('hash').get('StringValue')
            self.assertTrue(hash in hashes)
            hashes.remove(hash)
            message.delete()
            msgcount += 1

        self.assertEqual(msgcount, 4)

if __name__ == '__main__':
    unittest.main()
