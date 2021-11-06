import json
import pytest

from aws_cdk import core
from eventbridge_shortener.eventbridge_shortener_stack import EventbridgeShortenerStack


def get_template():
    app = core.App()
    EventbridgeShortenerStack(app, "eventbridge-shortener")
    return json.dumps(app.synth().get_stack("eventbridge-shortener").template)


def test_sqs_queue_created():
    assert("AWS::SQS::Queue" in get_template())


def test_sns_topic_created():
    assert("AWS::SNS::Topic" in get_template())
