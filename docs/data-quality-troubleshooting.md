# Data Quality Troubleshooting Guide

## Overview

This guide provides comprehensive troubleshooting solutions for PrimeData's enterprise data quality management system, covering rule configuration, violation handling, and system integration issues.

## Common Data Quality Issues

### **1. Data Quality Rules Not Saving**

#### **Symptoms**
- "Failed to Save Rules" error
- Rules not appearing in UI
- API errors when updating rules

#### **Root Causes**
1. **Database connection issues**
2. **Rule validation failures**
3. **Serialization errors**
4. **Permission problems**

#### **Solutions**

##### **Check Database Connection**
```bash
# Verify database is running
docker-compose ps postgres

# Test database connection
docker exec -it primedata-postgres psql -U primedata -d primedata -c "SELECT COUNT(*) FROM data_quality_rules;"
```

##### **Validate Rule Configuration**
```json
// Ensure rule configuration is valid
{
  "name": "Required Fields Rule",
  "description": "All documents must have required fields",
  "rule_type": "required_fields",
  "severity": "error",
  "configuration": {
    "fields": ["title", "author"],
    "validation_pattern": "^.+$"
  },
  "enabled": true
}
```

##### **Check API Response**
```bash
# Test API endpoint
curl -X GET "http://localhost:8000/api/v1/data-quality/products/{product_id}/rules" \
  -H "Authorization: Bearer your_token"
```

#### **Prevention**
- Always validate rule configuration before saving
- Test database connectivity regularly
- Use proper error handling in API calls

### **2. Quality Violations Not Detected**

#### **Symptoms**
- Rules configured but no violations reported
- Data quality scores not updating
- Violation detection not working

#### **Root Causes**
1. **Rule evaluation not running**
2. **Data not meeting rule criteria**
3. **Rule configuration issues**
4. **Evaluation engine problems**

#### **Solutions**

##### **Check Rule Evaluation**
```python
# Test rule evaluation manually
from primedata.dq.validator import DataQualityValidator

validator = DataQualityValidator()
rules = get_data_quality_rules(product_id)
violations = validator.evaluate_rules(data, rules)
print(f"Found {len(violations)} violations")
```

##### **Verify Rule Configuration**
```json
// Ensure rule is properly configured
{
  "rule_type": "required_fields",
  "configuration": {
    "fields": ["title", "author"],
    "validation_pattern": "^.+$"
  },
  "enabled": true
}
```

##### **Check Data Quality**
```python
# Check if data meets rule criteria
def check_required_fields(data, fields):
    for item in data:
        for field in fields:
            if field not in item or not item[field]:
                return False
    return True
```

#### **Prevention**
- Test rules with sample data
- Verify rule configuration
- Monitor rule evaluation logs

### **3. False Positive Violations**

#### **Symptoms**
- Rules triggering incorrectly
- Valid data marked as violations
- High false positive rate

#### **Root Causes**
1. **Incorrect rule logic**
2. **Data format mismatches**
3. **Rule threshold issues**
4. **Data preprocessing problems**

#### **Solutions**

##### **Review Rule Logic**
```python
# Debug rule evaluation
def debug_rule_evaluation(data, rule):
    print(f"Rule: {rule['name']}")
    print(f"Configuration: {rule['configuration']}")
    
    for item in data:
        result = evaluate_rule_item(item, rule)
        print(f"Item: {item['id']}, Result: {result}")
```

##### **Adjust Rule Thresholds**
```json
// Fine-tune rule parameters
{
  "rule_type": "max_duplicate_rate",
  "configuration": {
    "max_duplicate_percentage": 15.0  // Increase from 10.0
  }
}
```

##### **Improve Data Preprocessing**
```python
# Clean data before evaluation
def preprocess_data(data):
    # Remove null values
    # Normalize text
    # Fix encoding issues
    return cleaned_data
```

#### **Prevention**
- Test rules with diverse data samples
- Use appropriate thresholds
- Implement data preprocessing

### **4. Performance Issues with Quality Rules**

#### **Symptoms**
- Slow rule evaluation
- High memory usage
- Timeout errors
- System performance degradation

