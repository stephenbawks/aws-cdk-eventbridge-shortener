import json
from aws_cdk import (
    aws_s3 as s3,
    aws_events as events,
    aws_lambda as lambda_,
    aws_iam as iam,
    aws_apigatewayv2 as apigw,
    aws_logs as logs,
    aws_certificatemanager as acm,
    aws_apigatewayv2_integrations as apigw_integrations,
    aws_apigatewayv2_authorizers as apigw_authorizers,
    core
)

# ------------------------------------------------------------------------------
#                        Documentation for the AWS CDK                        #
# ------------------------------------------------------------------------------
# https://docs.aws.amazon.com/cdk/api/latest/python/index.html


class ShortenerStack(core.Stack):

    def __init__(
        self, scope: core.Construct, construct_id: str, applicationName: str, env: str,
        jwt_audience: list, jwt_issuer: str, http_default_stage: bool = False,
        domainName: str = None, add_stage_name_to_endpoint=False, stage_name=None,
        ** kwargs
    ) -> None:

        self.application_name = applicationName
        self.env = env
        self.jwt_audience = jwt_audience
        self.jwt_issuer = jwt_issuer
        self.create_http_default_stage = http_default_stage
        self.add_stage_name_to_endpoint = add_stage_name_to_endpoint
        self.stage_name = stage_name
        self.domain_name = domainName

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
            removal_policy=core.RemovalPolicy.DESTROY
        )

        Fn = lambda_.Function(
            self, "shortenerLambda",
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.asset("./src/shortener"),
            timeout=core.Duration.seconds(900),
            runtime=lambda_.Runtime.PYTHON_3_9,
            tracing=lambda_.Tracing.ACTIVE,
            layers=[
                lambda_.LayerVersion.from_layer_version_arn(
                    self, "awsPowerToolsLambdaLayer",
                    f"arn:aws:lambda:{region}:017000801446:layer:AWSLambdaPowertoolsPython:3"
                )
            ]
        )

        Fn.add_environment("SHORTENER_BUCKET_NAME", bucket.bucket_name)
        Fn.add_environment("ENVIRONMENT", self.env)
        Fn.add_environment("POWERTOOLS_METRICS_NAMESPACE", "Shortener")
        Fn.add_environment("POWERTOOLS_SERVICE_NAME", "event-service")
        Fn.add_environment("EVENTBRIDGE_BUS_NAME", bridge.event_bus_name)

        bucket.grant_read_write(Fn)

        if self.domain_name is not None:
            cert = acm.Certificate(
                self, "certificate",
                domain_name=self.domain_name,
                subject_alternative_names=[f"*.{self.domain_name}"],
                validation=acm.CertificateValidation.from_dns()
            )

        dn = apigw.DomainName(self, "domainName",
                              domain_name=self.domain_name,
                              certificate=acm.Certificate.from_certificate_arn(
                                  self, "cert", cert.certificate_arn)
                              )

        http_api = apigw.HttpApi(self, "httpApi",
                                 api_name=f"{app_name}-api",
                                 create_default_stage=self.create_http_default_stage
                                 )

        apigw.ApiMapping(self, "apiMapping",
                         domain_name=dn,
                         api=http_api
                         )

        httpLogGroup = logs.LogGroup(
            self, "httpLogs",
            # https://docs.aws.amazon.com/cdk/api/latest/python/aws_cdk.aws_logs/RetentionDays.html#aws_cdk.aws_logs.RetentionDays
            retention=logs.RetentionDays.TWO_WEEKS,
            log_group_name=f"/aws/http/{app_name}-api"
        )

        log_settings = apigw.CfnStage.AccessLogSettingsProperty(
            destination_arn=httpLogGroup.log_group_arn,
            format="requestId:$context.requestId,ip:$context.identity.sourceIp,requestTime:$context.requestTime,httpMethod:$context.httpMethod,routeKey:$context.routeKey,status:$context.status,protocol:$context.protocol,responseLength:$context.responseLength,integrationRequestId:$context.integration.requestId,integrationStatus:$context.integration.integrationStatus,integrationLatency:$context.integrationLatency,integrationErrorMessage:$context.integrationErrorMessage,errorMessageString:$context.error.message,authorizerError:$context.authorizer.error"
        )

        apigw.CfnStageProps(
            api_id=http_api.http_api_id,
            auto_deploy=True,
            stage_name=http_api.default_stage,
            access_log_settings=(log_settings)
        )

        if self.add_stage_name_to_endpoint and self.stage_name is not None:
            http_api.add_stage(
                "addStage",
                auto_deploy=True,
                stage_name=self.stage_name
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
            source_arn=f"arn:aws:execute-api:{region}:{account_id}:{http_api.api_id}/*/*/{Fn.function_name}"
        )

        iam.Policy(
            self, "policy",
            roles=[Fn.role],
            policy_name=f"policy-{app_name}-put-events",
            statements=[
                iam.PolicyStatement(
                    sid="AllowPutEvents",
                    actions=["events:PutEvents"],
                    effect=iam.Effect.ALLOW,
                    resources=[bridge.event_bus_arn]
                )
            ]
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

        self.http_url_output = core.CfnOutput(
            self, "shortener-api-default-stage",
            value=http_api.default_stage.stage_name
        )

        self.http_url_output = core.CfnOutput(
            self, "shortener-api-log-arn",
            value=httpLogGroup.log_group_arn
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
