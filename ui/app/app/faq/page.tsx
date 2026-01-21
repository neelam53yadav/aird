'use client'

import { useState } from 'react'
import AppLayout from '@/components/layout/AppLayout'
import { 
  ChevronDown, 
  ChevronUp, 
  BookOpen, 
  Play, 
  Package, 
  Database, 
  BarChart3,
  Shield,
  FileText,
  Layers,
  Search,
  HelpCircle,
  Sparkles,
  CheckCircle,
  AlertTriangle,
  Info
} from 'lucide-react'

interface FAQItem {
  question: string
  answer: React.ReactNode
  category: 'getting-started' | 'features' | 'metrics' | 'troubleshooting'
}

const METRIC_CATEGORIES = {
  governance: {
    name: 'Governance & Compliance',
    icon: Shield,
    metrics: [
      { key: 'Secure', name: 'Security', description: 'Measures PII detection and privacy compliance. Detects emails, phone numbers, and other sensitive information. Higher scores indicate better data security.' },
      { key: 'Completeness', name: 'Completeness', description: 'Assesses how complete the content is. Based on token count and content presence. Ensures data has sufficient information for AI applications.' },
      { key: 'Accuracy', name: 'Accuracy', description: 'Evaluates information accuracy using ASCII ratio and spell checking. Higher scores indicate cleaner, more accurate text.' },
      { key: 'Metadata_Presence', name: 'Metadata Presence', description: 'Measures completeness of metadata fields (section, field_name, document_id). Essential for proper data organization and retrieval.' },
    ],
  },
  content: {
    name: 'Content Quality',
    icon: FileText,
    metrics: [
      { key: 'Quality', name: 'Quality', description: 'Overall content quality based on readability metrics (Flesch reading ease) and sentence length analysis. Higher scores indicate well-structured, readable content.' },
      { key: 'Context_Quality', name: 'Context Quality', description: 'Measures context richness through structure indicators (paragraphs, lists), information density (numbers, dates, references), and contextual keywords.' },
      { key: 'Audience_Intentionality', name: 'Audience Intentionality', description: 'Evaluates how well content targets its intended audience. Based on audience field presence and relevance.' },
      { key: 'Audience_Accessibility', name: 'Audience Accessibility', description: 'Measures content accessibility based on average sentence length. Ideal range is 10-25 words per sentence.' },
      { key: 'Diversity', name: 'Diversity', description: 'Content diversity measured by type-token ratio (vocabulary diversity). Higher scores indicate more varied vocabulary and less repetitive content.' },
      { key: 'Timeliness', name: 'Timeliness', description: 'Assesses content recency based on timestamp comparison. Newer content receives higher scores.' },
      { key: 'KnowledgeBase_Ready', name: 'Knowledge Base Ready', description: 'Composite score (40% metadata + 40% quality + 20% context) indicating readiness for RAG applications.' },
      { key: 'Token_Count', name: 'Token Count', description: 'Normalized token count around optimal target (900 tokens). Properly sized chunks are essential for effective AI processing.' },
    ],
  },
  chunking: {
    name: 'Chunking & Structure',
    icon: Layers,
    metrics: [
      { key: 'Chunk_Coherence', name: 'Chunk Coherence', description: 'Measures semantic cohesion within chunks. Uses embedding similarity to ensure chunks stay on one topic. Higher scores indicate better topic consistency.' },
      { key: 'Noise_Free_Score', name: 'Noise-Free Score', description: 'Percentage of content free from boilerplate, navigation elements, and legal footer text. Higher scores indicate cleaner, more useful content.' },
      { key: 'Chunk_Boundary_Quality', name: 'Chunk Boundary Quality', description: 'Assesses quality of chunk boundaries. Lower mid-sentence breaks indicate better chunking strategy. Score = 100 - (mid_sentence_rate × 100).' },
      { key: 'Avg_Chunk_Coherence', name: 'Avg Chunk Coherence', description: 'Average coherence score across all chunks. Provides overall assessment of chunk quality at the product level.' },
      { key: 'Avg_Noise_Free_Score', name: 'Avg Noise-Free Score', description: 'Average noise-free score across all chunks. Indicates overall content cleanliness for the entire product.' },
    ],
  },
  vector: {
    name: 'Vector Metrics',
    icon: Database,
    metrics: [
      { key: 'Embedding_Dimension_Consistency', name: 'Embedding Dimension Consistency', description: 'Percentage of vectors with expected dimension. Ensures all embeddings match the configured model dimension. Critical for vector search accuracy.' },
      { key: 'Embedding_Success_Rate', name: 'Embedding Success Rate', description: 'Percentage of chunks successfully embedded and stored in the vector database. Higher rates indicate successful processing.' },
      { key: 'Vector_Quality_Score', name: 'Vector Quality Score', description: 'Composite score evaluating valid vectors (no NaN/Inf), non-zero vectors, and optimal norm distribution. Essential for reliable semantic search.' },
      { key: 'Embedding_Model_Health', name: 'Embedding Model Health', description: 'Health score based on API error rates, fallback usage, dimension consistency, and response consistency. Indicates model reliability.' },
      { key: 'Semantic_Search_Readiness', name: 'Semantic Search Readiness', description: 'Composite score (25% dimension + 35% quality + 25% health + 15% success rate) indicating overall readiness for semantic search operations.' },
    ],
    note: 'These metrics are only available when vector creation is enabled for your product.',
  },
  rag: {
    name: 'RAG Performance',
    icon: Search,
    metrics: [
      { key: 'Retrieval_Recall_At_K', name: 'Retrieval Recall@K', description: 'Percentage of relevant documents retrieved in top K results. Measures how often the correct chunk appears in search results. Higher scores indicate better retrieval accuracy.' },
      { key: 'Average_Precision_At_K', name: 'Average Precision@K', description: 'Average precision across top K retrieved results. Measures ranking quality - how high relevant results appear in the list. Higher scores indicate better ranking.' },
      { key: 'Query_Coverage', name: 'Query Coverage', description: 'Percentage of queries with at least one relevant result retrieved. Indicates how well your data covers different query types. Higher scores indicate better coverage.' },
    ],
    note: 'These metrics are only available when vector creation is enabled. They use self-retrieval evaluation to assess RAG performance.',
  },
}

