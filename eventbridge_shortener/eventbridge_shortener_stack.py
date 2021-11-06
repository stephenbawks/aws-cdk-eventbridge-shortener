from aws_cdk import (
    aws_s3 as s3,
    aws_events as events,
    aws_lambda as lambda_,
    aws_iam as iam,
    aws_apigatewayv2 as apigw,
    aws_apigatewayv2_integrations as apigw_integrations,
    aws_apigatewayv2_authorizers as apigw_authorizers,
    core
)

###############################################################################
#                        Documentation for the AWS CDK                        #
###############################################################################
# https://docs.aws.amazon.com/cdk/api/latest/python/index.html


class ShortenerStack(core.Stack):

    def __init__(self, scope: core.Construct, construct_id: str, applicationName: str, env: str, jwt_audience: list, jwt_issuer: str, http_default_stage: bool=False, ** kwargs) -> None:
        self.application_name = applicationName
        self.env = env
        self.jwt_audience = jwt_audience
        self.jwt_issuer = jwt_issuer
        self.create_http_default_stage = http_default_stage

        super().__init__(scope, construct_id, **kwargs)

        region = core.Aws.REGION
        account_id = core.Aws.ACCOUNT_ID

        app_name = f"{self.application_name}-{self.env}"

        bridge = events.EventBus(
            self, "eventBus",
            event_bus_name=f"{app_name}-event-bus"
        )

        bucket = s3.Bucket(
            self, "s3Bucket",
            versioned=True,
            removal_policy=core.RemovalPolicy.DESTROY)

        Fn = lambda_.Function(
            self, "shortenerLambda",
            handler="lambda_handler",
            code=lambda_.Code.asset("./src/shortener"),
            timeout=core.Duration.seconds(900),
            runtime=lambda_.Runtime.PYTHON_3_9,
            architecture
        )

        Fn.add_environment("BUCKET_NAME", bucket.bucket_name)
        Fn.add_environment("ENVIRONMENT", self.env)

        bucket.grant_read_write(Fn)

        http_api = apigw.HttpApi(self, "httpApi", create_default_stage=self.create_http_default_stage)

        http_id = http_api.api_id

        http_api.add_stage(
            "v1",
            auto_deploy=True,
            stage_name="v1"
        )

        apigw.HttpRoute(
            self, "httpRoute",
            http_api=http_api,
            route_key=apigw.HttpRouteKey.with_(
                method=apigw.HttpMethod.POST,
                path="/putevent"
            ),
            authorizer=apigw_authorizers.HttpJwtAuthorizer(
                authorizer_name=f"{app_name}-authorizer",
                identity_source=["$request.header.Authorization"],
                jwt_audience=self.jwt_audience,
                jwt_issuer=self.jwt_issuer
            ),
            integration=apigw_integrations.LambdaProxyIntegration(
                handler=Fn
            ),
        )

        lambda_.Permission(
            principal=[iam.ServicePrincipal("apigateway.amazonaws.com")],
            action="lambda:InvokeFunction",
            source_arn=f"arn:aws:execute-api:{region}:{account_id}:{http_id}/*/*/{Fn.function_name}"
        )

        # -------------------------------------------------------------------------------
        # Outputs
        # -------------------------------------------------------------------------------
        self.eventbus_arn_output = core.CfnOutput(
            self, "eventbus",
            value=bridge.event_bus_arn
        )

        self.http_url_output = core.CfnOutput(
            self, "shortener-api-url",
            value=http_api.url
        )

        self.http_url_output = core.CfnOutput(
            self, "shortener-api-id",
            value=http_api.api_id
        )

        self.lambda_arn_output = core.CfnOutput(
            self, "shortener-lambda-name",
            value=Fn.function_name
        )

        self.lambda_arn_output = core.CfnOutput(
            self, "shortener-lambda-arn",
            value=Fn.function_arn
        )

        self.s3_bucket_arn_output = core.CfnOutput(
            self, "shortener-s3-bucket",
            value=bucket.bucket_arn
        )
