import json

ICON_MAP = {
    "aws_instance": "https://raw.githubusercontent.com/awslabs/aws-icons-for-plantuml/main/dist/Compute/EC2.png",
    "aws_s3_bucket": "https://raw.githubusercontent.com/awslabs/aws-icons-for-plantuml/main/dist/Storage/S3.png",
    "aws_db_instance": "https://raw.githubusercontent.com/awslabs/aws-icons-for-plantuml/main/dist/Database/RDS.png",
    "aws_lambda_function": "https://raw.githubusercontent.com/awslabs/aws-icons-for-plantuml/main/dist/Compute/Lambda.png",
    "aws_vpc": "https://raw.githubusercontent.com/awslabs/aws-icons-for-plantuml/main/dist/Networking/VPC.png",
    "aws_subnet": "https://raw.githubusercontent.com/awslabs/aws-icons-for-plantuml/main/dist/Networking/PrivateSubnet.png",
    "aws_security_group": "https://raw.githubusercontent.com/awslabs/aws-icons-for-plantuml/main/dist/Security/SecurityGroup.png",
    "aws_iam_role": "https://raw.githubusercontent.com/awslabs/aws-icons-for-plantuml/main/dist/Security/IAMRole.png",
    "aws_lb": "https://raw.githubusercontent.com/awslabs/aws-icons-for-plantuml/main/dist/Networking/ElasticLoadBalancing.png",
    "aws_ecs_cluster": "https://raw.githubusercontent.com/awslabs/aws-icons-for-plantuml/main/dist/Containers/ECS.png",
    "aws_eks_cluster": "https://raw.githubusercontent.com/awslabs/aws-icons-for-plantuml/main/dist/Containers/EKS.png",
    "aws_sqs_queue": "https://raw.githubusercontent.com/awslabs/aws-icons-for-plantuml/main/dist/AppIntegration/SQS.png",
    "aws_sns_topic": "https://raw.githubusercontent.com/awslabs/aws-icons-for-plantuml/main/dist/AppIntegration/SNS.png",
    "aws_api_gateway_rest_api": "https://raw.githubusercontent.com/awslabs/aws-icons-for-plantuml/main/dist/Networking/APIGateway.png",
    "azurerm_resource_group": "https://raw.githubusercontent.com/benc-uk/azure-icon-collection/main/icons/Azure/Management/resourcegroup.svg",
    "azurerm_linux_virtual_machine": "https://raw.githubusercontent.com/benc-uk/azure-icon-collection/main/icons/Azure/Compute/virtualmachine.svg",
    "azurerm_windows_virtual_machine": "https://raw.githubusercontent.com/benc-uk/azure-icon-collection/main/icons/Azure/Compute/virtualmachine.svg",
    "azurerm_managed_disk": "https://raw.githubusercontent.com/benc-uk/azure-icon-collection/main/icons/Azure/Storage/manageddisk.svg",
    "azurerm_network_interface": "https://raw.githubusercontent.com/benc-uk/azure-icon-collection/main/icons/Azure/Networking/networkinterface.svg",
    "azurerm_network_security_group": "https://raw.githubusercontent.com/benc-uk/azure-icon-collection/main/icons/Azure/Networking/nsg.svg",
    "azurerm_virtual_network": "https://raw.githubusercontent.com/benc-uk/azure-icon-collection/main/icons/Azure/Networking/virtualnetwork.svg",
    "azurerm_storage_account": "https://raw.githubusercontent.com/benc-uk/azure-icon-collection/main/icons/Azure/Storage/storageaccount.svg",
    "azurerm_subnet": "https://raw.githubusercontent.com/benc-uk/azure-icon-collection/main/icons/Azure/Networking/subnet.svg",
    "default": "https://raw.githubusercontent.com/awslabs/aws-icons-for-plantuml/main/dist/General/Resource.png"
}

import os
import json
import google.generativeai as genai

def analyze_state_file(state_content):
    """Analyzes Terraform state file by pre-processing it and sending sanitized data to the Gemini API."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not set.")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
    generation_config = genai.types.GenerationConfig(max_output_tokens=8192)

    try:
        state_json = json.loads(state_content)
        resources = state_json.get('resources', [])
    except json.JSONDecodeError:
        raise ValueError("Invalid Terraform state file format.")

    sanitized_resources = []
    for resource in resources:
        sanitized_resources.append({
            "type": resource.get("type"),
            "name": resource.get("name"),
            "instances": [{
                "attributes": {
                    "id": instance.get("attributes", {}).get("id"),
                    "name": instance.get("attributes", {}).get("name")
                },
                "dependencies": instance.get("dependencies", [])
            } for instance in resource.get("instances", [])]
        })

    prompt = f"""Analyze the following sanitized Terraform resources and return a JSON object with 'nodes' and 'edges'.
    - Create a node for each resource with 'id', 'label', 'group', and 'image' from the ICON_MAP.
    - Create edges for dependencies between resources.
    - Ensure the output is a single, complete JSON object.

    ICON_MAP: {json.dumps(ICON_MAP, indent=2)}
    Sanitized Resources: {json.dumps(sanitized_resources, indent=2)}

    JSON Output:"""

    print(f"--- SANITIZED PROMPT SENT TO GEMINI ---\n{prompt[:1000]}...\n---")
    response = model.generate_content(prompt, generation_config=generation_config)

    cleaned_response = response.text.strip()
    print(f"--- RAW RESPONSE FROM GEMINI ---\n{cleaned_response}\n---")

    json_start = cleaned_response.find('{')
    json_end = cleaned_response.rfind('}') + 1

    if json_start != -1 and json_end > json_start:
        json_str = cleaned_response[json_start:json_end]
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            error_message = f"Failed to decode JSON: {e}. Malformed JSON string received: {json_str}"
            print(error_message)
            raise ValueError(error_message)
    else:
        error_message = f"Could not find a valid JSON object in the response. Full response: {cleaned_response}"
        print(error_message)
        raise ValueError(error_message)
