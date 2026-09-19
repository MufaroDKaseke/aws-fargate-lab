# AWS Fargate Terraform Lab

A hands-on AWS lab for containerizing a FastAPI application and deploying it to **Amazon ECS Fargate using Terraform**. The project explores container orchestration, infrastructure as code, AWS networking, IAM, ECR, CloudWatch, and serverless container deployment.


## Prerequisites

* AWS account
* AWS CLI
* Docker
* Terraform
* Python
* An AWS IAM identity with permissions to create the required resources

Verify the tools:

```bash
aws sts get-caller-identity
terraform version
docker version
```

---

# 1. Create the Application

The project uses a small FastAPI application with a few endpoints for testing:

```text
/
 /health
 /compute
```

The application listens on:

```text
8000
```

Project structure:

```text
aws-fargate-lab/
├── app/
│   ├── main.py
│   └── Dockerfile
├── main.tf
├── variables.tf
└── outputs.tf
```

---

# 2. Build and Test the Docker Container Locally

Build the image:

```bash
docker build -t fargate-lab ./app
```

Run it locally:

```bash
docker run --rm -p 8000:8000 fargate-lab
```

The application can then be tested at:

```text
http://localhost:8000
```

For example:

```text
http://localhost:8000/health
```

Stop the container with:

```text
Ctrl + C
```

---

# 3. Configure Terraform

Terraform was used to provision the AWS infrastructure rather than creating resources manually through the AWS Console.

The AWS provider was configured with the desired AWS region.

For this experiment:

```text
Region: af-south-1
```

The existing default VPC was used instead of creating a new VPC.

Terraform discovers the default VPC and its subnets using data sources.

---

# 4. Initialize Terraform

Initialize the project:

```bash
terraform init
```

Format the Terraform configuration:

```bash
terraform fmt
```

Validate the configuration:

```bash
terraform validate
```

Review the resources Terraform intends to create:

```bash
terraform plan
```

---

# 5. Create the ECR Repository

Terraform creates an Amazon ECR repository for the Docker image.

Apply the infrastructure:

```bash
terraform apply
```

Confirm the deployment by entering:

```text
yes
```

The ECR repository URL can be retrieved with:

```bash
terraform output
```

The repository URL will look similar to:

```text
ACCOUNT_ID.dkr.ecr.af-south-1.amazonaws.com/fargate-lab
```

---

# 6. Authenticate Docker with ECR

Authenticate Docker against Amazon ECR:

```bash
aws ecr get-login-password \
  --region af-south-1 |
docker login \
  --username AWS \
  --password-stdin ACCOUNT_ID.dkr.ecr.af-south-1.amazonaws.com
```

A successful login returns:

```text
Login Succeeded
```

---

# 7. Tag the Docker Image

The locally built image needs to be tagged with the ECR repository URL.

```bash
docker tag fargate-lab:latest \
  ACCOUNT_ID.dkr.ecr.af-south-1.amazonaws.com/fargate-lab:latest
```

---

# 8. Push the Image to ECR

Push the image:

```bash
docker push \
  ACCOUNT_ID.dkr.ecr.af-south-1.amazonaws.com/fargate-lab:latest
```

At this point the container image is stored in Amazon ECR and can be pulled by ECS.

---

# 9. ECS Infrastructure

Terraform provisions the following ECS components:

* ECS cluster
* Fargate task definition
* ECS service
* IAM execution role
* Security group
* CloudWatch log group

The task uses:

```text
Launch type: FARGATE
CPU:         256
Memory:      512 MB
```

The ECS task uses `awsvpc` networking and is assigned a public IP for this temporary lab.

---

# 10. Deploy the Container

After the image has been pushed to ECR, Terraform creates the ECS service:

```bash
terraform apply
```

ECS starts the Fargate task and pulls the Docker image from ECR.

Check the running tasks:

```bash
aws ecs list-tasks \
  --cluster fargate-lab \
  --region af-south-1
```

