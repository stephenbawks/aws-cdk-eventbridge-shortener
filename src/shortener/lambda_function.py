import os
import json
import datetime
import uuid
import boto3
from botocore.exceptions import ClientError
from aws_lambda_powertools import Tracer, Logger, Metrics
from aws_lambda_powertools.metrics import MetricUnit

# Grabbing Environmental Variables on the Lambda Function
# https://docs.aws.amazon.com/lambda/latest/dg/configuration-envvars.html#configuration-envvars-retrieve
REGION = os.environ['AWS_REGION']
ENVIRONMENT = os.environ['ENVIRONMENT']
BUCKET_NAME = os.environ['SHORTENER_BUCKET_NAME']
URL_EXP_TIME = os.environ['URL_EXP_TIME']

#------------------------------------------------------------------------------
#                     Documentation for the Lambda Function                   
#------------------------------------------------------------------------------

# Inside Lambda - What is inside AWS lambda? Are there things inside there? Let's find out!
# https://insidelambda.com/

# Create boto3 Events Client
# https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/events.html

# Lambda Defined/Reserverd runtime environment variables
# https://docs.aws.amazon.com/lambda/latest/dg/configuration-envvars.html#configuration-envvars-runtime

# Lambda Context - Python
# https://docs.aws.amazon.com/lambda/latest/dg/python-context.html

# Lambda HTTP API Payload
# https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-develop-integrations-lambda.html

# Amazon EventBridge Events
# https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-events.html



# Tracer and Logger are part of AWS Lambda Powertools Python
# https://awslabs.github.io/aws-lambda-powertools-python/latest/
tracer = Tracer()  # Sets service via env var
logger = Logger()
metrics = Metrics()


@tracer.capture_method(capture_response=False)
def extract_data(event: dict):
    # Extract the body from event
    if 'body' in event:
        data = event['body']
        try:
            data = json.loads(data)
            return data
        except ValueError as e:
            return False


@tracer.capture_method(capture_response=False)
def get_eventbridge_put_event_size(eventbridge_event: dict) -> int:
    """Calculating the size of the event in bytes
    https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-putevent-size.html

    Args:
        eventbridge_event (dict): Event to calculate size of in

    Returns:
        size (int): Size of the event in bytes
    """
    size = 0
    if eventbridge_event.get("time") is not None:
        size += 14
    size += len(eventbridge_event.get("source").encode("utf-8"))
    size += len(eventbridge_event.get("detail-type").encode("utf-8"))
    size += len(json.dumps(eventbridge_event.get("detail")).encode("utf-8"))
    for resource in eventbridge_event.get("resources", []):
        if resource:
            size += len(resource.encode("utf-8"))

    tracer.put_annotation(key="EventSize", value=size)

    return size


@tracer.capture_method(capture_response=False)
def put_event_size_metrics(event_size: int, event_type: str, put_event_id: str) -> None:
    """CloudWatch embedded metric format enables you to ingest complex high-cardinality application
    data in the form of logs and to generate actionable metrics from them
    https://docs.aws.amazon.com/AmazonCloudWatch/latest/APIReference/API_MetricDatum.html

    Args:
        event_size (int): Size of the event
        event_type (str): A type of Event
        put_event_id (str): Put Event ID for additional metadata tracking

    Returns:
        None
    """
    metrics.add_metric(name="Size", unit=MetricUnit.Bytes, value=event_size)
    metrics.add_metric(name="Count", unit=MetricUnit.Count, value=1)
    metrics.add_dimension(name="EventType", value=event_type)
    metrics.add_metadata(key="PutEventId", value=put_event_id)
    return None


@tracer.capture_method(capture_response=False)
def add_event_metadata(event: dict, trucated_event: bool, presigned_url: str = None, event_data_size: int = None, bucket_name: str = None, object_path: str = None) -> dict:
    """Add metadata to the event to be sent to EventBridge

    Args:
        event (dict): Event to add metadata to
        trucated_event (bool): True or False if the event was trucated
        presigned_url (str): Optional presigned URL to the object
        event_data_size (int): Optional size of the Data in the event
        bucket_name (str): Optional bucket name
        obejct_path (str): Optional object path

    Returns:
        event (dict): Event with metadata added and data field removed
    """

    if trucated_event:
        add_key = {
            "event_trucation":
            {
                "event_truncated": True,
                "event_body_url": presigned_url,
                "event_data_size": event_data_size,
                "event_object_bucket": bucket_name,
                "event_object_key": object_path
            }
        }
        # Adding metadata to the event
        event["detail"]["metadata"].update(add_key)

        # Removing the data field from the event
        if 'data' in event["detail"]:
            del event["detail"]["data"]

        tracer.put_annotation(key="EventTruncated", value="True")

    else:
        add_key = {
            "event_trucation":
            {
                "event_truncated": False,
            }
        }
        # Adding metadata to the event
        event["detail"]["metadata"].update(add_key)

        tracer.put_annotation(key="EventTruncated", value="False")
    return event


