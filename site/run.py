#!/usr/bin/env python
from app import app
import os
import logging
import watchtower

def init_log_handler(log_handler, log_level):
    log_handler.setLevel(log_level)

    # Make some attempt to comply with RFC5424
    log_handler.setFormatter(logging.Formatter(fmt='%(levelname)s %(asctime)s %(name)s %(process)d - %(message)s',
                                               datefmt='%Y-%m-%dT%H:%M:%S%z'))

# Setup logging
svc_name = os.path.splitext(os.path.basename(__file__))[0]
log_level=logging.INFO
root_logger = logging.getLogger('werkzeug')
root_logger.setLevel(log_level)

console_handler = None
log_handler = watchtower.CloudWatchLogHandler(log_group='core-nlp-services',
                                                  use_queues=False, # Does not shutdown if True
                                                  create_log_group=False)
init_log_handler(log_handler, log_level)
#root_logger.addHandler(log_handler)
app.logger.addHandler(log_handler)
logging.getLogger("werkzeug").addHandler(log_handler)

app.run(debug=True, host='0.0.0.0')
