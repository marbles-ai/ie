#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

import StringIO
import base64
import json
import logging
import mimetypes
import time

import boto3
import requests
from nltk.tokenize import sent_tokenize

from marbles.ie import grpc
from marbles.ie.ccg import parse_ccg_derivation2 as parse_ccg_derivation
from marbles.ie.semantics.ccg import process_ccg_pt
from marbles.log import ExceptionRateLimitedLogAdaptor
from marbles.ie.utils.text import preprocess_sentence
from svc import ServiceState

_logger = ExceptionRateLimitedLogAdaptor(logging.getLogger(__name__))


def receive_messages(*args, **kwargs):
    queue = args[0]
    args = args[1:]
    if queue is not None:
        maxmsgs = filter(lambda x: x[0] == 'MaxNumberOfMessages', kwargs.iteritems())
        if len(maxmsgs) != 0:
            for msg in queue.receive_messages(*args, **kwargs):
                yield msg
        else:
            msgs = [ None ]
            while len(msgs) != 0:
                msgs = queue.receive_messages(*args, **kwargs)
                for m in msgs:
                    yield m


class AwsNewsQueueBase(object):
    """News queue base class."""

    def __init__(self):
        self.s3 = boto3.resource('s3')
        self.sqs = None
        self.news_queue = None


class AwsNewsQueueWriterResources(AwsNewsQueueBase):
    """AWS news queue writer resources."""

    def __init__(self, queue_name=None):
        super(AwsNewsQueueWriterResources, self).__init__()
        if queue_name:
            self.sqs = boto3.resource('sqs')
            if queue_name == 'default-queue':
                resp = self.sqs.get_queue_by_name(QueueName='marbles-ai-rss-aggregator')
            else:
                resp = self.sqs.get_queue_by_name(QueueName=queue_name)
            self.news_queue = resp
        else:
            self.sqs = None
            self.news_queue = None


class AwsNewsQueueReaderResources(AwsNewsQueueBase):
    """AWS news queue reader resources - includes gRPC client."""

    def __init__(self, stub, news_queue_name, ccg_queue_name=None):
        super(AwsNewsQueueReaderResources, self).__init__()
        self.sqs = boto3.resource('sqs')
        self.stub = stub
        if news_queue_name == 'default-queue':
            resp = self.sqs.get_queue_by_name(QueueName='marbles-ai-rss-aggregator')
        else:
            resp = self.sqs.get_queue_by_name(QueueName=news_queue_name)
        self.news_queue = resp

        if ccg_queue_name:
            if ccg_queue_name == 'default-queue':
                resp = self.sqs.get_queue_by_name(QueueName='marbles-ai-discourse-logic')
            else:
                resp = self.sqs.get_queue_by_name(QueueName=ccg_queue_name)
            self.ccg_queue = resp
        else:
            self.ccg_queue = None