#### **Root Causes**
1. **Inefficient rule logic**
2. **Large dataset processing**
3. **Resource constraints**
4. **Concurrent evaluation issues**

#### **Solutions**

##### **Optimize Rule Logic**
```python
# Use efficient data structures
def optimized_duplicate_check(data):
    seen = set()
    duplicates = []
    
    for item in data:
        key = hash(item['content'])
        if key in seen:
            duplicates.append(item)
        else:
            seen.add(key)
    
    return duplicates
```

##### **Implement Batch Processing**
```python
# Process data in batches
def batch_evaluate_rules(data, rules, batch_size=1000):
    violations = []
    
    for i in range(0, len(data), batch_size):
        batch = data[i:i+batch_size]
        batch_violations = evaluate_rules_batch(batch, rules)
        violations.extend(batch_violations)
    
    return violations
```

##### **Use Caching**
```python
# Cache rule evaluation results
from functools import lru_cache

@lru_cache(maxsize=1000)
def cached_rule_evaluation(data_hash, rule_id):
    # Expensive rule evaluation
    return result
```

#### **Prevention**
- Design efficient rule logic
- Use appropriate data structures
- Implement caching strategies
- Monitor resource usage

## Advanced Troubleshooting

### **Rule Configuration Issues**

#### **Complex Rule Logic**
**Symptoms:**
- Rules not working as expected
- Complex validation failures
- Rule interaction problems

**Solutions:**
1. **Break Down Complex Rules**
   ```python
   # Instead of one complex rule
   def complex_validation(data):
       # Break into smaller, testable functions
       return (
           validate_required_fields(data) and
           validate_data_format(data) and
           validate_business_rules(data)
       )
   ```

2. **Use Rule Composition**
   ```python
   # Compose rules from smaller components
   class CompositeRule:
       def __init__(self, sub_rules):
           self.sub_rules = sub_rules
       
       def evaluate(self, data):
           results = []
           for rule in self.sub_rules:
               results.append(rule.evaluate(data))
           return all(results)
   ```

3. **Implement Rule Testing**
   ```python
   # Test rules with sample data
   def test_rule(rule, test_data):
       expected_results = [True, False, True]  # Expected outcomes
       actual_results = [rule.evaluate(item) for item in test_data]
       assert actual_results == expected_results
   ```

#### **Rule Versioning Issues**
**Symptoms:**
- Rule changes not taking effect
- Version conflicts
- Rollback problems

**Solutions:**
1. **Implement Rule Versioning**
   ```python
   class VersionedRule:
       def __init__(self, rule_id, version, configuration):
           self.rule_id = rule_id
           self.version = version
           self.configuration = configuration
       
       def get_latest_version(self):
           return self.get_version(self.get_max_version())
   ```

2. **Use Rule Migration**
   ```python
   def migrate_rule(old_rule, new_configuration):
       # Create new version
       new_rule = create_rule_version(old_rule.rule_id, new_configuration)
       
       # Update active rules
       update_active_rules(old_rule.rule_id, new_rule.version)
       
       # Archive old version
       archive_rule_version(old_rule.rule_id, old_rule.version)
   ```

3. **Implement Rule Rollback**
   ```python
   def rollback_rule(rule_id, target_version):
       # Get target version
       target_rule = get_rule_version(rule_id, target_version)
       
       # Update active rules
       update_active_rules(rule_id, target_version)
       
       # Log rollback
       log_rule_rollback(rule_id, target_version)
   ```

### **Violation Management Issues**

#### **Violation Processing Problems**
**Symptoms:**
- Violations not being processed
- Duplicate violations
- Violation status not updating

**Solutions:**
1. **Implement Violation Deduplication**
   ```python
   def deduplicate_violations(violations):
       seen = set()
       unique_violations = []
       
       for violation in violations:
           key = (violation['rule_id'], violation['data_id'])
           if key not in seen:
               seen.add(key)
               unique_violations.append(violation)
       
       return unique_violations
   ```

2. **Use Violation Queuing**
   ```python
   from queue import Queue
   import threading
   
   class ViolationProcessor:
       def __init__(self):
           self.queue = Queue()
           self.worker = threading.Thread(target=self.process_violations)
           self.worker.start()
       
       def process_violations(self):
           while True:
               violation = self.queue.get()
               self.handle_violation(violation)
               self.queue.task_done()
   ```

