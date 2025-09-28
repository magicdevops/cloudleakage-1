# AWS IAM Permissions for CloudLeakage

## 🔑 Required IAM Permissions

CloudLeakage requires specific AWS IAM permissions to function properly. The application validates credentials and accesses AWS services for cost optimization analysis.

## 📋 Minimum Required Permissions

### Basic Account Access (Required)
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "sts:GetCallerIdentity"
            ],
            "Resource": "*"
        }
    ]
}
```

### Cost Explorer Access (Recommended)
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ce:GetCostAndUsage",
                "ce:GetUsageReport",
                "ce:GetReservationCoverage",
                "ce:GetReservationPurchaseRecommendation",
                "ce:GetReservationUtilization",
                "ce:GetDimensionValues",
                "ce:GetMetricData",
                "ce:ListCostCategoryDefinitions",
                "ce:GetRightsizingRecommendation"
            ],
            "Resource": "*"
        }
    ]
}
```

### Billing Access (Optional)
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "budgets:ViewBudget",
                "budgets:DescribeBudgets",
                "budgets:DescribeBudgetPerformanceHistory"
            ],
            "Resource": "*"
        }
    ]
}
```

## 🛡️ Complete IAM Policy

### CloudLeakage Full Access Policy
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "BasicAccountAccess",
            "Effect": "Allow",
            "Action": [
                "sts:GetCallerIdentity"
            ],
            "Resource": "*"
        },
        {
            "Sid": "CostExplorerAccess",
            "Effect": "Allow",
            "Action": [
                "ce:GetCostAndUsage",
                "ce:GetUsageReport",
                "ce:GetReservationCoverage",
                "ce:GetReservationPurchaseRecommendation",
                "ce:GetReservationUtilization",
                "ce:GetDimensionValues",
                "ce:GetMetricData",
                "ce:ListCostCategoryDefinitions",
                "ce:GetRightsizingRecommendation"
            ],
            "Resource": "*"
        },
        {
            "Sid": "BillingAccess",
            "Effect": "Allow",
            "Action": [
                "budgets:ViewBudget",
                "budgets:DescribeBudgets",
                "budgets:DescribeBudgetPerformanceHistory"
            ],
            "Resource": "*"
        },
        {
            "Sid": "ResourceOptimizationAccess",
            "Effect": "Allow",
            "Action": [
                "ec2:DescribeInstances",
                "ec2:DescribeInstanceTypes",
                "ec2:DescribeReservedInstances",
                "ec2:DescribeSpotPriceHistory",
                "rds:DescribeDBInstances",
                "rds:DescribeReservedDBInstances"
            ],
            "Resource": "*"
        }
    ]
}
```

## 🏗️ IAM Setup Instructions

### Option 1: Create IAM User (Recommended)

1. **Create IAM User**:
   ```bash
   aws iam create-user --user-name cloudleakage-user
   ```

2. **Attach Policy**:
   ```bash
   # Create the policy first
   aws iam create-policy \
     --policy-name CloudLeakageAccess \
     --policy-document file://cloudleakage-policy.json
   
   # Attach to user
   aws iam attach-user-policy \
     --user-name cloudleakage-user \
     --policy-arn arn:aws:iam::ACCOUNT-ID:policy/CloudLeakageAccess
   ```

3. **Create Access Keys**:
   ```bash
   aws iam create-access-key --user-name cloudleakage-user
   ```

### Option 2: Use IAM Role (For EC2/ECS)

1. **Create Trust Policy** (`trust-policy.json`):
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Principal": {
           "Service": "ec2.amazonaws.com"
         },
         "Action": "sts:AssumeRole"
       }
     ]
   }
   ```

2. **Create Role**:
   ```bash
   aws iam create-role \
     --role-name CloudLeakageRole \
     --assume-role-policy-document file://trust-policy.json
   ```

3. **Attach Policy**:
   ```bash
   aws iam attach-role-policy \
     --role-name CloudLeakageRole \
     --policy-arn arn:aws:iam::ACCOUNT-ID:policy/CloudLeakageAccess
   ```

## 🚨 Permission Levels & Behavior

### Level 1: Basic Access Only
- **Permissions**: `sts:GetCallerIdentity`
- **Behavior**: Account can be added but cost data sync will be limited
- **Status**: ⚠️ Limited functionality

### Level 2: Cost Explorer Access
- **Permissions**: Basic + Cost Explorer
- **Behavior**: Full cost analysis and optimization recommendations
- **Status**: ✅ Recommended

### Level 3: Full Access
- **Permissions**: All permissions above + Billing + Resource access
- **Behavior**: Complete cost optimization with resource recommendations
- **Status**: 🚀 Optimal

## 🔧 Troubleshooting Permission Issues

### Common Errors and Solutions

1. **AccessDeniedException**
   ```
   Error: AWS Error: AccessDeniedException
   ```
   **Solution**: Add Cost Explorer permissions to IAM user/role

2. **UnauthorizedOperation**
   ```
   Error: AWS Error: UnauthorizedOperation
   ```
   **Solution**: Verify IAM permissions are attached correctly

3. **InvalidUserID.NotFound**
   ```
   Error: AWS Error: InvalidUserID.NotFound
   ```
   **Solution**: Check if IAM user exists and access keys are valid

### Verification Commands

```bash
# Test basic access
aws sts get-caller-identity

# Test Cost Explorer access
aws ce get-cost-and-usage \
  --time-period Start=2024-01-01,End=2024-01-02 \
  --granularity DAILY \
  --metrics BlendedCost

# Test billing access
aws budgets describe-budgets --account-id YOUR-ACCOUNT-ID
```

## 📊 Permission Impact on Features

| Feature | Required Permission | Impact if Missing |
|---------|-------------------|-------------------|
| Account Validation | `sts:GetCallerIdentity` | ❌ Cannot add account |
| Cost Analysis | `ce:GetCostAndUsage` | ⚠️ Limited cost data |
| Budget Tracking | `budgets:DescribeBudgets` | ⚠️ No budget insights |
| Resource Optimization | `ec2:DescribeInstances` | ⚠️ No resource recommendations |
| Reservation Analysis | `ce:GetReservationUtilization` | ⚠️ No RI recommendations |

## 🔒 Security Best Practices

1. **Principle of Least Privilege**: Only grant necessary permissions
2. **Regular Rotation**: Rotate access keys every 90 days
3. **MFA**: Enable MFA for IAM users when possible
4. **Monitoring**: Monitor CloudTrail for API usage
5. **Separate Accounts**: Use dedicated AWS account for cost analysis

## 📝 Notes

- Cost Explorer API is only available in `us-east-1` region
- Some permissions may take a few minutes to propagate
- CloudLeakage gracefully handles missing permissions and continues with available functionality
- Regular IAM policy reviews are recommended for security compliance
