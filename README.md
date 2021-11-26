# AWS Eventbridge Event API Shortener
- [AWS Eventbridge Event API Shortener](#aws-eventbridge-event-api-shortener)
  - [Purpose](#purpose)
  - [Architecture Diagram](#architecture-diagram)
  - [Event Example](#event-example)
    - [Example Event](#example-event)

## Purpose

This pattern in CDK offers a boilerlate to generate an AWS HTTP API endpoint with a `POST` endpoint of `/putevent`. That endpoint is a direct integration to a Lambda funnction provided in Python.  The Lambda functions primary purpose is to determine if the incoming event is over the limit of 256kb that is imposed for events being put onto an AWS Eventbridge bus.

If the size of the event is over that limit, the function will truncate the data portion of the event, take that data and put into a `.json` file that it will then upload that to an S3 bucket.  The Lambda then will create a pre-signed URL that has a default lifetime of 3600 seconds, and re-insert that data back into the event message so that downstream consumers of that message know that the message was truncated and where it can go and get that data from.

If the message is lower than the 256kb size limit, the function will truncate the message but it will still add the following data points so that downstream consumers know that the message was not over the limit.  Example below.

Learn more about this pattern at Serverless Land Patterns: https://serverlessland.com/patterns/apigw-lambda-cdk

Important: this application uses various AWS services and there are costs associated with these services after the Free Tier usage - please see the AWS Pricing page for details. You are responsible for any AWS costs incurred. No warranty is implied in this example.


## Architecture Diagram

Diagram Incoming...


## Event Example

There are occasions where you might want to send data to Eventbridge that is over the Eventbridge limit of 256kb in size.  Below is an example of an event structure and how this CDK project will handle that structure.

### Example Event

```json
{
    "source": "WidgitsService",
    "detail-type": "NewCustomerOpportunity",
    "detail": {
        "metadata": {
            "service": "myAwesomeSerice",
            "type": "ExampleEventType",
            "status": "submitted"
        },
        "data": {
            "AccountId": "6417c247082c4543yrty66a2516f607",
            "name": {
                "firstName": "Dudley",
                "lastName": "Bose"
            },
            "emailAddress":{
                    "emailUsageType": "Work",
                    "emailAddress": "sample@email.com",
            },
            "dataToLarge": {
                "data": "noufyfyrdvbzwaljzcjghcfscalohtsq...***VERY LONG MESSAGE DATA HERE OVER 256KB***"
            }
        }
    }
}
```

You can see in the example above there is a field that is abbreciavated here in this example just to show so not to overwhelm this documentation! So for the sake of pretending, imagine that field contains a very large set of data that pushes the measured size over 256kb.  What happens in that scenario is as follows.

The Lambda will strip out all of the information from the `data` field (this can obviously be customized to make it work with your event type).  The Lambda will then create a file in a S3 bucket using the current date of `YYYY/MM/DD` and it will generate a UUID to use for a file name.  The resulting path will be s3://`YYYY/MM/DD/UUID.json`.

Once that file is saved to S3 it will then generate a pre-signed URL with a timeout of 3600 seconds. It will then take the event and alter its structure to look like this.