3. **Implement Violation Status Tracking**
   ```python
   class ViolationStatus:
       PENDING = "pending"
       PROCESSING = "processing"
       RESOLVED = "resolved"
       IGNORED = "ignored"
       
       def update_status(self, violation_id, new_status):
           # Update violation status
           # Log status change
           # Notify stakeholders
           pass
   ```

#### **Violation Reporting Issues**
**Symptoms:**
- Reports not generating
- Incorrect violation counts
- Missing violation details

**Solutions:**
1. **Implement Report Caching**
   ```python
   from functools import lru_cache
   import datetime
   
   @lru_cache(maxsize=100)
   def get_violation_report(product_id, date_range):
       # Generate violation report
       # Cache for 1 hour
       return report
   ```

2. **Use Asynchronous Reporting**
   ```python
   import asyncio
   
   async def generate_violation_report(product_id):
       # Generate report asynchronously
       report = await process_violations_async(product_id)
       return report
   ```

3. **Implement Report Validation**
   ```python
   def validate_violation_report(report):
       # Check report completeness
       # Validate violation counts
       # Verify data integrity
       return validation_results
   ```

### **System Integration Issues**

#### **Database Integration Problems**
**Symptoms:**
- Rule data not persisting
- Audit trail missing
- Transaction failures

**Solutions:**
1. **Implement Transaction Management**
   ```python
   from sqlalchemy.orm import sessionmaker
   
   def save_rules_with_transaction(rules):
       session = Session()
       try:
           for rule in rules:
               session.add(rule)
           session.commit()
       except Exception as e:
           session.rollback()
           raise e
       finally:
           session.close()
   ```

2. **Use Database Connection Pooling**
   ```python
   from sqlalchemy.pool import QueuePool
   
   engine = create_engine(
       database_url,
       poolclass=QueuePool,
       pool_size=10,
       max_overflow=20
   )
   ```

3. **Implement Database Health Checks**
   ```python
   def check_database_health():
       try:
           session = Session()
           session.execute("SELECT 1")
           session.close()
           return True
       except Exception:
           return False
   ```

#### **API Integration Issues**
**Symptoms:**
- API calls failing
- Authentication problems
- Rate limiting issues

**Solutions:**
1. **Implement API Retry Logic**
   ```python
   import requests
   from requests.adapters import HTTPAdapter
   from urllib3.util.retry import Retry
   
   def create_session_with_retries():
       session = requests.Session()
       retry_strategy = Retry(
           total=3,
           backoff_factor=1,
           status_forcelist=[429, 500, 502, 503, 504]
       )
       adapter = HTTPAdapter(max_retries=retry_strategy)
       session.mount("http://", adapter)
       session.mount("https://", adapter)
       return session
   ```

2. **Use API Rate Limiting**
   ```python
   import time
   
   class RateLimitedAPI:
       def __init__(self, rate_limit=100):
           self.rate_limit = rate_limit
           self.last_request = 0
       
       def make_request(self, url):
           now = time.time()
           if now - self.last_request < 1/self.rate_limit:
               time.sleep(1/self.rate_limit - (now - self.last_request))
           self.last_request = time.time()
           return requests.get(url)
   ```

3. **Implement API Authentication**
   ```python
   def authenticate_api_request(request):
       token = request.headers.get('Authorization')
       if not token:
           raise AuthenticationError("Missing authorization token")
       
       try:
           payload = jwt.decode(token, public_key, algorithms=['RS256'])
           return payload
       except jwt.InvalidTokenError:
           raise AuthenticationError("Invalid token")
   ```

## Debugging Tools and Techniques

### **Rule Debugging**

#### **Rule Evaluation Debugging**
```python
def debug_rule_evaluation(data, rule):
    print(f"Evaluating rule: {rule['name']}")
    print(f"Rule configuration: {rule['configuration']}")
    
    for i, item in enumerate(data):
        print(f"Item {i}: {item}")
        result = evaluate_rule_item(item, rule)
        print(f"Result: {result}")
        print("---")
```

