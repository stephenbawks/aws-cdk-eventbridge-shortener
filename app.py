#!/usr/bin/env python3

from aws_cdk import core

from eventbridge_shortener.eventbridge_shortener_stack import ShortenerStack

applicationName = "shortener"
env = "dev"
jwt_audience = ["shortener"]
jwt_issuer = "https://dev-61u57x8t.us.auth0.com/"

app = core.App()
ShortenerStack(app, "eventbridge-shortener", applicationName,
               env, jwt_audience, jwt_issuer)


app.synth()