class AwsNewsQueueWriter(object):
    """News queue writer handler. Reads RSS/ATOM feeds and writes to queue. """

    def __init__(self, aws, state, sources, browser):
        self.browser = browser
        self.aws = aws
        self.sources = sources
        self.bucket_cache = set()
        self.hash_cache = {}
        self.state = state

    def close(self):
        self.browser.close()

    def check_bucket_exists(self, bucket):
        if bucket in self.bucket_cache:
            return True
        # Bucket count never exceeds a few 100
        # Refresh all so we handle deletions
        self.bucket_cache = set()
        for bkt in self.aws.s3.buckets.all():
            self.bucket_cache.add(bkt.name)
        return bucket in self.bucket_cache

    def check_hash_exists(self, hash):
        if hash in self.hash_cache:
            self.hash_cache[hash] = self.state.time()
            return True
        exists = 0 != len([x for x in self.aws.s3.Bucket('marbles-ai-feeds-hash').objects.filter(Prefix=hash)])
        if exists:
            self.hash_cache[hash] = self.state.time()
        return exists

    def clear_bucket_cache(self):
        self.bucket_cache = set()

    def retire_hash_cache(self, limit):
        global _logger
        """Retire least recently used in hash cache."""
        if limit >= len(self.hash_cache):
            return
        _logger.info('Retiring hash cache, current-size=%d, required-size=%d', len(self.hash_cache), limit)
        # Each value is a timestamp floating point
        vk_sort = sorted(self.hash_cache.items(), key=lambda x: x[1])
        vk_sort.reverse()
        self.hash_cache = dict(vk_sort[0:limit])

    def refresh(self):
        # TODO: Interleave work
        for src in self.sources:
            if self.state.terminate:
                return
            for rss in src.feeds:
                if self.state.terminate:
                    return
                rss.refresh()
                self.state.wait(1)

    def read_all(self, ignore_read):
        for src in self.sources:
            if self.state.terminate:
                return
            self.read_from_source(src, ignore_read)
        self.browser.get_blank()

    def read_from_source(self, src, ignore_read):
        global _logger
        articles = []
        for rss in src.feeds:
            if self.state.terminate:
                return
            articles.extend(rss.get_articles(ignore_read=ignore_read)) # Returns unread articles

        errors = 0
        for a in articles:
            if self.state.terminate:
                return
            hash = ''
            try:
                arc = a.archive(src.scraper)
                bucket, objname = a.get_aws_s3_names(arc['content'])
                hash = objname.split('/')[-1]
                _logger.debug(hash + ' - ' + arc['title'])
                if self.check_hash_exists(hash):
                    continue

                if not self.check_bucket_exists(bucket):
                    # Create a bucket
                    self.aws.s3.create_bucket(Bucket=bucket,
                                              CreateBucketConfiguration={'LocationConstraint': 'us-west-1'})
                    self.bucket_cache.add(bucket)

                strm = StringIO.StringIO()
                json.dump(arc, strm, indent=2)
                objpath = objname+'.json'
                data = strm.getvalue()
                self.aws.s3.Object(bucket, objpath).put(Body=data)

                # Add to hash listing - allows us to find entries by hash
                self.aws.s3.Object('marbles-ai-feeds-hash', hash).put(Body=bucket + '/' + objpath)

                # Add to AWS processing queue
                if self.aws.news_queue:
                    attributes = {
                        's3': {
                            'DataType': 'String',
                            'StringValue': bucket + '/' + objpath
                        },
                        'hash': {
                            'DataType': 'String',
                            'StringValue': hash
                        }
                    }
                    # Store thumbnail in message so website has immediate access
                    d = arc.setdefault('media', {})
                    if d.setdefault('thumbnail', -1) >= 0:
                        try:
                            media = d['content'][ d['thumbnail']]
                            r = requests.get(media['url'])
                            b64media = base64.b64encode(r.content)
                            attributes['media_thumbnail'] = {
                                'DataType': 'String',
                                'StringValue': b64media
                            }
                            if 'type' in d['content']:
                                attributes['media_type'] = {
                                    'DataType': 'String',
                                    'StringValue': d['content']['type']
                                }
                            else:
                                # Infer type
                                mtype, _ = mimetypes.guess_type(media['url'])
                                if mtype is not None:
                                    attributes['media_type'] = {
                                        'DataType': 'String',
                                        'StringValue': mtype
                                    }
                                else:
                                    _logger.info('Could not infer mime type for url(%s) - message hash(%s)',
                                                 media['url'], hash)
                        except requests.ConnectionError as e:
                            # Non critical error - can happen when replaying old stories
                            _logger.warning('Media not found when processing message hash(%s) - %s', hash, str(e))

                    # Send the message to our queue
                    response = self.aws.news_queue.send_message(MessageAttributes=attributes,
                                                                MessageBody=data)
                    _logger.debug('Sent hash(%s) -> news_queue(%s)', hash, response['MessageId'])

                # Update hash cache
                self.hash_cache[hash] = self.state.time()

            except KeyboardInterrupt:
                # Pass on so we can close when running in console mode
                raise

            except Exception as e:
                # Exception source defined by file-name:line-number:exeption-class:hash
                _logger.exception('AwsNewsQueueWriter.read_from_source', exc_info=e, rlimitby=hash)
                errors += 1
                if self.state.pass_on_exceptions:
                    raise

            self.state.wait(1)