#### **Rule Performance Profiling**
```python
import cProfile
import pstats

def profile_rule_evaluation(data, rules):
    profiler = cProfile.Profile()
    profiler.enable()
    
    violations = evaluate_rules(data, rules)
    
    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats()
    
    return violations
```

#### **Rule Testing Framework**
```python
class RuleTestFramework:
    def __init__(self):
        self.test_cases = []
    
    def add_test_case(self, rule, test_data, expected_result):
        self.test_cases.append({
            'rule': rule,
            'test_data': test_data,
            'expected_result': expected_result
        })
    
    def run_tests(self):
        results = []
        for test_case in self.test_cases:
            actual_result = evaluate_rule(test_case['test_data'], test_case['rule'])
            passed = actual_result == test_case['expected_result']
            results.append({
                'test_case': test_case,
                'actual_result': actual_result,
                'passed': passed
            })
        return results
```

### **Violation Analysis**

#### **Violation Pattern Analysis**
```python
def analyze_violation_patterns(violations):
    patterns = {}
    
    for violation in violations:
        rule_type = violation['rule_type']
        if rule_type not in patterns:
            patterns[rule_type] = []
        patterns[rule_type].append(violation)
    
    return patterns
```

#### **Violation Trend Analysis**
```python
import pandas as pd
from datetime import datetime, timedelta

def analyze_violation_trends(violations, days=30):
    df = pd.DataFrame(violations)
    df['created_at'] = pd.to_datetime(df['created_at'])
    
    # Group by day
    daily_violations = df.groupby(df['created_at'].dt.date).size()
    
    # Calculate trends
    trend = daily_violations.pct_change().mean()
    
    return {
        'daily_violations': daily_violations.to_dict(),
        'trend': trend,
        'total_violations': len(violations)
    }
```

#### **Violation Impact Analysis**
```python
def analyze_violation_impact(violations):
    impact_analysis = {
        'high_impact': [],
        'medium_impact': [],
        'low_impact': []
    }
    
    for violation in violations:
        severity = violation['severity']
        if severity == 'error':
            impact_analysis['high_impact'].append(violation)
        elif severity == 'warning':
            impact_analysis['medium_impact'].append(violation)
        else:
            impact_analysis['low_impact'].append(violation)
    
    return impact_analysis
```

## Prevention Strategies

### **Proactive Quality Management**

#### **Rule Health Monitoring**
```python
def monitor_rule_health():
    # Check rule performance
    # Monitor violation rates
    # Track rule effectiveness
    # Alert on anomalies
    pass
```

#### **Automated Rule Testing**
```python
def automated_rule_testing():
    # Test rules with sample data
    # Validate rule configuration
    # Check rule performance
    # Report rule health
    pass
```

#### **Quality Metrics Dashboard**
```python
def create_quality_dashboard():
    # Real-time quality metrics
    # Violation trends
    # Rule performance
    # System health
    pass
```

### **Best Practices**

#### **Rule Design**
1. **Keep Rules Simple**
   - Single responsibility
   - Clear logic
   - Easy to test
   - Well documented

2. **Use Appropriate Severity Levels**
   - Error: Critical issues
   - Warning: Important issues
   - Info: Informational issues

3. **Implement Rule Testing**
   - Unit tests for rules
   - Integration tests
   - Performance tests
   - User acceptance tests

#### **Violation Management**
1. **Implement Violation Lifecycle**
   - Detection
   - Notification
   - Resolution
   - Closure

2. **Use Violation Prioritization**
   - Severity-based prioritization
   - Impact-based prioritization
   - Time-based prioritization

3. **Implement Violation Analytics**
   - Trend analysis
   - Pattern recognition
   - Impact assessment
   - Root cause analysis

## Support Resources

### **Documentation**
- **Data Quality Guide**: `docs/data-quality.md`
- **API Reference**: `docs/api-reference.md`
- **Pipeline Guide**: `docs/pipeline-guide.md`

### **Community Support**
- GitHub Issues
- User Forums
- Documentation Wiki
- Expert Consultations

### **Professional Support**
- Enterprise Support
- Custom Development
- Training Services
- Consulting Services

This comprehensive troubleshooting guide ensures successful data quality management and quick resolution of common issues.
