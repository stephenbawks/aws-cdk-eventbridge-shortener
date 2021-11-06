import setuptools


with open("README.md") as fp:
    long_description = fp.read()


setuptools.setup(
    name="eventbridge_shortener",
    version="0.0.1",

    description="A sample CDK Python app",
    long_description=long_description,
    long_description_content_type="text/markdown",

    author="author",

    package_dir={"": "eventbridge_shortener"},
    packages=setuptools.find_packages(where="eventbridge_shortener"),

    install_requires=[
        "aws-cdk.core",
        "aws-cdk.aws_iam",
        "aws-cdk.aws_s3",
        "aws-cdk.aws-events",
        "aws-cdk.aws-route53",
        "aws-cdk.aws-apigatewayv2",
        "aws-cdk.aws-apigatewayv2-authorizers",
        "aws-cdk.aws-apigatewayv2-integrations",
        "aws-cdk.aws-lambda",
    ],

    python_requires=">=3.6",

    classifiers=[
        "Development Status :: 4 - Beta",

        "Intended Audience :: Developers",

        "Programming Language :: JavaScript",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",

        "Topic :: Software Development :: Code Generators",
        "Topic :: Utilities",

        "Typing :: Typed",
    ],
)
