# PrimeData FAQ

Frequently Asked Questions about PrimeData platform.

## 🚀 Getting Started

### **Q: What is PrimeData?**
A: PrimeData is an enterprise-grade data platform designed for AI workflows. It provides comprehensive data ingestion, processing, vectorization, and quality management with advanced features like team collaboration, billing integration, and analytics.

### **Q: Who is PrimeData for?**
A: PrimeData is designed for:
- **Data Scientists**: Processing and preparing data for AI models
- **ML Engineers**: Building and managing AI pipelines
- **Data Teams**: Managing data quality and governance
- **Enterprises**: Large-scale data processing with compliance
- **Developers**: Building AI applications with quality data

### **Q: What makes PrimeData different?**
A: PrimeData offers:
- **Enterprise Data Quality**: 7 rule types with real-time monitoring
- **Hybrid Chunking**: AI-powered and manual chunking options
- **Team Collaboration**: Role-based access control
- **Billing Integration**: Stripe-powered subscription management
- **Analytics**: Comprehensive performance and quality metrics
- **Export Management**: Secure data export with provenance

### **Q: Do I need coding experience?**
A: No! PrimeData provides a user-friendly interface for most operations. However, some advanced features may require basic technical knowledge.

## 💰 Billing & Pricing

### **Q: What are the pricing plans?**
A: PrimeData offers three plans:
- **Free**: 3 products, 5 data sources per product, 10 pipeline runs/month
- **Pro ($99/month)**: 25 products, 50 data sources per product, 1,000 pipeline runs/month
- **Enterprise ($999/month)**: Unlimited everything, advanced features, dedicated support

### **Q: Can I change plans anytime?**
A: Yes! You can upgrade or downgrade your plan at any time. Changes take effect immediately.

### **Q: What happens if I exceed my limits?**
A: You'll receive notifications when approaching limits. If exceeded, you'll need to upgrade your plan or reduce usage.

### **Q: Is there a free trial?**
A: The Free plan provides a permanent free tier with limited features. No trial period required.

### **Q: How is billing calculated?**
A: Billing is based on:
- **Products**: Number of products created
- **Data Sources**: Number of data sources configured
- **Pipeline Runs**: Number of pipeline executions
- **Vectors**: Amount of vector data stored

## 🔧 Technical Questions

### **Q: What data sources are supported?**
A: PrimeData supports:
- **Web Sources**: Websites, online content
- **Folder Sources**: Local and remote directories
- **Database Sources**: PostgreSQL, MySQL, and other SQL databases
- **API Sources**: RESTful APIs and webhooks

### **Q: What file formats are supported?**
A: PrimeData supports most text-based formats:
- **Documents**: PDF, DOC, DOCX, TXT, RTF
- **Web Content**: HTML, XML, JSON
- **Code**: Python, JavaScript, Java, C++, etc.
- **Data**: CSV, JSON, XML
- **Markup**: Markdown, LaTeX, HTML

### **Q: How does chunking work?**
A: PrimeData offers two chunking modes:
- **Auto Mode**: AI analyzes content and optimizes settings automatically
- **Manual Mode**: Full control over chunk size, overlap, and strategy

### **Q: What embedding models are supported?**
A: PrimeData supports various embedding models:
- **OpenAI**: text-embedding-ada-002, text-embedding-3-small, text-embedding-3-large
- **Hugging Face**: Various open-source models
- **Custom Models**: Your own embedding models

### **Q: How is data quality measured?**
A: Data quality is measured using:
- **Quality Rules**: 7 rule types for comprehensive validation
- **Quality Scores**: 0-100 scoring system
- **Violation Tracking**: Real-time quality monitoring
- **Trend Analysis**: Quality improvements over time

## 🏢 Enterprise Features

### **Q: What enterprise features are available?**
A: Enterprise features include:
- **Team Management**: Role-based access control
- **Billing Integration**: Stripe-powered subscriptions
- **Analytics**: Comprehensive performance metrics
- **Export Management**: Secure data export
- **Audit Trails**: Complete activity logging
- **Compliance**: Enterprise-grade governance

