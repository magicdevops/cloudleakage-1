# CloudLeakage Production Deployment Checklist

## 🚨 Critical Security Requirements

### 1. Environment Variables (REQUIRED)
```bash
export FLASK_ENV=production
export SECRET_KEY="your-secure-random-secret-key-32-chars+"
export ENCRYPTION_KEY="your-32-byte-base64-encoded-encryption-key"
export DATABASE_URL="postgresql://user:pass@host:port/dbname"
```

### 2. Disable Debug Mode
```python
# In app.py - Change from:
app.run(debug=True, host='127.0.0.1', port=5000)
# To:
app.run(debug=False, host='0.0.0.0', port=8000)
```

### 3. Production Database
- **PostgreSQL** (recommended) or **MySQL**
- **NOT SQLite** for production
- Configure connection pooling
- Set up database backups

### 4. WSGI Server
```bash
# Install Gunicorn
pip install gunicorn

# Run with Gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

### 5. Reverse Proxy (Nginx)
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 6. HTTPS/SSL
- Configure SSL certificates
- Force HTTPS redirects
- Set secure cookie flags

## 🔒 Security Enhancements Needed

### 1. Add Security Headers
```python
from flask_talisman import Talisman

# Add to create_app()
Talisman(app, force_https=True)
```

### 2. CSRF Protection
```python
from flask_wtf.csrf import CSRFProtect

csrf = CSRFProtect(app)
```

### 3. Rate Limiting
```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)
```

### 4. Input Validation
- Validate all user inputs
- Sanitize file uploads
- Implement proper error handling

## 📊 Monitoring & Logging

### 1. Application Logging
```python
import logging
from logging.handlers import RotatingFileHandler

if not app.debug:
    file_handler = RotatingFileHandler('logs/cloudleakage.log', maxBytes=10240, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
```

### 2. Health Check Endpoint
```python
@app.route('/health')
def health_check():
    return {'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()}
```

### 3. Metrics Collection
- Application performance monitoring
- Database connection monitoring
- AWS API call tracking

## 🚀 Deployment Architecture

### Recommended Production Setup:
```
Internet → Load Balancer → Nginx → Gunicorn → Flask App
                                      ↓
                              PostgreSQL Database
                                      ↓
                                 AWS Services
```

## 📋 Pre-Deployment Testing

### 1. Security Testing
- [ ] Vulnerability scanning
- [ ] Penetration testing
- [ ] Dependency security audit

### 2. Performance Testing
- [ ] Load testing
- [ ] Database performance
- [ ] AWS API rate limits

### 3. Backup & Recovery
- [ ] Database backup strategy
- [ ] Application data backup
- [ ] Disaster recovery plan

## 🔧 Additional Production Dependencies

```bash
# Add to requirements.txt
flask-talisman==1.1.0
flask-wtf==1.1.1
flask-limiter==3.5.0
gunicorn==21.2.0
psycopg2-binary==2.9.7
redis==4.6.0
```

## ⚠️ Current Status: NOT PRODUCTION READY

**Must Fix Before Production:**
1. ❌ Debug mode disabled
2. ❌ Environment variables configured
3. ❌ Production database setup
4. ❌ WSGI server configuration
5. ❌ Security headers implemented
6. ❌ HTTPS/SSL configured
7. ❌ Proper logging setup
8. ❌ Error handling improved

**Estimated Time to Production Ready:** 2-3 days of dedicated work