@tracer.capture_method(capture_response=False)
def create_presigned_url(bucket_name: str, file_name: str, object_path: str, file_content: str, expiration: int) -> str:
    """Generate a presigned URL to share an S3 object
    https://boto3.amazonaws.com/v1/documentation/api/latest/guide/s3-presigned-urls.html

    Args:
        bucket_name (str): Name of the bucket
        object_path (str): Path to the file
        file_content (str): Content of the file
        expiration (str): (Optional) Time in seconds for the presigned URL to remain valid

    Returns:
        Presigned URL as string. If error, returns None.
    """

    s3 = boto3.client('s3')

    try:
        file_path = "/tmp/" + file_name
        with open(file_path, 'w') as f:
            f.write(file_content)

        s3.upload_file(
            file_path,
            bucket_name,
            object_path,
            ExtraArgs={'ContentType': 'text/csv'}
        )

        response = s3.generate_presigned_url(
            ClientMethod="get_object",
            ExpiresIn=expiration,
            HttpMethod="GET",
            Params={"Bucket": bucket_name, "Key": object_path}
        )

        tracer.put_annotation(key="CreatePreSignedUrl", value="SUCCESS")
        tracer.put_metadata(key="object_path", value=object_path)

    except ClientError as e:
        logger.error(e)
        return None

    # The response contains the presigned URL
    return response


@metrics.log_metrics(capture_cold_start_metric=True)
@logger.inject_lambda_context(log_event=False)
@tracer.capture_method(capture_response=False)
def lambda_handler(event, context):

    # Extract the body from event
    event_data = extract_data(event)
    if event_data is False:
        response = {"statusCode": 400, "message": "Invalid JSON in body"}
        return json.dumps(response)

    # Getting size of the event in bytes and check if it is over the limit
    # initial_event_size = get_eventbridge_put_event_size(event_data)
    # 256000 - 50 for minimum metadata size (technically 47 but rounding up for safety)
    if get_eventbridge_put_event_size(event_data) > 255950:
        print("Event Size Larger than EventBrige Event Payload Limit")

        # Calculating the size of the event in bytes for the data field that will be truncated
        truncated_event_data = event_data["detail"].get("data")
        truncated_data_size = len(json.dumps(event_data).encode("utf-8"))

        # Create File Name using Context Request ID
        generate_uuid_filename = str(uuid.uuid4())
        generate_file_name = f"{generate_uuid_filename}.json"
        current_date = datetime.datetime.today()
        file_object_path = f"{str(current_date.year)}/{str(current_date.month)}/{str(current_date.day)}/{generate_file_name}"

        # Generating a presigned URL for the file that will contained the truncated event data
        presigned_url = create_presigned_url(bucket_name=BUCKET_NAME, file_name=generate_file_name,
                                             object_path=file_object_path, file_content=str(truncated_event_data),
                                             expiration=URL_EXP_TIME)

        # Add truncated metadata to the event and remove the data field
        event_with_metadata = add_event_metadata(event_data, trucated_event=True, presigned_url=presigned_url,
                                                 event_data_size=truncated_data_size, bucket_name=BUCKET_NAME, object_path=file_object_path)

        # Calculating the size of the event after adding metadata
        final_event_size = get_eventbridge_put_event_size(event_with_metadata)

        put_event_size_metrics(event_size=final_event_size, event_type=event_data.get(
            "detail-type"), put_event_id=context.aws_request_id)

        response = {"statusCode": 200,
                    "headers": {"Content-Type": "application/json"},
                    "event": {
                        "event_trucated": True,
                        "presigned_url": presigned_url,
                        "event_size": final_event_size
                    }
                    }
        return json.dumps(response)
    else:
        # Add truncated metadata to the event
        event_with_metadata = add_event_metadata(
            event_data, trucated_event=False)

        # Calculating the size of the event after adding metadata
        final_event_size = get_eventbridge_put_event_size(event_with_metadata)

        # Put Cloudwatch Logs Metrics
        put_event_size_metrics(event_size=final_event_size, event_type=event_data.get(
            "detail-type"), put_event_id=context.aws_request_id)

        response = {"statusCode": 200,
                    "headers": {"Content-Type": "application/json"},
                    "event": {
                        "event_trucated": False,
                        "event_size": final_event_size
                    }
                    }
        return json.dumps(response)