### **Q: How does team management work?**
A: Team management includes:
- **Roles**: Owner, Admin, Editor, Viewer
- **Permissions**: Granular access control
- **Invitations**: Email-based team invitations
- **Activity Tracking**: Monitor team member activity

### **Q: Is there audit logging?**
A: Yes! PrimeData provides comprehensive audit logging:
- **User Actions**: Track all user activities
- **Data Changes**: Monitor data modifications
- **System Events**: Log system activities
- **Compliance**: Generate compliance reports

### **Q: How secure is PrimeData?**
A: PrimeData implements enterprise-grade security:
- **Authentication**: JWT tokens with Google OAuth
- **Authorization**: Role-based access control
- **Data Encryption**: Encrypted data storage and transmission
- **Audit Logging**: Complete activity tracking
- **Access Control**: Granular permission management

## 📊 Analytics & Monitoring

### **Q: What analytics are available?**
A: PrimeData provides comprehensive analytics:
- **Performance Metrics**: Processing speed, success rates
- **Quality Metrics**: Data quality scores and trends
- **Usage Analytics**: Resource consumption and costs
- **Team Analytics**: Team member activity and productivity

### **Q: How are metrics calculated?**
A: Metrics are calculated using:
- **Real-time Processing**: Live data during processing
- **Historical Analysis**: Trends over time
- **Quality Assessment**: AI-powered quality scoring
- **Performance Monitoring**: System resource usage

### **Q: Can I export analytics data?**
A: Yes! You can export:
- **Analytics Reports**: PDF and CSV reports
- **Raw Data**: JSON and CSV data exports
- **Custom Reports**: Tailored analytics reports
- **API Access**: Programmatic access to metrics

## 🔄 Data Processing

### **Q: How does the pipeline work?**
A: The pipeline processes data in stages:
1. **Ingestion**: Collect data from sources
2. **Preprocessing**: Clean and prepare data
3. **Chunking**: Split data into manageable chunks
4. **Embedding**: Generate vector embeddings
5. **Indexing**: Store vectors in Qdrant
6. **Quality Check**: Validate data quality
7. **Export**: Make data available for use

### **Q: How long does processing take?**
A: Processing time depends on:
- **Data Volume**: Amount of data to process
- **Content Complexity**: Complexity of content
- **Chunking Settings**: Chunk size and overlap
- **Embedding Model**: Model performance
- **System Resources**: Available CPU and memory

### **Q: Can I monitor processing in real-time?**
A: Yes! PrimeData provides:
- **Real-time Updates**: Live processing status
- **Progress Tracking**: Detailed progress information
- **Error Handling**: Immediate error notifications
- **Performance Metrics**: Processing speed and efficiency

### **Q: What happens if processing fails?**
A: PrimeData handles failures gracefully:
- **Error Logging**: Detailed error information
- **Retry Logic**: Automatic retry mechanisms
- **Partial Results**: Save successful processing
- **Recovery**: Resume from failure points

## 🔍 Data Quality

### **Q: What quality rules are available?**
A: PrimeData offers 7 rule types:
1. **Required Fields**: Ensure critical fields exist
2. **Duplicate Detection**: Find and flag duplicates
3. **Chunk Coverage**: Ensure adequate content coverage
4. **Bad Extensions**: Block problematic file types
5. **File Size Limits**: Control file size constraints
6. **Content Validation**: Validate content quality
7. **Custom Rules**: Define your own validation logic

### **Q: How are quality violations handled?**
A: Quality violations are handled with:
- **Severity Levels**: Error, Warning, Info
- **Real-time Monitoring**: Immediate violation detection
- **Notification System**: Alert users to violations
- **Reporting**: Generate quality reports