export default function FAQPage() {
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set())
  const [activeCategory, setActiveCategory] = useState<string | null>(null)

  const toggleItem = (id: string) => {
    setExpandedItems(prev => {
      const newSet = new Set(prev)
      if (newSet.has(id)) {
        newSet.delete(id)
      } else {
        newSet.add(id)
      }
      return newSet
    })
  }

  const faqItems: FAQItem[] = [
    // Getting Started
    {
      category: 'getting-started',
      question: 'How do I get started with AIRDOps?',
      answer: (
        <div className="space-y-4">
          <p className="text-gray-700">Follow these steps to get started:</p>
          <ol className="list-decimal list-inside space-y-2 text-gray-700 ml-4">
            <li><strong>Create a Product:</strong> Go to Products → New Product. Give it a name and optionally select a playbook.</li>
            <li><strong>Add Data Sources:</strong> Navigate to your product → Data Sources tab → Add Data Source. Connect your data (web, database, Confluence, SharePoint, or folder).</li>
            <li><strong>Run the Pipeline:</strong> Go to your product → Overview tab → Click "Run Pipeline" to process your data.</li>
            <li><strong>Review Metrics:</strong> After the pipeline completes, check the AI Trust Score tab to see quality metrics and recommendations.</li>
            <li><strong>Enable Vector Creation (Optional):</strong> If you need semantic search, enable vector creation in product settings to generate embeddings and RAG metrics.</li>
          </ol>
        </div>
      ),
    },
    {
      category: 'getting-started',
      question: 'What is a Product in AIRDOps?',
      answer: (
        <div className="space-y-2">
          <p className="text-gray-700">
            A <strong>Product</strong> is a container for your data that goes through the complete AI readiness pipeline. 
            Each product represents a distinct dataset or knowledge base that you want to make AI-ready.
          </p>
          <p className="text-gray-700">
            Products have versions, allowing you to track changes over time. You can have multiple products 
            for different use cases (e.g., "Product Documentation", "Customer Support KB", "Internal Wiki").
          </p>
        </div>
      ),
    },
    {
      category: 'getting-started',
      question: 'What is a Playbook and do I need one?',
      answer: (
        <div className="space-y-2">
          <p className="text-gray-700">
            A <strong>Playbook</strong> defines preprocessing strategies, chunking rules, and quality controls 
            tailored to specific content types (e.g., TECH, REGULATORY, FINANCE).
          </p>
          <p className="text-gray-700">
            <strong>You can:</strong>
          </p>
          <ul className="list-disc list-inside space-y-1 text-gray-700 ml-4">
            <li>Let AIRDOps auto-detect the best playbook based on your content</li>
            <li>Manually select a playbook during product creation</li>
            <li>Use the default playbook if none is specified</li>
          </ul>
          <p className="text-gray-700">
            Playbooks enable AI-Ready metrics (Chunk Coherence, Noise-Free Score) which provide deeper insights 
            into your data quality.
          </p>
        </div>
      ),
    },
    {
      category: 'getting-started',
      question: 'How long does the pipeline take to run?',
      answer: (
        <div className="space-y-2">
          <p className="text-gray-700">
            Pipeline duration depends on several factors:
          </p>
          <ul className="list-disc list-inside space-y-1 text-gray-700 ml-4">
            <li><strong>Data volume:</strong> Number of files and total content size</li>
            <li><strong>Embedding model:</strong> Large models (1024+ dimensions) take longer than smaller ones</li>
            <li><strong>Vector creation:</strong> If enabled, embedding generation is the longest step</li>
          </ul>
          <p className="text-gray-700">
            <strong>Typical times:</strong>
          </p>
          <ul className="list-disc list-inside space-y-1 text-gray-700 ml-4">
            <li>Small datasets (&lt;100 files): 5-15 minutes</li>
            <li>Medium datasets (100-1000 files): 15-60 minutes</li>
            <li>Large datasets (1000+ files): 1-4 hours (with vector creation)</li>
          </ul>
          <p className="text-gray-700 text-sm bg-blue-50 p-3 rounded-lg border border-blue-200">
            <strong>💡 Tip:</strong> For faster processing, use smaller embedding models (e.g., minilm) or disable 
            vector creation if you only need quality metrics.
          </p>
        </div>
      ),
    },
    // Features
    {
      category: 'features',
      question: 'What data sources can I connect?',
      answer: (
        <div className="space-y-2">
          <p className="text-gray-700">AIRDOps supports multiple data source types:</p>
          <ul className="list-disc list-inside space-y-1 text-gray-700 ml-4">
            <li><strong>Web:</strong> Websites, documentation sites, blogs</li>
            <li><strong>Database:</strong> SQL databases (PostgreSQL, MySQL, etc.)</li>
            <li><strong>Confluence:</strong> Atlassian Confluence spaces and pages</li>
            <li><strong>SharePoint:</strong> Microsoft SharePoint sites and document libraries</li>
            <li><strong>Folder:</strong> Local or network file system folders</li>
          </ul>
          <p className="text-gray-700">
            Each data source type has specific configuration options. Navigate to your product → 
            Data Sources tab → Add Data Source to see available options.
          </p>
        </div>
      ),
    },
    {
      category: 'features',
      question: 'What is the difference between vector-enabled and non-vector-enabled products?',
      answer: (
        <div className="space-y-2">
          <p className="text-gray-700">
            <strong>Vector-Enabled Products:</strong>
          </p>
          <ul className="list-disc list-inside space-y-1 text-gray-700 ml-4">
            <li>Generate embeddings for semantic search</li>
            <li>Store vectors in the vector database for retrieval</li>
            <li>Calculate Vector Metrics (5 metrics) and RAG Performance Metrics (3 metrics)</li>
            <li>Enable semantic search in the Playground</li>
            <li>Require more processing time and storage</li>
          </ul>
          <p className="text-gray-700 mt-3">
            <strong>Non-Vector-Enabled Products:</strong>
          </p>
          <ul className="list-disc list-inside space-y-1 text-gray-700 ml-4">
            <li>Calculate Base Trust Metrics (14 metrics) and AI-Ready Metrics (5 metrics)</li>
            <li>Faster processing (no embedding generation)</li>
            <li>Lower storage requirements</li>
            <li>Ideal for quality assessment without semantic search needs</li>
          </ul>
          <p className="text-gray-700 text-sm bg-yellow-50 p-3 rounded-lg border border-yellow-200 mt-3">
            <strong>Note:</strong> You can enable/disable vector creation in product settings. 
            Vector metrics will show "Not Evaluated" when disabled.
          </p>
        </div>
      ),
    },
    {
      category: 'features',
      question: 'How do I improve my AI Trust Score?',
      answer: (
        <div className="space-y-2">
          <p className="text-gray-700">
            The AI Trust Score is a weighted composite of all quality metrics. To improve it:
          </p>
          <ul className="list-disc list-inside space-y-1 text-gray-700 ml-4">
            <li><strong>Review Optimization Suggestions:</strong> Check the AI Trust Score tab for actionable recommendations</li>
            <li><strong>Apply Recommendations:</strong> Click "Apply" on suggestions like "Increase Overlap" or "Extract Metadata"</li>
            <li><strong>Improve Data Quality:</strong> Ensure your source data is clean, well-structured, and complete</li>
            <li><strong>Add Metadata:</strong> Include section, field_name, and document_id in your data</li>
            <li><strong>Remove PII:</strong> Clean sensitive information before ingestion</li>
            <li><strong>Optimize Chunking:</strong> Adjust chunk size and overlap based on recommendations</li>
            <li><strong>Re-run Pipeline:</strong> After making changes, run the pipeline again to see updated scores</li>
          </ul>
        </div>
      ),
    },
    {
      category: 'features',
      question: 'What is the Playground feature?',
      answer: (
        <div className="space-y-2">
          <p className="text-gray-700">
            The <strong>Playground</strong> allows you to test semantic search on your indexed data. 
            It's available for products with vector creation enabled.
          </p>
          <p className="text-gray-700">
            <strong>Features:</strong>
          </p>
          <ul className="list-disc list-inside space-y-1 text-gray-700 ml-4">
            <li>Test queries against your indexed data</li>
            <li>See retrieval results with relevance scores</li>
            <li>Compare different embedding models</li>
            <li>Validate RAG performance before production use</li>
          </ul>
          <p className="text-gray-700">
            Access it from: Product → Playground tab (only visible for vector-enabled products).
          </p>
        </div>
      ),
    },
    // Metrics
    {
      category: 'metrics',
      question: 'What metrics are available and what do they mean?',
      answer: (
        <div className="space-y-4">
          <p className="text-gray-700">
            AIRDOps provides <strong>26 comprehensive metrics</strong> organized into 5 categories. 
            All metrics are scored on a 0-100 scale, where higher scores indicate better quality.
          </p>
          <div className="space-y-6">
            {Object.entries(METRIC_CATEGORIES).map(([catKey, catConfig]) => {
              const Icon = catConfig.icon
              return (
                <div key={catKey} className="border border-gray-200 rounded-lg p-4">
                  <div className="flex items-center gap-2 mb-3">
                    <Icon className="h-5 w-5 text-blue-600" />
                    <h4 className="font-semibold text-gray-900">{catConfig.name}</h4>
                  </div>
                  {catConfig.note && (
                    <p className="text-sm text-amber-600 bg-amber-50 p-2 rounded mb-3 border border-amber-200">
                      <Info className="h-4 w-4 inline mr-1" />
                      {catConfig.note}
                    </p>
                  )}
                  <div className="space-y-3">
                    {catConfig.metrics.map((metric) => (
                      <div key={metric.key} className="border-l-2 border-gray-200 pl-3">
                        <h5 className="font-medium text-gray-900">{metric.name}</h5>
                        <p className="text-sm text-gray-600 mt-1">{metric.description}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      ),
    },
    {
      category: 'metrics',
      question: 'Why do some metrics show "Not Evaluated"?',
      answer: (
        <div className="space-y-2">
          <p className="text-gray-700">
            Some metrics require specific configurations to be calculated:
          </p>
          <ul className="list-disc list-inside space-y-1 text-gray-700 ml-4">
            <li><strong>Vector Metrics (5) & RAG Metrics (3):</strong> Only available when <code className="bg-gray-100 px-1 rounded">vector_creation_enabled = true</code>. Enable vector creation in product settings to see these metrics.</li>
            <li><strong>AI-Ready Metrics (Chunk Coherence, Noise-Free Score):</strong> Require a playbook with <code className="bg-gray-100 px-1 rounded">coherence</code> and <code className="bg-gray-100 px-1 rounded">noise_patterns</code> sections. Most playbooks include these by default.</li>
            <li><strong>Chunk Boundary Quality:</strong> Requires preprocessing statistics. This is automatically calculated during the preprocessing stage.</li>
          </ul>
          <p className="text-gray-700 text-sm bg-blue-50 p-3 rounded-lg border border-blue-200 mt-3">
            <strong>💡 Tip:</strong> To see all 26 metrics, ensure vector creation is enabled and a playbook is selected for your product.
          </p>
        </div>
      ),
    },
    {
      category: 'metrics',
      question: 'What is a good AI Trust Score?',
      answer: (
        <div className="space-y-2">
          <p className="text-gray-700">
            AI Trust Score interpretation:
          </p>
          <ul className="list-disc list-inside space-y-1 text-gray-700 ml-4">
            <li><strong>80-100% (Excellent):</strong> Ready for AI use. Your data is high-quality and well-structured.</li>
            <li><strong>60-79% (Good):</strong> Minor improvements recommended. Review optimization suggestions for quick wins.</li>
            <li><strong>40-59% (Needs Improvement):</strong> Significant enhancements required. Focus on data quality and structure.</li>
            <li><strong>0-39% (Poor):</strong> Major issues detected. Review violations and apply recommended fixes.</li>
          </ul>
          <p className="text-gray-700 text-sm bg-green-50 p-3 rounded-lg border border-green-200 mt-3">
            <strong>📊 Industry Standard:</strong> Organizations achieving &gt;85% quality scores see <strong>4x efficiency gains</strong> 
            in AI applications compared to 70-85% quality data.
          </p>
        </div>
      ),
    },
    {
      category: 'metrics',
      question: 'How are metrics calculated?',
      answer: (
        <div className="space-y-2">
          <p className="text-gray-700">
            Metrics are calculated during the pipeline execution:
          </p>
          <ul className="list-disc list-inside space-y-1 text-gray-700 ml-4">
            <li><strong>Base Trust Metrics:</strong> Calculated in the Scoring stage using heuristics and optional advanced libraries (textstat, spellchecker)</li>
            <li><strong>AI-Ready Metrics:</strong> Calculated in the Scoring stage using playbook configurations (coherence analysis, noise detection)</li>
            <li><strong>Vector Metrics:</strong> Calculated in the Indexing stage by analyzing embedding quality, dimension consistency, and model health</li>
            <li><strong>RAG Metrics:</strong> Calculated in the Indexing stage using self-retrieval evaluation (testing if chunks can retrieve themselves)</li>
          </ul>
          <p className="text-gray-700">
            All metrics are aggregated from chunk-level to product-level in the Fingerprint stage, 
            creating your readiness fingerprint.
          </p>
        </div>
      ),
    },
    // Troubleshooting
    {
      category: 'troubleshooting',
      question: 'My pipeline failed. What should I do?',
      answer: (
        <div className="space-y-2">
          <p className="text-gray-700">
            If your pipeline fails, follow these steps:
          </p>
          <ol className="list-decimal list-inside space-y-2 text-gray-700 ml-4">
            <li><strong>Check Pipeline Runs:</strong> Go to your product → Overview tab → View recent pipeline runs to see error messages</li>
            <li><strong>Review Error Details:</strong> Click on the failed run to see detailed error information</li>
            <li><strong>Common Issues:</strong>
              <ul className="list-disc list-inside ml-6 mt-1 space-y-1">
                <li>Data source connection issues (check credentials and permissions)</li>
                <li>Vector database connection problems (ensure the vector database service is running)</li>
                <li>Embedding model errors (check API keys for OpenAI models)</li>
                <li>Storage issues (check S3/MinIO configuration)</li>
              </ul>
            </li>
            <li><strong>Contact Support:</strong> If the issue persists, use the Support page to report the problem with error details</li>
          </ol>
        </div>
      ),
    },
    {
      category: 'troubleshooting',
      question: 'Why are my vector metrics showing 0% or "Not Evaluated"?',
      answer: (
        <div className="space-y-2">
          <p className="text-gray-700">
            Vector metrics show "Not Evaluated" when:
          </p>
          <ul className="list-disc list-inside space-y-1 text-gray-700 ml-4">
            <li><strong>Vector creation is disabled:</strong> Check product settings → ensure <code className="bg-gray-100 px-1 rounded">vector_creation_enabled</code> is set to <code className="bg-gray-100 px-1 rounded">true</code></li>
            <li><strong>Indexing stage was skipped:</strong> The DAG automatically skips indexing when vector creation is disabled</li>
            <li><strong>Indexing failed:</strong> Check pipeline runs for indexing stage errors</li>
            <li><strong>No vectors were created:</strong> All embedding attempts may have failed (check logs)</li>
          </ul>
          <p className="text-gray-700 text-sm bg-blue-50 p-3 rounded-lg border border-blue-200 mt-3">
            <strong>Solution:</strong> Enable vector creation in product settings and re-run the pipeline. 
            Vector metrics will be calculated during the indexing stage.
          </p>
        </div>
      ),
    },
    {
      category: 'troubleshooting',
      question: 'How do I change my embedding model?',
      answer: (
        <div className="space-y-2">
          <p className="text-gray-700">
            To change your embedding model:
          </p>
          <ol className="list-decimal list-inside space-y-2 text-gray-700 ml-4">
            <li>Go to your product → Settings tab (or Edit Product)</li>
            <li>Update the <code className="bg-gray-100 px-1 rounded">embedding_config</code>:
              <ul className="list-disc list-inside ml-6 mt-1 space-y-1">
                <li><code className="bg-gray-100 px-1 rounded">embedder_name</code>: Model name (e.g., "minilm", "text-embedding-3-small")</li>
                <li><code className="bg-gray-100 px-1 rounded">embedding_dimension</code>: Model dimension (e.g., 384, 768, 1536)</li>
              </ul>
            </li>
            <li>Save the changes</li>
            <li>Re-run the pipeline to generate new embeddings with the updated model</li>
          </ol>
          <p className="text-gray-700 text-sm bg-yellow-50 p-3 rounded-lg border border-yellow-200 mt-3">
            <strong>⚠️ Important:</strong> Changing the embedding model will require re-indexing all data. 
            This may take significant time for large datasets.
          </p>
        </div>
      ),
    },
  ]

  const categories = [
    { id: 'getting-started', name: 'Getting Started', icon: Play },
    { id: 'features', name: 'Features & Usage', icon: Sparkles },
    { id: 'metrics', name: 'Metrics Explained', icon: BarChart3 },
    { id: 'troubleshooting', name: 'Troubleshooting', icon: HelpCircle },
  ]

  const filteredItems = activeCategory 
    ? faqItems.filter(item => item.category === activeCategory)
    : faqItems

  return (
    <AppLayout>
      <div className="p-6 bg-gradient-to-br from-gray-50 via-blue-50/30 to-indigo-50/30 min-h-screen">
        <div className="max-w-6xl mx-auto">
          {/* Header */}
          <div className="mb-8">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-3 bg-gradient-to-br from-blue-600 to-indigo-600 rounded-lg">
                <BookOpen className="h-8 w-8 text-white" />
              </div>
              <div>
                <h1 className="text-3xl font-bold text-gray-900">Frequently Asked Questions</h1>
                <p className="text-gray-600 mt-1">Learn how to use AIRDOps and understand all metrics</p>
              </div>
            </div>
          </div>

          {/* Category Filter */}
          <div className="mb-8">
            <div className="flex flex-wrap gap-3">
              <button
                onClick={() => setActiveCategory(null)}
                className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                  activeCategory === null
                    ? 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white'
                    : 'bg-white text-gray-700 hover:bg-gray-50 border border-gray-200'
                }`}
              >
                All Questions
              </button>
              {categories.map((cat) => {
                const Icon = cat.icon
                return (
                  <button
                    key={cat.id}
                    onClick={() => setActiveCategory(cat.id)}
                    className={`px-4 py-2 rounded-lg font-medium transition-colors flex items-center gap-2 ${
                      activeCategory === cat.id
                        ? 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white'
                        : 'bg-white text-gray-700 hover:bg-gray-50 border border-gray-200'
                    }`}
                  >
                    <Icon className="h-4 w-4" />
                    {cat.name}
                  </button>
                )
              })}
            </div>
          </div>

          {/* Quick Start Guide */}
          {activeCategory === null || activeCategory === 'getting-started' ? (
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-8">
              <h2 className="text-xl font-semibold text-gray-900 mb-4 flex items-center gap-2">
                <Play className="h-5 w-5 text-blue-600" />
                Quick Start Guide
              </h2>
              <div className="grid md:grid-cols-3 gap-4">
                <div className="border border-gray-200 rounded-lg p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                      <span className="text-blue-600 font-bold">1</span>
                    </div>
                    <h3 className="font-semibold text-gray-900">Create Product</h3>
                  </div>
                  <p className="text-sm text-gray-600">Go to Products → New Product. Name it and optionally select a playbook.</p>
                </div>
                <div className="border border-gray-200 rounded-lg p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                      <span className="text-blue-600 font-bold">2</span>
                    </div>
                    <h3 className="font-semibold text-gray-900">Add Data Sources</h3>
                  </div>
                  <p className="text-sm text-gray-600">Connect your data (web, database, Confluence, SharePoint, or folder).</p>
                </div>
                <div className="border border-gray-200 rounded-lg p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                      <span className="text-blue-600 font-bold">3</span>
                    </div>
                    <h3 className="font-semibold text-gray-900">Run Pipeline</h3>
                  </div>
                  <p className="text-sm text-gray-600">Click "Run Pipeline" to process your data and generate metrics.</p>
                </div>
              </div>
            </div>
          ) : null}

          {/* FAQ Items */}
          <div className="space-y-4">
            {filteredItems.map((item, index) => {
              const itemId = `${item.category}-${index}`
              const isExpanded = expandedItems.has(itemId)
              return (
                <div
                  key={itemId}
                  className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden"
                >
                  <button
                    onClick={() => toggleItem(itemId)}
                    className="w-full px-6 py-4 flex items-center justify-between text-left hover:bg-gray-50 transition-colors"
                  >
                    <span className="font-semibold text-gray-900 pr-4">{item.question}</span>
                    {isExpanded ? (
                      <ChevronUp className="h-5 w-5 text-gray-400 flex-shrink-0" />
                    ) : (
                      <ChevronDown className="h-5 w-5 text-gray-400 flex-shrink-0" />
                    )}
                  </button>
                  {isExpanded && (
                    <div className="px-6 pb-4 pt-0 border-t border-gray-100">
                      <div className="pt-4 text-gray-700">{item.answer}</div>
                    </div>
                  )}
                </div>
              )
            })}
          </div>

          {/* Metrics Reference Section */}
          {activeCategory === null || activeCategory === 'metrics' ? (
            <div className="mt-12 bg-white rounded-xl shadow-sm border border-gray-200 p-8">
              <h2 className="text-2xl font-semibold text-gray-900 mb-6 flex items-center gap-2">
                <BarChart3 className="h-6 w-6 text-blue-600" />
                Complete Metrics Reference
              </h2>
              <p className="text-gray-600 mb-6">
                AIRDOps provides 26 comprehensive metrics organized into 5 categories. 
                All metrics are scored on a 0-100 scale, where higher scores indicate better quality.
              </p>
              
              <div className="space-y-6">
                {Object.entries(METRIC_CATEGORIES).map(([catKey, catConfig]) => {
                  const Icon = catConfig.icon
                  const isExpanded = expandedItems.has(`metric-category-${catKey}`)
                  return (
                    <div key={catKey} className="border-2 border-gray-200 rounded-xl overflow-hidden">
                      <button
                        onClick={() => toggleItem(`metric-category-${catKey}`)}
                        className="w-full px-6 py-4 flex items-center justify-between bg-gray-50 hover:bg-gray-100 transition-colors"
                      >
                        <div className="flex items-center gap-3">
                          <Icon className="h-5 w-5 text-blue-600" />
                          <h3 className="text-lg font-semibold text-gray-900">{catConfig.name}</h3>
                          <span className="text-sm text-gray-500">({catConfig.metrics.length} metrics)</span>
                        </div>
                        {isExpanded ? (
                          <ChevronUp className="h-5 w-5 text-gray-400" />
                        ) : (
                          <ChevronDown className="h-5 w-5 text-gray-400" />
                        )}
                      </button>
                      {isExpanded && (
                        <div className="p-6 bg-white">
                          {catConfig.note && (
                            <div className="mb-4 p-3 bg-amber-50 border border-amber-200 rounded-lg">
                              <p className="text-sm text-amber-800 flex items-start gap-2">
                                <Info className="h-4 w-4 mt-0.5 flex-shrink-0" />
                                <span>{catConfig.note}</span>
                              </p>
                            </div>
                          )}
                          <div className="grid md:grid-cols-2 gap-4">
                            {catConfig.metrics.map((metric) => (
                              <div key={metric.key} className="border border-gray-200 rounded-lg p-4 hover:bg-gray-50 transition-colors">
                                <h4 className="font-semibold text-gray-900 mb-2">{metric.name}</h4>
                                <p className="text-sm text-gray-600">{metric.description}</p>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>
          ) : null}

          {/* Still Need Help */}
          <div className="mt-12 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl border border-blue-200 p-6">
            <div className="flex items-start gap-4">
              <HelpCircle className="h-6 w-6 text-blue-600 flex-shrink-0 mt-1" />
              <div>
                <h3 className="font-semibold text-gray-900 mb-2">Still Need Help?</h3>
                <p className="text-gray-700 mb-3">
                  Can't find the answer you're looking for? Our support team is here to help.
                </p>
                <a
                  href="/app/support"
                  className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
                >
                  Contact Support
                </a>
              </div>
            </div>
          </div>
        </div>
      </div>
    </AppLayout>
  )
}