class AwsNewsQueueReader(object):
    """News queue reader handler"""

    def __init__(self, aws, state, options=0):
        self.aws = aws
        self.state = state
        self.options = options

    def run(self):
        """Process messages."""
        for message in receive_messages(self.aws.news_queue, MessageAttributeNames=['All']):
            global _logger
            # Attributes will be passed onto next queue
            attributes = message.message_attributes
            mhash = attributes['hash']['StringValue']
            _logger.debug('Received news_queue(%s) -> hash(%s)', message.message_id, mhash)
            body = json.loads(message.body)
            retry = 3
            ccgbank = None
            title = body['title']
            paragraphs_in = filter(lambda y: len(y) != 0, map(lambda x: x.strip(), body['content'].split('\n')))
            paragraphs_out = []
            if len(paragraphs_in) == 0:
                _logger.debug('No paragraphs for story %s\n%s', (mhash, title))
            # Use NLTK to split paragraphs into sentences.
            for p in paragraphs_in:
                sentences = filter(lambda x: len(x.strip()) != 0, sent_tokenize(p))
                paragraphs_out.append(sentences)

            if self.state.terminate:
                break

            result = {}
            result['title'] = {}
            while retry:
                try:
                    ccgbank = grpc.ccg_parse(self.aws.stub, title, grpc.DEFAULT_SESSION)
                    pt = parse_ccg_derivation(ccgbank)
                    ccg = process_ccg_pt(pt, options=self.options)
                    result['title']['lexemes'] = [x.get_json() for x in ccg.get_span()]
                    result['title']['constituents'] = [c.get_json() for c in ccg.constituents]
                    ccgpara = []
                    result['paragraphs'] = ccgpara
                    for sentences in paragraphs_out:
                        ccgsent = []
                        ccgpara.append(ccgsent)
                        for s in sentences:
                            smod = preprocess_sentence(s)
                            ccgbank = grpc.ccg_parse(self.aws.stub, smod, grpc.DEFAULT_SESSION)
                            pt = parse_ccg_derivation(ccgbank)
                            ccg = process_ccg_pt(pt, options=self.options)
                            ccgentry = {}
                            ccgentry['lexemes'] = [x.get_json() for x in ccg.get_span()]
                            ccgentry['constituents'] = [c.get_json() for c in ccg.constituents]
                            ccgsent.append(ccgentry)
                    break   # exit while
                except requests.exceptions.ConnectionError as e:
                    time.sleep(0.25)
                    retry -= 1
                    _logger.exception('AwsNewsQueueReader.run', exc_info=e)
                    if self.state.pass_on_exceptions:
                        raise
                except Exception as e:
                    # After X reads AWS sends the item to the dead letter queue.
                    # X is configurable in AWS console.
                    retry = 0
                    _logger.exception('AwsNewsQueueReader.run', exc_info=e, rlimitby=mhash)
                    if self.state.pass_on_exceptions:
                        raise

                if self.state.terminate:
                    retry = 0
                    break

            # retry == 0 indicates failure
            if retry == 0:
                continue


            try:
                # Let the queue know that the message is processed
                message.delete()
                if self.aws.ccg_queue:
                    ireduce = -1
                    iorig = len(result['paragraphs'])

                    while True:
                        strm = StringIO.StringIO()
                        # Add indent so easier to debug
                        json.dump(result, strm, indent=2)
                        data = strm.getvalue()
                        if len(data) >= 200*1024:
                            para = result['paragraphs']
                            ireduce = max([1, (len(para) * 200 * 1024)/ len(data)])
                            ireduce = min([len(para)-1, ireduce])
                            result['paragraphs'] = para[0:ireduce]
                        else:
                            break

                        if len(result['paragraphs']) <= 1:
                            break

                    if ireduce >= 0:
                        _logger.warning('Hash(%s) ccg paragraphs reduced from %d to %d' % (mhash, iorig, ireduce))
                    response = self.aws.ccg_queue.send_message(MessageAttributes=attributes, MessageBody=data)
                    _logger.debug('Sent hash(%s) -> ccg_queue(%s)', mhash, response['MessageId'])
            except Exception as e:
                _logger.exception('AwsNewsQueueReader.run', exc_info=e, rlimitby=mhash)
                if self.state.pass_on_exceptions:
                    raise