### **Q: Can I customize quality rules?**
A: Yes! You can:
- **Configure Rules**: Set rule parameters
- **Custom Messages**: Define custom error messages
- **Severity Levels**: Set violation severity
- **Conditional Logic**: Create complex validation rules

## 📤 Export & Data Management

### **Q: What can I export?**
A: You can export:
- **Processed Data**: Chunks and embeddings
- **Source Data**: Original source files
- **Metadata**: File information and provenance
- **Quality Reports**: Data quality assessments
- **Configuration**: Product and pipeline settings

### **Q: How secure are exports?**
A: Exports are secured with:
- **Presigned URLs**: Time-limited download links
- **Access Control**: Secure access to exports
- **Encryption**: Encrypted data transmission
- **Audit Logging**: Track download activity

### **Q: Can I schedule exports?**
A: Yes! You can:
- **Automated Exports**: Schedule regular exports
- **Version Control**: Export specific versions
- **Quality Filters**: Export only high-quality data
- **Custom Formats**: Choose export formats

## 🛠️ Development & Integration

### **Q: Is there an API?**
A: Yes! PrimeData provides a comprehensive REST API:
- **Complete Coverage**: All features accessible via API
- **OpenAPI Documentation**: Auto-generated API docs
- **SDK Support**: Python and JavaScript SDKs
- **Webhook Support**: Real-time event notifications

### **Q: Can I integrate with other tools?**
A: Yes! PrimeData integrates with:
- **MLflow**: Experiment tracking and model management
- **Airflow**: Workflow orchestration
- **Stripe**: Payment processing
- **Google OAuth**: Authentication
- **Custom Tools**: Via API and webhooks

### **Q: Is there a CLI?**
A: Currently, PrimeData focuses on the web interface and API. CLI tools may be added in future releases.

### **Q: Can I deploy on-premises?**
A: Yes! PrimeData can be deployed:
- **Local Development**: Docker Compose setup
- **On-Premises**: Self-hosted deployment
- **Cloud**: Cloud provider deployment
- **Hybrid**: Mixed deployment options

## 🆘 Support & Troubleshooting

### **Q: What support is available?**
A: Support varies by plan:
- **Free**: Community support and documentation
- **Pro**: Email support and priority assistance
- **Enterprise**: Phone, email, and dedicated support

### **Q: Where can I get help?**
A: You can get help from:
- **Documentation**: Comprehensive guides and references
- **Troubleshooting Guide**: Common issues and solutions
- **Community Forum**: User community support
- **Support Team**: Direct support for Pro and Enterprise

### **Q: How do I report bugs?**
A: You can report bugs:
- **GitHub Issues**: Create issues in the repository
- **Support Email**: Email the support team
- **Community Forum**: Post in the community forum
- **In-App Feedback**: Use the feedback feature

### **Q: Is there a status page?**
A: Yes! Check the status page for:
- **System Status**: Current system health
- **Incident Reports**: Known issues and resolutions
- **Maintenance**: Scheduled maintenance windows
- **Updates**: System updates and announcements

## 🔮 Future Features

### **Q: What features are coming?**
A: Upcoming features include:
- **Advanced Analytics**: More detailed analytics and reporting
- **Custom Models**: Support for custom embedding models
- **Advanced Scheduling**: More sophisticated scheduling options
- **Multi-workspace**: Cross-workspace data sharing
- **CLI Tools**: Command-line interface tools

### **Q: How can I request features?**
A: You can request features:
- **GitHub Issues**: Create feature requests
- **Support Email**: Email the support team
- **Community Forum**: Post in the community forum
- **User Feedback**: Use the in-app feedback feature

### **Q: Is there a roadmap?**
A: Yes! The roadmap includes:
- **Short-term**: Bug fixes and improvements
- **Medium-term**: New features and enhancements
- **Long-term**: Major platform updates
- **Community**: Community-driven features

---

**Still have questions?** Check the [Troubleshooting Guide](troubleshooting.md) or contact support for assistance.
