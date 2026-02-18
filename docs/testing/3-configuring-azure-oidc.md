# Configuring OIDC to an Azure Tenant

This document provides a quick overview of the process. You can also refer to the detailed [documentation from GitHub](https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-azure).

## Create an App Registration and Federated Identity Credential

> [!NOTE]
> This requires elevated permissions in your Azure tenant.

Start by navigating to **App Registrations** and create a new one with the name of your choice. The value of **Supported account types** will vary depending on your Azure setup, but for Launch, we use the **Single Tenant** option. It is not necessary to supply a redirect URL.



Create a new Identity Provider configuration within AWS IAM. Select the `OpenID Connect` option, and provide the following values:

> **Provider URL**: https://token.actions.githubusercontent.com
> **Audience**: sts.amazonaws.com

## Create a Policy to control access to AWS resources

In the IAM section, you will need to create a new Policy object that allows actions you will need for testing. Keep in mind that the identity that is creating your test resources is also creating an S3 bucket for state management and entitle it appropriately.

## Create a Role and establish Trust

Create a Role object and assign it to the policy you just created. Create a Trust Relationship for your role, replacing the `{templated}` items with values that correspond to your environment and IAM objects:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Federated": "arn:aws:iam::{your AWS account number}}:oidc-provider/token.actions.githubusercontent.com"
            },
            "Action": "sts:AssumeRoleWithWebIdentity",
            "Condition": {
                "StringEquals": {
                    "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
                },
                "StringLike": {
                    "token.actions.githubusercontent.com:sub": [
                        "repo:{test organization name}/test-repo-*:*",
                    ]
                }
            }
        }
    ]
}
```

## Configure GitHub Organization

Finally, the workflows are expecting a setting to configure which Role they assume when making the OIDC request. In GitHub, open the Organization's Settings page, navigate to the Secrets and Variables > Actions section. Create a new **Variable** (not a secret) as shown below:

> DEPLOY_ROLE_ARN = {ARN of the role you created earlier}

Ensure that you update the **Repository Access** setting to `All repositories`.

> [!TIP]
> AWS OIDC is now configured for your organization. To configure Azure, see the [next section](3-configuring-azure-oidc.md).
