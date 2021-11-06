import json
import pytest

from aws_cdk import core
from eventbridge_shortener.eventbridge_shortener_stack import EventbridgeShortenerStack


def get_template():
    app = core.App()
    EventbridgeShortenerStack(app, "eventbridge-shortener")
    return json.dumps(app.synth().get_stack("eventbridge-shortener").template)


def test_eventbridge_bus_created():
    assert("AWS::Events::EventBus" in get_template())

def test_s3_bucket_created():
    assert("AWS::S3::Bucket" in get_template())

def test_lambda_function_created():
    assert("AWS::Lambda::Function" in get_template())

def test_http_api_created():
    assert("AWS::ApiGatewayV2::Api" in get_template())

