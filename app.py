#!/usr/bin/env python3

from aws_cdk import core

from eventbridge_shortener.eventbridge_shortener_stack import ShortenerStack


#------------------------------------------------------------------------------
#                     AWS CDK - EventBridge Shortener
#                         - Parameters -
#------------------------------------------------------------------------------

applicationName = "shortener"
env = "dev"
jwt_audience = ["DoStuff"]
jwt_issuer = "https://dev-61u57x8t.us.auth0.com/"
http_default_stage = True  #(optional: False by default)
domainName = "api.skwab.dev"

# add_stage_name_to_endpoint = True  #(optional: False by default)
# stage_name = "v1" #(optional: add_stage_name_to_endpoint required to be True)



#------------------------------------------------------------------------------
#                     AWS CDK - EventBridge Shortener
#                         - Stack -
#------------------------------------------------------------------------------
app = core.App()
ShortenerStack(
    app, "eventbridge-shortener", applicationName, env, jwt_audience, jwt_issuer, http_default_stage, domainName,
    #add_stage_name_to_endpoint, stage_name
)


app.synth()