---

# 11. Find the Public IP

First retrieve the task details:

```bash
aws ecs describe-tasks \
  --cluster fargate-lab \
  --tasks TASK_ARN \
  --region af-south-1
```

Find the Elastic Network Interface (ENI) associated with the task.

Then retrieve the network interface:

```bash
aws ec2 describe-network-interfaces \
  --network-interface-ids ENI_ID \
  --region af-south-1
```

The response contains the public IP assigned to the Fargate task.

The application can then be accessed through:

```text
http://PUBLIC_IP:8000
```

For example:

```text
http://PUBLIC_IP:8000/health
```

---

# 12. View Container Logs

The application sends its container logs to CloudWatch.

Logs can be followed from the CLI:

```bash
aws logs tail /ecs/fargate-lab \
  --follow \
  --region af-south-1
```

Requests made to the application can then be observed in the logs.

---

# 13. Experiment With the Deployment

Because the infrastructure is managed through Terraform, resources can be modified and redeployed by changing the Terraform configuration.

For example, the Fargate task can be changed from:

```text
0.25 vCPU / 512 MB
```

to:

```text
0.5 vCPU / 1 GB
```

Then apply the change:

```bash
terraform apply
```

This provides an opportunity to observe ECS deployments, task replacement, resource allocation, and CloudWatch logging.

---

# 14. Destroy the Infrastructure

Because this is a disposable lab, the infrastructure should be destroyed after testing:

```bash
terraform destroy
```

Confirm with:

```text
yes
```

This removes the AWS resources managed by Terraform.

---

# Important: ECR Repository Cleanup

One issue encountered during cleanup was that the ECR repository contained the Docker image that had been pushed during deployment.

A normal:

```bash
terraform destroy
```

can fail when Terraform attempts to delete a non-empty ECR repository.

For this disposable lab, the repository can be configured with:

```hcl
resource "aws_ecr_repository" "app" {
  name         = "fargate-lab"
  force_delete = true
}
```

However, if the infrastructure was already created **without** `force_delete = true`, simply running `terraform destroy` will not apply this new configuration before attempting the deletion.

The solution is to first target the ECR repository with Terraform:

```bash
terraform apply -target=aws_ecr_repository.app
```

This updates the ECR repository configuration to enable:

```text
force_delete = true
```

After the targeted apply completes, run the normal destroy:

```bash
terraform destroy
```

Terraform can then delete the ECR repository and its images as part of the cleanup.

### Cleanup sequence

If the repository is already deployed and contains an image:

```bash
# 1. Add force_delete = true to the ECR resource

# 2. Apply only the ECR change
terraform apply -target=aws_ecr_repository.app

# 3. Destroy the complete lab
terraform destroy
```

> **Note:** `-target` should generally not be used as a normal Terraform workflow. It is being used here intentionally to update the disposable ECR resource before destroying the rest of the lab.


# Cost Considerations

The infrastructure was designed as a short-lived experiment.

The main potentially billable resources include:

* ECS Fargate compute
* Public IPv4 address
* ECR storage
* CloudWatch logs

The experiment intentionally avoids resources such as:

* NAT Gateway
* Application Load Balancer
* RDS
* Dedicated VPC infrastructure

After testing, always run:

```bash
terraform destroy
```

and verify that no unexpected resources remain in the AWS account.

---

# What This Lab Demonstrates

This exercise provides hands-on experience with:

* Docker containerization
* Amazon ECR
* Amazon ECS
* AWS Fargate
* Terraform
* IAM
* VPC networking
* Security groups
* Public IP networking
* CloudWatch Logs
* Infrastructure lifecycle management
* AWS resource cleanup

## Next Step

The next stage is to automate the deployment with **GitHub Actions**, so that pushing a change to the repository can automatically:

```text
Git Push
   ↓
GitHub Actions
   ↓
Docker Build
   ↓
Push to ECR
   ↓
Deploy to ECS Fargate
```
