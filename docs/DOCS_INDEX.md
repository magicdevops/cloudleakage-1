# 📚 CloudLeakage Documentation Index

This directory contains all documentation files for the CloudLeakage project.

## 📁 Documentation Structure

### 🚀 **Setup & Installation**
- **`README.md`** - Main project overview and quick start guide
- **`DOCKER_POSTGRESQL_SETUP.md`** - Complete Docker and PostgreSQL setup guide
- **`database_setup.md`** - Database configuration and setup instructions

### 🏗️ **Architecture & Design**
- **`database_migration_strategy.md`** - Database migration and scaling strategies
- **`production_checklist.md`** - Production deployment checklist

### 🔧 **Development & Configuration**
- **`aws_iam_permissions.md`** - AWS IAM permissions and security setup
- **`polling_and_caching_readme.md`** - Polling mechanisms and caching strategies

### 🤖 **Advanced Features**
- **`CLOUDWATCH_RAG_README.md`** - CloudWatch RAG (Retrieval-Augmented Generation) system

### 💾 **Database Schema**
- **`cloudwatch_rag_schema.sql`** - Database schema for CloudWatch RAG features

## 📖 **Reading Guide**

### **New Users**
1. Start with **`README.md`** for project overview
2. Follow **`DOCKER_POSTGRESQL_SETUP.md`** for setup
3. Review **`database_setup.md`** for database configuration

### **Developers**
1. Check **`production_checklist.md`** for deployment guidelines
2. Review **`database_migration_strategy.md`** for scaling plans
3. Understand **`polling_and_caching_readme.md`** for system behavior

### **Advanced Features**
1. Explore **`CLOUDWATCH_RAG_README.md`** for AI-powered features
2. Review **`cloudwatch_rag_schema.sql`** for database structure

## 🔍 **File Descriptions**

| File | Description |
|------|-------------|
| `README.md` | Main project documentation and quick start |
| `DOCKER_POSTGRESQL_SETUP.md` | Docker, PostgreSQL, and deployment guide |
| `database_setup.md` | Database configuration and setup |
| `database_migration_strategy.md` | Database scaling and migration strategies |
| `production_checklist.md` | Production deployment checklist |
| `aws_iam_permissions.md` | AWS permissions and security configuration |
| `polling_and_caching_readme.md` | System polling and caching mechanisms |
| `CLOUDWATCH_RAG_README.md` | CloudWatch RAG AI system documentation |
| `cloudwatch_rag_schema.sql` | Database schema definitions |

## 🚀 **Quick Access**

### **Setup Commands**
```bash
# Quick Docker setup
./setup_docker.sh

# Traditional setup
./setup_and_run.sh
```

### **Database Management**
```bash
# Access PostgreSQL
psql -h localhost -p 5432 -U app_user -d cloudleakage

# View database logs
docker-compose logs postgres
```

### **Application URLs**
- **Main App**: http://localhost:5000
- **Dashboard**: http://localhost:5000/dashboard
- **EC2 Dashboard**: http://localhost:5000/ec2
- **API**: http://localhost:5000/integration

## 📝 **Documentation Standards**

All documentation follows these standards:
- Clear section headers with emojis
- Code examples with syntax highlighting
- Step-by-step instructions
- Troubleshooting sections
- Cross-references between related documents

---

*📖 Happy reading and developing with CloudLeakage!*
