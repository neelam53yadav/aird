'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { 
  HelpCircle, 
  BookOpen, 
  BarChart3, 
  Database, 
  Zap, 
  AlertTriangle, 
  CheckCircle2, 
  ChevronDown, 
  ChevronUp,
  Info,
  Lightbulb,
  Target,
  Rocket,
  TrendingUp,
  Shield,
  Layers,
  FileText,
  Sparkles,
  Cpu,
  Globe,
  Settings,
  Search,
  ArrowLeft
} from 'lucide-react'
import Link from 'next/link'
import { Button } from '@/components/ui/button'

export default function HelpPage() {
  const router = useRouter()
  
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    gettingStarted: true,
    understandingScores: true,  // Expanded by default for beginners
    metricsExplained: true,      // Expanded by default for beginners
    vectorization: false,
    troubleshooting: false,
    bestPractices: false,
  })

  const toggleSection = (section: string) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }))
  }

  const scrollTo = (id: string, expandKey?: string) => {
    if (expandKey) {
      setExpandedSections(prev => ({ ...prev, [expandKey]: true }))
    }
    // Let state update flush before scroll
    setTimeout(() => {
      const element = document.getElementById(id)
      if (element) {
        element.scrollIntoView({ behavior: 'smooth', block: 'start' })
      }
    }, 100)
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-white via-white to-rose-100">
      <div className="container mx-auto px-3 sm:px-4 lg:px-6 py-12 max-w-7xl">
        {/* Header */}
        <div className="text-center mb-12">
          <div className="inline-flex items-center justify-center w-20 h-20 bg-[#C8102E] rounded-full mb-6">
            <HelpCircle className="h-10 w-10 text-white" />
          </div>
          <h1 className="text-5xl font-bold text-gray-900 mb-4">Help Center</h1>
          <p className="text-xl text-gray-600 max-w-2xl mx-auto">
            Comprehensive guide to using PrimeData effectively
          </p>
        </div>

        {/* Top Actions */}
        <div className="flex items-center justify-between mb-8">
          <Button
            type="button"
            variant="outline"
            className="border-[#C8102E] text-[#C8102E] hover:bg-[#F5E6E8]"
            onClick={() => router.back()}
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back
          </Button>
        </div>

        <div className="flex flex-col lg:flex-row gap-8">
          {/* Left Sidebar Index */}
          <aside className="lg:w-72 flex-shrink-0">
            <div className="bg-white rounded-xl shadow-lg border-2 border-gray-200 p-5 sticky top-6">
              <h2 className="text-lg font-bold text-gray-900 mb-4">Topics</h2>
              <div className="space-y-2">
                <button
                  className="w-full text-left px-3 py-2 rounded-lg border border-gray-200 hover:border-[#C8102E] hover:bg-[#F5E6E8]/40 transition-all text-sm font-medium text-gray-900"
                  onClick={() => scrollTo('gettingStarted', 'gettingStarted')}
                >
                  Getting Started
                </button>
                <button
                  className="w-full text-left px-3 py-2 rounded-lg border border-gray-200 hover:border-[#C8102E] hover:bg-[#F5E6E8]/40 transition-all text-sm font-medium text-gray-900"
                  onClick={() => scrollTo('understandingScores', 'understandingScores')}
                >
                  Understanding Scores
                </button>
                <button
                  className="w-full text-left px-3 py-2 rounded-lg border border-gray-200 hover:border-[#C8102E] hover:bg-[#F5E6E8]/40 transition-all text-sm font-medium text-gray-900"
                  onClick={() => scrollTo('metricsExplained', 'metricsExplained')}
                >
                  Metrics Explained
                </button>
                <button
                  className="w-full text-left px-3 py-2 rounded-lg border border-gray-200 hover:border-[#C8102E] hover:bg-[#F5E6E8]/40 transition-all text-sm font-medium text-gray-900"
                  onClick={() => scrollTo('vectorization', 'vectorization')}
                >
                  Vectorization
                </button>
                <button
                  className="w-full text-left px-3 py-2 rounded-lg border border-gray-200 hover:border-[#C8102E] hover:bg-[#F5E6E8]/40 transition-all text-sm font-medium text-gray-900"
                  onClick={() => scrollTo('troubleshooting', 'troubleshooting')}
                >
                  Troubleshooting
                </button>
                <button
                  className="w-full text-left px-3 py-2 rounded-lg border border-gray-200 hover:border-[#C8102E] hover:bg-[#F5E6E8]/40 transition-all text-sm font-medium text-gray-900"
                  onClick={() => scrollTo('bestPractices', 'bestPractices')}
                >
                  Best Practices
                </button>
              </div>
            </div>
          </aside>

          {/* Main Content */}
          <div className="flex-1 space-y-6">
          {/* Getting Started */}
          <section id="gettingStarted" className="bg-white rounded-xl shadow-lg border-2 border-gray-200 p-8">
            <button
              onClick={() => toggleSection('gettingStarted')}
              className="w-full flex items-center justify-between text-left"
            >
              <h2 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
                <div className="bg-[#C8102E]/10 rounded-xl p-3">
                  <Rocket className="h-6 w-6 text-[#C8102E]" />
                </div>
                Getting Started
              </h2>
              {expandedSections.gettingStarted ? (
                <ChevronUp className="h-5 w-5 text-gray-400" />
              ) : (
                <ChevronDown className="h-5 w-5 text-gray-400" />
              )}
            </button>

            {expandedSections.gettingStarted && (
              <div className="mt-8 space-y-8 text-gray-700">
                <div className="bg-[#F5E6E8] border-l-4 border-[#C8102E] rounded-lg p-6">
                  <h3 className="text-lg font-bold text-gray-900 mb-4">Quick Start Guide</h3>
                  <ol className="space-y-4 list-decimal list-inside">
                    <li className="flex items-start gap-3">
                      <span className="flex-shrink-0 w-6 h-6 bg-[#C8102E] text-white rounded-full flex items-center justify-center text-sm font-bold">1</span>
                      <div>
                        <strong>Create a Data Product:</strong> Navigate to Products → New Product and provide a name and description.
                      </div>
                    </li>
                    <li className="flex items-start gap-3">
                      <span className="flex-shrink-0 w-6 h-6 bg-[#C8102E] text-white rounded-full flex items-center justify-center text-sm font-bold">2</span>
                      <div>
                        <strong>Add Data Sources:</strong> Connect your data sources (files, URLs, cloud storage).
                      </div>
                    </li>
                    <li className="flex items-start gap-3">
                      <span className="flex-shrink-0 w-6 h-6 bg-[#C8102E] text-white rounded-full flex items-center justify-center text-sm font-bold">3</span>
                      <div>
                        <strong>Configure Processing:</strong> Select a playbook and configure chunking/embedding settings.
                      </div>
                    </li>
                    <li className="flex items-start gap-3">
                      <span className="flex-shrink-0 w-6 h-6 bg-[#C8102E] text-white rounded-full flex items-center justify-center text-sm font-bold">4</span>
                      <div>
                        <strong>Run Pipeline:</strong> Start the AIRD pipeline to process your data.
                      </div>
                    </li>
                    <li className="flex items-start gap-3">
                      <span className="flex-shrink-0 w-6 h-6 bg-[#C8102E] text-white rounded-full flex items-center justify-center text-sm font-bold">5</span>
                      <div>
                        <strong>Review Scores:</strong> Check the AI Trust Score and detailed metrics.
                      </div>
                    </li>
                    <li className="flex items-start gap-3">
                      <span className="flex-shrink-0 w-6 h-6 bg-[#C8102E] text-white rounded-full flex items-center justify-center text-sm font-bold">6</span>
                      <div>
                        <strong>Export Vectors:</strong> Once ready, export your vector embeddings for use in RAG applications.
                      </div>
                    </li>
                    <li className="flex items-start gap-3">
                      <span className="flex-shrink-0 w-6 h-6 bg-[#C8102E] text-white rounded-full flex items-center justify-center text-sm font-bold">7</span>
                      <div>
                        <strong>Test in Playground:</strong> Use the Playground to test retrieval and RAG queries.
                      </div>
                    </li>
                  </ol>
                </div>

                <div className="bg-white border-2 border-gray-200 rounded-xl p-6">
                  <h3 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
                    <Database className="h-5 w-5 text-[#C8102E]" />
                    Data Processing Pipeline Architecture
                  </h3>
                  <p className="mb-4 text-gray-700">
                    PrimeData uses an 8-stage AIRD (AI-Ready Data) pipeline to transform raw data into production-ready AI assets:
                  </p>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="bg-[#F5E6E8] border-l-4 border-[#C8102E] rounded-lg p-4">
                      <h4 className="font-bold text-gray-900 mb-2">1. Ingestion</h4>
                      <p className="text-sm text-gray-700">Download/upload files to object storage and create metadata records.</p>
                    </div>
                    <div className="bg-[#F5E6E8] border-l-4 border-[#C8102E] rounded-lg p-4">
                      <h4 className="font-bold text-gray-900 mb-2">2. Preprocessing</h4>
                      <p className="text-sm text-gray-700">Text normalization, OCR correction, metadata extraction, content type detection.</p>
                    </div>
                    <div className="bg-[#F5E6E8] border-l-4 border-[#C8102E] rounded-lg p-4">
                      <h4 className="font-bold text-gray-900 mb-2">3. Chunking</h4>
                      <p className="text-sm text-gray-700">Intelligent document chunking with multiple strategies (fixed-size, semantic, recursive).</p>
                    </div>
                    <div className="bg-[#F5E6E8] border-l-4 border-[#C8102E] rounded-lg p-4">
                      <h4 className="font-bold text-gray-900 mb-2">4. Scoring</h4>
                      <p className="text-sm text-gray-700">15+ dimensional quality metrics and trust score calculation.</p>
                    </div>
                    <div className="bg-[#F5E6E8] border-l-4 border-[#C8102E] rounded-lg p-4">
                      <h4 className="font-bold text-gray-900 mb-2">5. Embedding</h4>
                      <p className="text-sm text-gray-700">Generate vector embeddings using OpenAI or open-source models.</p>
                    </div>
                    <div className="bg-[#F5E6E8] border-l-4 border-[#C8102E] rounded-lg p-4">
                      <h4 className="font-bold text-gray-900 mb-2">6. Indexing</h4>
                      <p className="text-sm text-gray-700">Store vectors in Qdrant vector database with metadata.</p>
                    </div>
                    <div className="bg-[#F5E6E8] border-l-4 border-[#C8102E] rounded-lg p-4">
                      <h4 className="font-bold text-gray-900 mb-2">7. Fingerprinting</h4>
                      <p className="text-sm text-gray-700">Generate comprehensive AI readiness fingerprint with all metrics.</p>
                    </div>
                    <div className="bg-[#F5E6E8] border-l-4 border-[#C8102E] rounded-lg p-4">
                      <h4 className="font-bold text-gray-900 mb-2">8. Validation</h4>
                      <p className="text-sm text-gray-700">Data quality validation and policy compliance checks.</p>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </section>

          {/* Understanding Scores */}
          <section id="understandingScores" className="bg-white rounded-xl shadow-lg border-2 border-gray-200 p-8">
            <button
              onClick={() => toggleSection('understandingScores')}
              className="w-full flex items-center justify-between text-left"
            >
              <h2 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
                <div className="bg-[#C8102E]/10 rounded-xl p-3">
                  <BarChart3 className="h-6 w-6 text-[#C8102E]" />
                </div>
                Understanding Scores
              </h2>
              {expandedSections.understandingScores ? (
                <ChevronUp className="h-5 w-5 text-gray-400" />
              ) : (
                <ChevronDown className="h-5 w-5 text-gray-400" />
              )}
            </button>

            {expandedSections.understandingScores && (
              <div className="mt-8 space-y-8 text-gray-700">
                {/* Beginner-friendly Score Interpretation Guide */}
                <div className="bg-[#F5E6E8] border-l-4 border-[#C8102E] rounded-lg p-6">
                  <h3 className="text-lg font-bold text-gray-900 mb-3">📊 How to Read Scores (0-100%)</h3>
                  <p className="text-sm text-gray-700 mb-4">
                    All metrics and scores are displayed as percentages from 0% to 100%. Here's what each range means:
                  </p>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                    <div className="bg-white rounded-lg p-4 border-2 border-green-300">
                      <div className="flex items-center gap-2 mb-2">
                        <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                        <strong className="text-gray-900">90-100%</strong>
                      </div>
                      <p className="text-sm text-gray-700">Excellent - Production-ready quality. Safe to use in production AI applications.</p>
                    </div>
                    <div className="bg-white rounded-lg p-4 border-2 border-blue-300">
                      <div className="flex items-center gap-2 mb-2">
                        <div className="w-3 h-3 bg-blue-500 rounded-full"></div>
                        <strong className="text-gray-900">75-89%</strong>
                      </div>
                      <p className="text-sm text-gray-700">Good - Minor improvements recommended. Generally acceptable for production use.</p>
                    </div>
                    <div className="bg-white rounded-lg p-4 border-2 border-yellow-300">
                      <div className="flex items-center gap-2 mb-2">
                        <div className="w-3 h-3 bg-yellow-500 rounded-full"></div>
                        <strong className="text-gray-900">60-74%</strong>
                      </div>
                      <p className="text-sm text-gray-700">Fair - Quality issues may affect retrieval and RAG outputs. Review recommended.</p>
                    </div>
                    <div className="bg-white rounded-lg p-4 border-2 border-red-300">
                      <div className="flex items-center gap-2 mb-2">
                        <div className="w-3 h-3 bg-red-500 rounded-full"></div>
                        <strong className="text-gray-900">&lt; 60%</strong>
                      </div>
                      <p className="text-sm text-gray-700">Needs Work - Significant improvements required before production use.</p>
                    </div>
                  </div>
                  <div className="bg-white rounded-lg p-4 border border-[#C8102E]/30">
                    <p className="text-sm font-semibold text-[#C8102E] mb-2">💡 Quick Tip for Beginners:</p>
                    <p className="text-sm text-gray-700">
                      Focus first on <strong>Security</strong>, <strong>Completeness</strong>, and <strong>Embedding Success Rate</strong>. 
                      These are "hard blockers" - if any of these fail, your data won't work well in AI applications.
                    </p>
                  </div>
                </div>

                <div className="bg-white border-2 border-gray-200 rounded-xl p-6">
                  <h3 className="text-xl font-bold text-gray-900 mb-4">AI Trust Score</h3>
                  <p className="mb-4 text-gray-700">
                    The AI Trust Score is a comprehensive metric (0-100%) that evaluates your data's readiness for AI applications. It combines:
                  </p>
                  <ul className="list-disc list-inside space-y-2 ml-4 text-gray-700 mb-6">
                    <li><strong>Data Quality Metrics</strong> (Completeness, Accuracy, Security, Quality, Timeliness, Token Count, GPT Confidence, Context Quality, Metadata Presence, Audience Intentionality, Diversity, Audience Accessibility, Knowledge Base Ready)</li>
                    <li><strong>AI-Ready Metrics</strong> (Chunk Coherence, Noise-Free Score, Chunk Boundary Quality)</li>
                    <li><strong>Vector Metrics</strong> (Dimension Consistency, Vector Quality, Embedding Success Rate, Model Health, Semantic Search Readiness)</li>
                    <li><strong>RAG Metrics</strong> (Retrieval Recall@K, Average Precision@K, Query Coverage)</li>
                  </ul>
                  
                  <div className="bg-blue-50 border-l-4 border-blue-500 rounded-lg p-4 mb-6">
                    <h4 className="font-bold text-gray-900 mb-3">Overall AI Trust Score Formula</h4>
                    <div className="bg-white rounded-lg p-3 font-mono text-xs text-gray-800 mb-3">
                      <strong>AI Trust Score = Σ(metric<sub>i</sub> × weight<sub>i</sub>)</strong>
                      <br />where i ranges over all metrics
                      <br />All weights sum to 1.0 (100%)
                    </div>
                    <p className="text-sm text-gray-700">
                      Each metric is normalized to 0-100 scale and multiplied by its configured weight. The sum of all weighted metrics gives the final AI Trust Score.
                    </p>
                  </div>
                </div>

                <div className="bg-white border-2 border-gray-200 rounded-xl p-6">
                  <h3 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
                    <div className="flex-shrink-0 w-7 h-7 bg-[#C8102E] text-white rounded-full flex items-center justify-center text-sm font-bold">1</div>
                    Step 1: Chunk-Level Scoring
                  </h3>
                  <div className="space-y-4">
                    <p className="text-sm text-gray-700 mb-4">
                      Each text chunk is evaluated against 13 core data quality metrics (0-100 scale). Each metric is calculated independently using specific algorithms:
                    </p>
                    
                    <div className="bg-[#F5E6E8] border-l-4 border-[#C8102E] rounded-lg p-4">
                      <p className="font-semibold text-gray-900 mb-2">Chunk-Level Metric Calculation</p>
                      <div className="bg-white rounded-lg p-3 font-mono text-xs text-gray-800 mb-2">
                        For each chunk c:
                        <br />Completeness(c) = 100 if len(c.strip()) &gt; 0, else 0
                        <br />Security(c) = 100 if PII_detected == 0, else 75
                        <br />Quality(c) = f(avg_sentence_length, reading_ease, vocabulary_diversity)
                        <br />Accuracy(c) = (valid_patterns / total_patterns) × 100
                        <br />Context_Quality(c) = base_score + structure_bonus + info_density
                        <br />Metadata_Presence(c) = (populated_fields / expected_fields) × 100
                        <br />... (see Metrics Explained section for full formulas)
                      </div>
                      <p className="text-xs text-gray-600 mt-2">
                        All metrics are calculated on a per-chunk basis, producing a score between 0-100 for each metric.
                      </p>
                    </div>
                  </div>
                </div>

                <div className="bg-white border-2 border-gray-200 rounded-xl p-6">
                  <h3 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
                    <div className="flex-shrink-0 w-7 h-7 bg-[#C8102E] text-white rounded-full flex items-center justify-center text-sm font-bold">2</div>
                    Step 2: Chunk-Level AI Trust Score
                  </h3>
                  <div className="space-y-4">
                    <p className="text-sm text-gray-700 mb-4">
                      A weighted average of all chunk-level metrics creates the chunk's AI Trust Score. Default weights are configurable via <code className="bg-gray-100 px-1 rounded text-xs">backend/config/scoring_weights.json</code>.
                    </p>
                    
                    <div className="bg-[#F5E6E8] border-l-4 border-[#C8102E] rounded-lg p-4">
                      <p className="font-semibold text-gray-900 mb-2">Chunk AI Trust Score Formula</p>
                      <div className="bg-white rounded-lg p-3 font-mono text-xs text-gray-800 mb-2">
                        <strong>Chunk_AI_Trust_Score(c) = Σ(metric<sub>i</sub>(c) × weight<sub>i</sub>)</strong>
                        <br />where:
                        <br />- c = chunk
                        <br />- i ranges over all 13 data quality metrics
                        <br />- weight<sub>i</sub> = configured weight for metric i (default: 1/13 ≈ 0.077)
                        <br />- Σ weight<sub>i</sub> = 1.0 (weights normalized)
                      </div>
                      <p className="text-xs text-gray-600 mt-2">
                        <strong>Example:</strong> If a chunk has Completeness=100, Security=100, Quality=80, and all other metrics=75 with equal weights (1/13):
                        <br />Chunk_AI_Trust_Score = (100×1/13) + (100×1/13) + (80×1/13) + ... + (75×1/13) ≈ 82.3
                      </p>
                    </div>
                  </div>
                </div>

                <div className="bg-white border-2 border-gray-200 rounded-xl p-6">
                  <h3 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
                    <div className="flex-shrink-0 w-7 h-7 bg-[#C8102E] text-white rounded-full flex items-center justify-center text-sm font-bold">3</div>
                    Step 3: Product-Level Aggregation
                  </h3>
                  <div className="space-y-4">
                    <p className="text-sm text-gray-700 mb-4">
                      Chunk scores are aggregated to produce product-level metrics using arithmetic mean (average) across all chunks.
                    </p>
                    
                    <div className="bg-[#F5E6E8] border-l-4 border-[#C8102E] rounded-lg p-4">
                      <p className="font-semibold text-gray-900 mb-2">Product-Level Metric Aggregation</p>
                      <div className="bg-white rounded-lg p-3 font-mono text-xs text-gray-800 mb-2">
                        <strong>Product_Metric = (1/n) × Σ metric(c<sub>j</sub>)</strong>
                        <br />where:
                        <br />- n = total number of chunks
                        <br />- j ranges from 0 to n-1
                        <br />- metric(c<sub>j</sub>) = metric value for chunk j
                      </div>
                      <p className="text-xs text-gray-600 mt-2">
                        <strong>Example:</strong> If you have 100 chunks with Quality scores: [80, 85, 75, 90, ...]
                        <br />Product_Quality = (80 + 85 + 75 + 90 + ...) / 100 = 81.5
                      </p>
                      <p className="text-xs text-gray-600 mt-2">
                        This applies to all 13 data quality metrics, producing product-level averages for each metric.
                      </p>
                    </div>
                  </div>
                </div>

                <div className="bg-white border-2 border-gray-200 rounded-xl p-6">
                  <h3 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
                    <div className="flex-shrink-0 w-7 h-7 bg-[#C8102E] text-white rounded-full flex items-center justify-center text-sm font-bold">4</div>
                    Step 4: AI-Ready & Vector Metrics
                  </h3>
                  <div className="space-y-4">
                    <p className="text-sm text-gray-700 mb-4">
                      After chunking and indexing, AI-Ready metrics and Vector metrics are calculated at the product level.
                    </p>
                    
                    <div className="bg-[#F5E6E8] border-l-4 border-[#C8102E] rounded-lg p-4 mb-4">
                      <p className="font-semibold text-gray-900 mb-2">AI-Ready Metrics</p>
                      <div className="bg-white rounded-lg p-3 font-mono text-xs text-gray-800 mb-2">
                        <strong>Chunk Coherence:</strong> (1/n) × Σ cos_sim(sentence<sub>i</sub>, sentence<sub>i+1</sub>)
                        <br /><strong>Noise-Free Score:</strong> (clean_content_length / total_content_length) × 100
                        <br /><strong>Boundary Quality:</strong> 100 - (mid_sentence_breaks / total_boundaries) × 100
                      </div>
                    </div>
                    
                    <div className="bg-[#F5E6E8] border-l-4 border-[#C8102E] rounded-lg p-4">
                      <p className="font-semibold text-gray-900 mb-2">Vector Metrics (Post-Indexing)</p>
                      <div className="bg-white rounded-lg p-3 font-mono text-xs text-gray-800 mb-2">
                        <strong>Dimension Consistency:</strong> (vectors_with_correct_dim / total_vectors) × 100
                        <br /><strong>Success Rate:</strong> (successfully_embedded_chunks / total_chunks) × 100
                        <br /><strong>Vector Quality:</strong> 0.4×valid_ratio + 0.3×non_zero_ratio + 0.3×norm_health
                        <br /><strong>Model Health:</strong> f(embedding_variance, outlier_rate, api_error_rate)
                        <br /><strong>Semantic Search Readiness:</strong> 0.25×dim_consistency + 0.35×vector_quality + 0.25×model_health + 0.15×success_rate
                      </div>
                      <p className="text-xs text-gray-600 mt-2">
                        These metrics require successful vector indexing and are calculated after embeddings are generated and stored.
                      </p>
                    </div>
                  </div>
                </div>

                <div className="bg-white border-2 border-gray-200 rounded-xl p-6">
                  <h3 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
                    <div className="flex-shrink-0 w-7 h-7 bg-[#C8102E] text-white rounded-full flex items-center justify-center text-sm font-bold">5</div>
                    Step 5: Final AI Trust Score Calculation
                  </h3>
                  <div className="space-y-4">
                    <p className="text-sm text-gray-700 mb-4">
                      The final AI Trust Score combines all aggregated metrics (data quality, AI-ready, vector, and RAG metrics) with their respective weights.
                    </p>
                    
                    <div className="bg-[#F5E6E8] border-l-4 border-[#C8102E] rounded-lg p-4">
                      <p className="font-semibold text-gray-900 mb-2">Final AI Trust Score Formula</p>
                      <div className="bg-white rounded-lg p-3 font-mono text-xs text-gray-800 mb-2">
                        <strong>AI_Trust_Score = </strong>
                        <br />  (Data_Quality_Score × w<sub>dq</sub>) +
                        <br />  (AI_Ready_Score × w<sub>ar</sub>) +
                        <br />  (Vector_Score × w<sub>vec</sub>) +
                        <br />  (RAG_Score × w<sub>rag</sub>)
                        <br />
                        <br />where:
                        <br />- Data_Quality_Score = Σ(data_quality_metric<sub>i</sub> × w<sub>i</sub>)
                        <br />- AI_Ready_Score = (Coherence + Noise_Free + Boundary_Quality) / 3
                        <br />- Vector_Score = Semantic_Search_Readiness (if available, else 0)
                        <br />- RAG_Score = (Recall@K + Precision@K + Query_Coverage) / 3 (if available, else 0)
                        <br />- w<sub>dq</sub> + w<sub>ar</sub> + w<sub>vec</sub> + w<sub>rag</sub> = 1.0
                      </div>
                      <p className="text-xs text-gray-600 mt-2">
                        <strong>Default Weights:</strong> Data Quality (60%), AI-Ready (25%), Vector (10%), RAG (5%)
                        <br />If vector/RAG metrics are not calculated (0% or not evaluated), their weights are redistributed proportionally.
                      </p>
                      <p className="text-xs text-gray-600 mt-2">
                        <strong>Final Score Range:</strong> 0-100%, where 100% indicates perfect AI readiness across all dimensions.
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </section>

          {/* Metrics Explained */}
          <section id="metricsExplained" className="bg-white rounded-xl shadow-lg border-2 border-gray-200 p-8">
            <button
              onClick={() => toggleSection('metricsExplained')}
              className="w-full flex items-center justify-between text-left"
            >
              <h2 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
                <div className="bg-[#C8102E]/10 rounded-xl p-3">
                  <Target className="h-6 w-6 text-[#C8102E]" />
                </div>
                Metrics Explained
              </h2>
              {expandedSections.metricsExplained ? (
                <ChevronUp className="h-5 w-5 text-gray-400" />
              ) : (
                <ChevronDown className="h-5 w-5 text-gray-400" />
              )}
            </button>

            {expandedSections.metricsExplained && (
              <div className="mt-8 space-y-6">
                {/* Governance Metrics */}
                <div className="bg-white border-2 border-blue-200 rounded-xl p-6">
                  <h3 className="text-xl font-bold text-gray-900 mb-6 flex items-center gap-3">
                    <Shield className="h-6 w-6 text-[#C8102E]" />
                    Governance & Compliance Metrics
                  </h3>
                  <div className="space-y-6">
                    <div className="bg-blue-50 border-l-4 border-blue-500 rounded-lg p-5">
                      <h4 className="font-bold text-gray-900 mb-3">Security (Secure)</h4>
                      <p className="text-sm text-gray-700 mb-3">
                        <strong>Description:</strong> Evaluates data privacy and security compliance by detecting personally identifiable information (PII).
                      </p>
                      <p className="text-sm text-gray-700 mb-3">
                        <strong>Calculation:</strong> Binary classification based on PII detection patterns (emails, phone numbers, SSN, credit card numbers).
                      </p>
                      <div className="bg-white rounded-lg p-3 mb-3 font-mono text-xs text-gray-800">
                        <strong>Formula:</strong> Security = 100% if PII_count == 0, else 75% (penalty for detected PII)
                      </div>
                      <p className="text-xs text-gray-600">
                        <strong>Threshold:</strong> ≥ 95% = Excellent, ≥ 75% = Good, &lt; 75% = Needs Review
                      </p>
                    </div>

                    <div className="bg-blue-50 border-l-4 border-blue-500 rounded-lg p-5">
                      <h4 className="font-bold text-gray-900 mb-3">Completeness</h4>
                      <p className="text-sm text-gray-700 mb-3">
                        <strong>Description:</strong> Measures how complete and non-empty the content is. Essential for data quality assessment.
                      </p>
                      <p className="text-sm text-gray-700 mb-3">
                        <strong>Calculation:</strong> Content presence validation based on text length and non-whitespace characters.
                      </p>
                      <div className="bg-white rounded-lg p-3 mb-3 font-mono text-xs text-gray-800">
                        <strong>Formula:</strong> Completeness = 100% if len(text.strip()) &gt; 0, else 0%
                      </div>
                      <p className="text-xs text-gray-600">
                        <strong>Threshold:</strong> 100% = Required (non-negotiable for valid content)
                      </p>
                    </div>

                    <div className="bg-blue-50 border-l-4 border-blue-500 rounded-lg p-5">
                      <h4 className="font-bold text-gray-900 mb-3">Accuracy</h4>
                      <p className="text-sm text-gray-700 mb-3">
                        <strong>Description:</strong> Validates information accuracy using domain-specific rules and pattern matching. Assesses data integrity.
                      </p>
                      <p className="text-sm text-gray-700 mb-3">
                        <strong>Calculation:</strong> Rule-based validation score considering format compliance, data type consistency, and logical constraints.
                      </p>
                      <div className="bg-white rounded-lg p-3 mb-3 font-mono text-xs text-gray-800">
                        <strong>Formula:</strong> Accuracy = (valid_patterns / total_patterns) × 100
                      </div>
                      <p className="text-xs text-gray-600">
                        <strong>Threshold:</strong> ≥ 90% = Excellent, ≥ 75% = Good, &lt; 75% = Needs Improvement
                      </p>
                    </div>

                    <div className="bg-blue-50 border-l-4 border-blue-500 rounded-lg p-5">
                      <h4 className="font-bold text-gray-900 mb-3">Metadata Presence</h4>
                      <p className="text-sm text-gray-700 mb-3">
                        <strong>Description:</strong> Quantifies the presence and richness of metadata (source, timestamp, section, author, etc.). Critical for traceability.
                      </p>
                      <p className="text-sm text-gray-700 mb-3">
                        <strong>Calculation:</strong> Percentage of expected metadata fields populated with non-null values.
                      </p>
                      <div className="bg-white rounded-lg p-3 mb-3 font-mono text-xs text-gray-800">
                        <strong>Formula:</strong> Metadata_Presence = (populated_fields / expected_fields) × 100
                      </div>
                      <p className="text-xs text-gray-600">
                        <strong>Threshold:</strong> ≥ 80% = Excellent, ≥ 60% = Good, &lt; 60% = Needs Enhancement
                      </p>
                    </div>
                  </div>
                </div>

                {/* Content Quality Metrics */}
                <div className="bg-white border-2 border-green-200 rounded-xl p-6">
                  <h3 className="text-xl font-bold text-gray-900 mb-6 flex items-center gap-3">
                    <FileText className="h-6 w-6 text-[#C8102E]" />
                    Content Quality Metrics
                  </h3>
                  <div className="space-y-6">
                    <div className="bg-green-50 border-l-4 border-green-500 rounded-lg p-5">
                      <h4 className="font-bold text-gray-900 mb-3">Quality</h4>
                      <p className="text-sm text-gray-700 mb-3">
                        <strong>Description:</strong> Overall content quality based on readability metrics, sentence structure, and linguistic patterns. Uses industry-standard readability formulas.
                      </p>
                      <p className="text-sm text-gray-700 mb-3">
                        <strong>Calculation:</strong> Composite score using Flesch Reading Ease, average sentence length (optimal: 10-30 words), and vocabulary diversity.
                      </p>
                      <div className="bg-white rounded-lg p-3 mb-3 font-mono text-xs text-gray-800">
                        <strong>Formula:</strong> Quality = f(avg_sentence_length, reading_ease_score, vocabulary_richness)
                        <br />where optimal sentence length ∈ [10, 30] words
                      </div>
                      <p className="text-xs text-gray-600">
                        <strong>Threshold:</strong> ≥ 80% = Excellent, ≥ 65% = Good, &lt; 65% = Needs Improvement
                      </p>
                    </div>

                    <div className="bg-green-50 border-l-4 border-green-500 rounded-lg p-5">
                      <h4 className="font-bold text-gray-900 mb-3">Context Quality</h4>
                      <p className="text-sm text-gray-700 mb-3">
                        <strong>Description:</strong> Evaluates the richness and informativeness of context within chunks. Measures structural elements, references, and information density.
                      </p>
                      <p className="text-sm text-gray-700 mb-3">
                        <strong>Calculation:</strong> Weighted score combining structure indicators (paragraphs, lists), information density (numbers, dates, references), and contextual keywords.
                      </p>
                      <div className="bg-white rounded-lg p-3 mb-3 font-mono text-xs text-gray-800">
                        <strong>Formula:</strong> Context_Quality = base_score(40%) + structure_bonus(20%) + info_density(15%) + references(10%) + contextual_keywords(15%)
                      </div>
                      <p className="text-xs text-gray-600">
                        <strong>Threshold:</strong> ≥ 85% = Excellent, ≥ 70% = Good, &lt; 70% = Needs Enhancement
                      </p>
                    </div>

                    <div className="bg-green-50 border-l-4 border-green-500 rounded-lg p-5">
                      <h4 className="font-bold text-gray-900 mb-3">Audience Intentionality</h4>
                      <p className="text-sm text-gray-700 mb-3">
                        <strong>Description:</strong> Measures how well content targets its intended audience through appropriate language, terminology, and complexity level.
                      </p>
                      <p className="text-sm text-gray-700 mb-3">
                        <strong>Calculation:</strong> Domain-specific terminology matching, complexity alignment with target audience, and audience-specific language patterns.
                      </p>
                      <div className="bg-white rounded-lg p-3 mb-3 font-mono text-xs text-gray-800">
                        <strong>Formula:</strong> Audience_Intentionality = (matched_terminology + complexity_alignment + language_patterns) / 3 × 100
                      </div>
                      <p className="text-xs text-gray-600">
                        <strong>Threshold:</strong> ≥ 70% = Excellent, ≥ 55% = Good, &lt; 55% = Needs Targeting
                      </p>
                    </div>

                    <div className="bg-green-50 border-l-4 border-green-500 rounded-lg p-5">
                      <h4 className="font-bold text-gray-900 mb-3">Diversity</h4>
                      <p className="text-sm text-gray-700 mb-3">
                        <strong>Description:</strong> Type-Token Ratio (TTR) measuring vocabulary diversity. Higher diversity indicates richer, more varied content.
                      </p>
                      <p className="text-sm text-gray-700 mb-3">
                        <strong>Calculation:</strong> Ratio of unique words to total words, normalized for text length. Industry-standard lexical diversity metric.
                      </p>
                      <div className="bg-white rounded-lg p-3 mb-3 font-mono text-xs text-gray-800">
                        <strong>Formula:</strong> Diversity = (unique_tokens / total_tokens) × 100
                        <br />TTR = |unique_words| / |total_words|
                      </div>
                      <p className="text-xs text-gray-600">
                        <strong>Threshold:</strong> ≥ 60% = Excellent, ≥ 45% = Good, &lt; 45% = Low Diversity
                      </p>
                    </div>

                    <div className="bg-green-50 border-l-4 border-green-500 rounded-lg p-5">
                      <h4 className="font-bold text-gray-900 mb-3">Audience Accessibility</h4>
                      <p className="text-sm text-gray-700 mb-3">
                        <strong>Description:</strong> Measures content accessibility based on average sentence length. Optimal sentence length (10-25 words) improves readability.
                      </p>
                      <p className="text-sm text-gray-700 mb-3">
                        <strong>Calculation:</strong> Penalty function based on deviation from optimal sentence length (17.5 words average).
                      </p>
                      <div className="bg-white rounded-lg p-3 mb-3 font-mono text-xs text-gray-800">
                        <strong>Formula:</strong> Accessibility = 100% if 10 ≤ avg_sentence_length ≤ 25, else 100% - min(|avg_sl - 17.5| / 25, 1) × 100
                      </div>
                      <p className="text-xs text-gray-600">
                        <strong>Threshold:</strong> ≥ 80% = Excellent, ≥ 65% = Good, &lt; 65% = Needs Simplification
                      </p>
                    </div>

                    <div className="bg-green-50 border-l-4 border-green-500 rounded-lg p-5">
                      <h4 className="font-bold text-gray-900 mb-3">Timeliness</h4>
                      <p className="text-sm text-gray-700 mb-3">
                        <strong>Description:</strong> Evaluates content currency and recency. Measures temporal relevance for time-sensitive applications.
                      </p>
                      <p className="text-sm text-gray-700 mb-3">
                        <strong>Calculation:</strong> Exponential decay based on days since content creation, normalized to 0-100 scale.
                      </p>
                      <div className="bg-white rounded-lg p-3 mb-3 font-mono text-xs text-gray-800">
                        <strong>Formula:</strong> Timeliness = max(0, (1 - days_since_creation / 365) × 100)
                      </div>
                      <p className="text-xs text-gray-600">
                        <strong>Threshold:</strong> ≥ 75% = Recent (&lt; 90 days), ≥ 50% = Acceptable (&lt; 180 days), &lt; 50% = Stale
                      </p>
                    </div>

                    <div className="bg-green-50 border-l-4 border-green-500 rounded-lg p-5">
                      <h4 className="font-bold text-gray-900 mb-3">Knowledge Base Ready</h4>
                      <p className="text-sm text-gray-700 mb-3">
                        <strong>Description:</strong> Composite readiness score for knowledge base ingestion. Combines metadata, quality, and context quality.
                      </p>
                      <p className="text-sm text-gray-700 mb-3">
                        <strong>Calculation:</strong> Weighted combination of metadata presence (40%), content quality (40%), and context quality (20%).
                      </p>
                      <div className="bg-white rounded-lg p-3 mb-3 font-mono text-xs text-gray-800">
                        <strong>Formula:</strong> KBR = 0.4 × Metadata_Presence + 0.4 × Quality + 0.2 × Context_Quality
                      </div>
                      <p className="text-xs text-gray-600">
                        <strong>Threshold:</strong> ≥ 85% = Ready, ≥ 70% = Acceptable, &lt; 70% = Needs Improvement
                      </p>
                    </div>

                    <div className="bg-green-50 border-l-4 border-green-500 rounded-lg p-5">
                      <h4 className="font-bold text-gray-900 mb-3">Token Count</h4>
                      <p className="text-sm text-gray-700 mb-3">
                        <strong>Description:</strong> Normalized token count for chunk size assessment. Critical for embedding model compatibility and cost estimation.
                      </p>
                      <p className="text-sm text-gray-700 mb-3">
                        <strong>Calculation:</strong> Token count using tokenizer (WordPiece, BPE, or SentencePiece) normalized to 0-1000 token range.
                      </p>
                      <div className="bg-white rounded-lg p-3 mb-3 font-mono text-xs text-gray-800">
                        <strong>Formula:</strong> Token_Count = tokens_per_chunk (raw count, not percentage)
                        <br />Optimal range: 200-800 tokens per chunk
                      </div>
                      <p className="text-xs text-gray-600">
                        <strong>Threshold:</strong> 200-800 tokens = Optimal, 100-200 or 800-1200 = Acceptable, outside range = Needs Adjustment
                      </p>
                    </div>
                  </div>
                </div>

                {/* Chunking Metrics */}
                <div className="bg-white border-2 border-purple-200 rounded-xl p-6">
                  <h3 className="text-xl font-bold text-gray-900 mb-6 flex items-center gap-3">
                    <Layers className="h-6 w-6 text-[#C8102E]" />
                    Chunking & Structure Metrics
                  </h3>
                  <div className="space-y-6">
                    <div className="bg-purple-50 border-l-4 border-purple-500 rounded-lg p-5">
                      <h4 className="font-bold text-gray-900 mb-3">Chunk Coherence</h4>
                      <p className="text-sm text-gray-700 mb-3">
                        <strong>Description:</strong> Measures semantic cohesion within chunks using cosine similarity between consecutive sentences. Higher coherence improves retrieval quality.
                      </p>
                      <p className="text-sm text-gray-700 mb-3">
                        <strong>Calculation:</strong> Average cosine similarity of sentence embeddings within a sliding window (default: 3 sentences). Uses embedding models (MiniLM, MPNet) or fallback n-gram similarity.
                      </p>
                      <div className="bg-white rounded-lg p-3 mb-3 font-mono text-xs text-gray-800">
                        <strong>Formula:</strong> Coherence = (1/n) × Σ cos_sim(sentence<sub>i</sub>, sentence<sub>i+1</sub>)
                        <br />where cos_sim(a, b) = (a · b) / (||a|| × ||b||)
                        <br />Note: i ranges from 0 to n-1, where n is the number of sentences
                      </div>
                      <p className="text-xs text-gray-600">
                        <strong>Threshold:</strong> ≥ 0.7 = Excellent, ≥ 0.5 = Good, &lt; 0.5 = Low Coherence (domain-dependent)
                      </p>
                    </div>

                    <div className="bg-purple-50 border-l-4 border-purple-500 rounded-lg p-5">
                      <h4 className="font-bold text-gray-900 mb-3">Noise-Free Score</h4>
                      <p className="text-sm text-gray-700 mb-3">
                        <strong>Description:</strong> Percentage of content free from boilerplate, navigation elements, headers, footers, and other non-informative noise.
                      </p>
                      <p className="text-sm text-gray-700 mb-3">
                        <strong>Calculation:</strong> Ratio of clean content to total content after removing noise patterns (copyright notices, navigation menus, page numbers, etc.).
                      </p>
                      <div className="bg-white rounded-lg p-3 mb-3 font-mono text-xs text-gray-800">
                        <strong>Formula:</strong> Noise_Free_Score = (clean_content_length / total_content_length) × 100
                        <br />clean_content = total_content - noise_pattern_matches
                      </div>
                      <p className="text-xs text-gray-600">
                        <strong>Threshold:</strong> ≥ 95% = Excellent, ≥ 85% = Good, &lt; 85% = Needs Cleaning
                      </p>
                    </div>

                    <div className="bg-purple-50 border-l-4 border-purple-500 rounded-lg p-5">
                      <h4 className="font-bold text-gray-900 mb-3">Chunk Boundary Quality</h4>
                      <p className="text-sm text-gray-700 mb-3">
                        <strong>Description:</strong> Measures quality of chunk boundaries. Fewer mid-sentence breaks indicate better boundary placement, preserving semantic integrity.
                      </p>
                      <p className="text-sm text-gray-700 mb-3">
                        <strong>Calculation:</strong> Inverse of mid-sentence boundary rate. Penalizes chunks that split sentences inappropriately.
                      </p>
                      <div className="bg-white rounded-lg p-3 mb-3 font-mono text-xs text-gray-800">
                        <strong>Formula:</strong> Boundary_Quality = 100% - (mid_sentence_breaks / total_boundaries) × 100
                        <br />Ideal: 0% mid-sentence breaks = 100% score
                      </div>
                      <p className="text-xs text-gray-600">
                        <strong>Threshold:</strong> ≥ 95% = Excellent, ≥ 85% = Good, &lt; 85% = Needs Boundary Adjustment
                      </p>
                    </div>
                  </div>
                </div>

                {/* Vector Metrics */}
                <div className="bg-white border-2 border-orange-200 rounded-xl p-6">
                  <h3 className="text-xl font-bold text-gray-900 mb-6 flex items-center gap-3">
                    <Database className="h-6 w-6 text-[#C8102E]" />
                    Vector & Embedding Metrics
                  </h3>
                  <div className="space-y-6">
                    <div className="bg-orange-50 border-l-4 border-orange-500 rounded-lg p-5">
                      <h4 className="font-bold text-gray-900 mb-3">Embedding Dimension Consistency</h4>
                      <p className="text-sm text-gray-700 mb-3">
                        <strong>Description:</strong> Percentage of vectors with expected embedding dimension. Critical for vector database compatibility and retrieval consistency.
                      </p>
                      <p className="text-sm text-gray-700 mb-3">
                        <strong>Calculation:</strong> Ratio of vectors with correct dimension (e.g., 384 for MiniLM, 1536 for OpenAI ada-002) to total vectors.
                      </p>
                      <div className="bg-white rounded-lg p-3 mb-3 font-mono text-xs text-gray-800">
                        <strong>Formula:</strong> Dimension_Consistency = (vectors_with_correct_dim / total_vectors) × 100
                        <br />Expected dimensions: MiniLM=384, OpenAI-3-small=1536, OpenAI-3-large=3072
                      </div>
                      <p className="text-xs text-gray-600">
                        <strong>Threshold:</strong> 100% = Required (must match configured model dimension)
                      </p>
                    </div>

                    <div className="bg-orange-50 border-l-4 border-orange-500 rounded-lg p-5">
                      <h4 className="font-bold text-gray-900 mb-3">Vector Quality Score</h4>
                      <p className="text-sm text-gray-700 mb-3">
                        <strong>Description:</strong> Composite quality metric evaluating vector validity, normalization, and distribution health. Ensures vectors are suitable for semantic search.
                      </p>
                      <p className="text-sm text-gray-700 mb-3">
                        <strong>Calculation:</strong> Weighted combination of: valid vectors (no NaN/Inf) 40%, non-zero vectors 30%, optimal L2 norm distribution 30%.
                      </p>
                      <div className="bg-white rounded-lg p-3 mb-3 font-mono text-xs text-gray-800">
                        <strong>Formula:</strong> VQS = 0.4 × valid_ratio + 0.3 × non_zero_ratio + 0.3 × norm_health
                        <br />where norm_health ≈ 1 - outlier_rate(norms) (robustly measured via MAD / modified z-score)
                      </div>
                      <p className="text-xs text-gray-600">
                        <strong>Threshold:</strong> ≥ 95% = Excellent, ≥ 85% = Good, &lt; 85% = Needs Investigation
                      </p>
                    </div>

                    <div className="bg-orange-50 border-l-4 border-orange-500 rounded-lg p-5">
                      <h4 className="font-bold text-gray-900 mb-3">Embedding Success Rate</h4>
                      <p className="text-sm text-gray-700 mb-3">
                        <strong>Description:</strong> Percentage of chunks successfully embedded and stored in the vector database (Qdrant). Indicates embedding pipeline reliability.
                      </p>
                      <p className="text-sm text-gray-700 mb-3">
                        <strong>Calculation:</strong> Ratio of successfully indexed chunks to total chunks attempted for embedding.
                      </p>
                      <div className="bg-white rounded-lg p-3 mb-3 font-mono text-xs text-gray-800">
                        <strong>Formula:</strong> Success_Rate = (successfully_embedded_chunks / total_chunks) × 100
                        <br />Includes validation: dimension check, storage confirmation, metadata persistence
                      </div>
                      <p className="text-xs text-gray-600">
                        <strong>Threshold:</strong> 100% = Required (all chunks must be embedded successfully)
                      </p>
                    </div>

                    <div className="bg-orange-50 border-l-4 border-orange-500 rounded-lg p-5">
                      <h4 className="font-bold text-gray-900 mb-3">Embedding Model Health</h4>
                      <p className="text-sm text-gray-700 mb-3">
                        <strong>Description:</strong> Health score of the embedding model based on output consistency, variance, and error rates. Monitors model performance degradation.
                      </p>
                      <p className="text-sm text-gray-700 mb-3">
                        <strong>Calculation:</strong> Composite metric evaluating embedding variance, outlier detection, and API error rates (for API-based models).
                      </p>
                      <div className="bg-white rounded-lg p-3 mb-3 font-mono text-xs text-gray-800">
                        <strong>Formula (current implementation):</strong> Model_Health = 0.30×(1-api_error_rate) + 0.25×(1-fallback_rate) + 0.20×(1-dim_mismatch_rate) + 0.15×norm_health + 0.10×response_consistency
                        <br />Note: If the embedder is running in fallback (hash) mode, Model_Health is set to 0%.
                      </div>
                      <p className="text-xs text-gray-600">
                        <strong>Threshold:</strong> ≥ 95% = Healthy, ≥ 85% = Acceptable, &lt; 85% = Degraded (investigate model)
                      </p>
                    </div>

                    <div className="bg-orange-50 border-l-4 border-orange-500 rounded-lg p-5">
                      <h4 className="font-bold text-gray-900 mb-3">Semantic Search Readiness</h4>
                      <p className="text-sm text-gray-700 mb-3">
                        <strong>Description:</strong> Composite RAG readiness score combining all vector health indicators. Indicates overall readiness for production semantic search.
                      </p>
                      <p className="text-sm text-gray-700 mb-3">
                        <strong>Calculation:</strong> Weighted combination of dimension consistency (25%), vector quality (35%), model health (25%), and success rate (15%).
                      </p>
                      <div className="bg-white rounded-lg p-3 mb-3 font-mono text-xs text-gray-800">
                        <strong>Formula:</strong> RAG_Readiness = 0.25 × Dimension_Consistency + 0.35 × Vector_Quality + 0.25 × Model_Health + 0.15 × Success_Rate
                      </div>
                      <p className="text-xs text-gray-600">
                        <strong>Threshold:</strong> ≥ 90% = Ready for Production, ≥ 75% = Acceptable, &lt; 75% = Needs Improvement
                      </p>
                    </div>
                  </div>
                </div>

                {/* RAG Performance Metrics */}
                <div className="bg-white border-2 border-red-200 rounded-xl p-6">
                  <h3 className="text-xl font-bold text-gray-900 mb-6 flex items-center gap-3">
                    <Search className="h-6 w-6 text-[#C8102E]" />
                    RAG Performance Metrics
                  </h3>
                  <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6 text-sm text-gray-700">
                    <strong>Note:</strong> Unless you have a curated evaluation set (queries + relevance labels), PrimeData computes these as a <em>self-retrieval proxy</em>:
                    each query is derived from a chunk, and the chunk is treated as the single relevant document. This validates indexing/search correctness, but it is not a full “production RAG” benchmark.
                  </div>
                  <div className="space-y-6">
                    <div className="bg-red-50 border-l-4 border-red-500 rounded-lg p-5">
                      <h4 className="font-bold text-gray-900 mb-3">Retrieval Recall@K</h4>
                      <p className="text-sm text-gray-700 mb-3">
                        <strong>Description:</strong> Industry-standard retrieval metric measuring the percentage of relevant documents retrieved in the top K results. Higher recall indicates better coverage.
                      </p>
                      <p className="text-sm text-gray-700 mb-3">
                        <strong>Calculation:</strong> Ratio of relevant documents found in top K to total relevant documents in the corpus. Standard in information retrieval literature.
                      </p>
                      <div className="bg-white rounded-lg p-3 mb-3 font-mono text-xs text-gray-800">
                        <strong>Formula:</strong> Recall@K = |&#123;relevant_docs&#125; ∩ &#123;retrieved_top_k&#125;| / |&#123;relevant_docs&#125;|
                        <br />Typical K values: K=5, K=10, K=20
                      </div>
                      <p className="text-xs text-gray-600">
                        <strong>Threshold:</strong> ≥ 80% = Excellent, ≥ 65% = Good, &lt; 65% = Needs Tuning (K-dependent)
                      </p>
                    </div>

                    <div className="bg-red-50 border-l-4 border-red-500 rounded-lg p-5">
                      <h4 className="font-bold text-gray-900 mb-3">Average Precision@K</h4>
                      <p className="text-sm text-gray-700 mb-3">
                        <strong>Description:</strong> Mean Average Precision (MAP) measuring ranking quality. Higher precision indicates more relevant results at the top of the ranking.
                      </p>
                      <p className="text-sm text-gray-700 mb-3">
                        <strong>Calculation:</strong> Average precision across all queries, considering the position of relevant documents in the ranked list.
                      </p>
                      <div className="bg-white rounded-lg p-3 mb-3 font-mono text-xs text-gray-800">
                        <strong>Formula:</strong> AP@K = (1/|relevant|) × Σ (precision_at_i × relevance_i)
                        <br />MAP = mean(AP@K across all queries)
                      </div>
                      <p className="text-xs text-gray-600">
                        <strong>Threshold:</strong> ≥ 0.75 = Excellent, ≥ 0.60 = Good, &lt; 0.60 = Needs Improvement
                      </p>
                    </div>

                    <div className="bg-red-50 border-l-4 border-red-500 rounded-lg p-5">
                      <h4 className="font-bold text-gray-900 mb-3">Query Coverage</h4>
                      <p className="text-sm text-gray-700 mb-3">
                        <strong>Description:</strong> Percentage of queries with at least one relevant result retrieved. Measures system robustness across diverse queries.
                      </p>
                      <p className="text-sm text-gray-700 mb-3">
                        <strong>Calculation:</strong> Ratio of queries with recall &gt; 0 to total queries. Higher coverage indicates better query handling diversity.
                      </p>
                      <div className="bg-white rounded-lg p-3 mb-3 font-mono text-xs text-gray-800">
                        <strong>Formula:</strong> Query_Coverage = (queries_with_relevant_results / total_queries) × 100
                        <br />Coverage = 1 if ∃ relevant_doc in retrieved@K, else 0
                      </div>
                      <p className="text-xs text-gray-600">
                        <strong>Threshold:</strong> ≥ 90% = Excellent, ≥ 75% = Good, &lt; 75% = Needs Broadening
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </section>

          {/* Vectorization */}
          <section id="vectorization" className="bg-white rounded-xl shadow-lg border-2 border-gray-200 p-8">
            <button
              onClick={() => toggleSection('vectorization')}
              className="w-full flex items-center justify-between text-left"
            >
              <h2 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
                <div className="bg-[#C8102E]/10 rounded-xl p-3">
                  <Sparkles className="h-6 w-6 text-[#C8102E]" />
                </div>
                Vectorization
              </h2>
              {expandedSections.vectorization ? (
                <ChevronUp className="h-5 w-5 text-gray-400" />
              ) : (
                <ChevronDown className="h-5 w-5 text-gray-400" />
              )}
            </button>

            {expandedSections.vectorization && (
              <div className="mt-8 space-y-6">
                <div className="bg-white border-2 border-gray-200 rounded-xl p-6">
                  <h3 className="text-xl font-bold text-gray-900 mb-4">How Vectorization Works</h3>
                  <div className="space-y-4">
                    <div className="flex items-start gap-4">
                      <div className="flex-shrink-0 w-8 h-8 bg-[#C8102E] text-white rounded-full flex items-center justify-center text-sm font-bold">1</div>
                      <div>
                        <p className="font-semibold text-gray-900">Text Chunking</p>
                        <p className="text-sm text-gray-700">Documents are split into chunks using configurable strategies (fixed-size, semantic, recursive).</p>
                      </div>
                    </div>
                    <div className="flex items-start gap-4">
                      <div className="flex-shrink-0 w-8 h-8 bg-[#C8102E] text-white rounded-full flex items-center justify-center text-sm font-bold">2</div>
                      <div>
                        <p className="font-semibold text-gray-900">Embedding Generation</p>
                        <p className="text-sm text-gray-700">Each chunk is converted to a vector embedding using OpenAI API or local models (MiniLM, MPNet, etc.).</p>
                      </div>
                    </div>
                    <div className="flex items-start gap-4">
                      <div className="flex-shrink-0 w-8 h-8 bg-[#C8102E] text-white rounded-full flex items-center justify-center text-sm font-bold">3</div>
                      <div>
                        <p className="font-semibold text-gray-900">Vector Storage</p>
                        <p className="text-sm text-gray-700">Vectors are stored in Qdrant vector database with metadata (chunk ID, source, section, etc.).</p>
                      </div>
                    </div>
                    <div className="flex items-start gap-4">
                      <div className="flex-shrink-0 w-8 h-8 bg-[#C8102E] text-white rounded-full flex items-center justify-center text-sm font-bold">4</div>
                      <div>
                        <p className="font-semibold text-gray-900">Quality Validation</p>
                        <p className="text-sm text-gray-700">Vector metrics are calculated to ensure quality and consistency.</p>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="bg-white border-2 border-gray-200 rounded-xl p-6">
                  <h3 className="text-xl font-bold text-gray-900 mb-4">Embedding Models</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="bg-[#F5E6E8] border-l-4 border-[#C8102E] rounded-lg p-4">
                      <h4 className="font-bold text-gray-900 mb-2">OpenAI (Recommended)</h4>
                      <ul className="text-sm text-gray-700 space-y-1">
                        <li>• text-embedding-3-small: 1536 dimensions</li>
                        <li>• text-embedding-3-large: 3072 dimensions</li>
                        <li>• Requires API key, saves ~500MB-1GB memory</li>
                        <li>• Best for production use</li>
                      </ul>
                    </div>
                    <div className="bg-[#F5E6E8] border-l-4 border-[#C8102E] rounded-lg p-4">
                      <h4 className="font-bold text-gray-900 mb-2">Open Source (Local)</h4>
                      <ul className="text-sm text-gray-700 space-y-1">
                        <li>• MiniLM: 384 dimensions</li>
                        <li>• MPNet, BGE, GTE, E5: 768-1024 dimensions</li>
                        <li>• Works offline, requires more memory</li>
                        <li>• Good for development/testing</li>
                      </ul>
                    </div>
                  </div>
                </div>

                <div className="bg-amber-50 border-l-4 border-amber-400 rounded-lg p-4">
                  <div className="flex items-start gap-3">
                    <AlertTriangle className="h-5 w-5 text-amber-600 flex-shrink-0 mt-0.5" />
                    <div>
                      <p className="font-semibold text-amber-900 mb-1">Fallback Mode</p>
                      <p className="text-sm text-amber-800">
                        If embedding models fail to load or API keys are missing, PrimeData falls back to hash-based embeddings. This provides basic functionality but won't support semantic search. Ensure your embedding model is properly configured for production use.
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </section>

          {/* Troubleshooting */}
          <section id="troubleshooting" className="bg-white rounded-xl shadow-lg border-2 border-gray-200 p-8">
            <button
              onClick={() => toggleSection('troubleshooting')}
              className="w-full flex items-center justify-between text-left"
            >
              <h2 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
                <div className="bg-[#C8102E]/10 rounded-xl p-3">
                  <AlertTriangle className="h-6 w-6 text-[#C8102E]" />
                </div>
                Troubleshooting
              </h2>
              {expandedSections.troubleshooting ? (
                <ChevronUp className="h-5 w-5 text-gray-400" />
              ) : (
                <ChevronDown className="h-5 w-5 text-gray-400" />
              )}
            </button>

            {expandedSections.troubleshooting && (
              <div className="mt-8 space-y-6">
                <div className="bg-white border-2 border-gray-200 rounded-xl p-6">
                  <h3 className="text-lg font-bold text-gray-900 mb-4">Common Issues</h3>
                  <div className="space-y-4">
                    <div className="bg-[#F5E6E8] border-l-4 border-[#C8102E] rounded-lg p-4">
                      <p className="font-semibold text-gray-900 mb-2">Low AI Trust Score</p>
                      <ul className="text-sm text-gray-700 space-y-1 list-disc list-inside ml-2">
                        <li>Check individual metric scores to identify weak areas</li>
                        <li>Review recommendations in the AI Readiness section</li>
                        <li>Try different chunking strategies or playbooks</li>
                        <li>Ensure preprocessing playbook is appropriate for your content type</li>
                      </ul>
                    </div>

                    <div className="bg-[#F5E6E8] border-l-4 border-[#C8102E] rounded-lg p-4">
                      <p className="font-semibold text-gray-900 mb-2">Pipeline Failures</p>
                      <ul className="text-sm text-gray-700 space-y-1 list-disc list-inside ml-2">
                        <li>Check Airflow logs for detailed error messages</li>
                        <li>Verify all services (PostgreSQL, Qdrant, MinIO) are running</li>
                        <li>Ensure sufficient disk space and memory</li>
                        <li>Check API keys (OpenAI, cloud storage) are configured correctly</li>
                      </ul>
                    </div>

                    <div className="bg-[#F5E6E8] border-l-4 border-[#C8102E] rounded-lg p-4">
                      <p className="font-semibold text-gray-900 mb-2">Vector Metrics Show "Not Evaluated"</p>
                      <ul className="text-sm text-gray-700 space-y-1 list-disc list-inside ml-2">
                        <li>This means indexing has not run or Qdrant is inaccessible</li>
                        <li>Ensure the indexing stage completed successfully</li>
                        <li>Check Qdrant connection settings</li>
                        <li>Verify embedding model is properly configured</li>
                      </ul>
                    </div>

                    <div className="bg-[#F5E6E8] border-l-4 border-[#C8102E] rounded-lg p-4">
                      <p className="font-semibold text-gray-900 mb-2">Memory Issues (8GB Systems)</p>
                      <ul className="text-sm text-gray-700 space-y-1 list-disc list-inside ml-2">
                        <li>Use OpenAI API embeddings instead of local models (saves ~500MB-1GB)</li>
                        <li>Use test-only services for development (excludes Airflow)</li>
                        <li>Close other memory-intensive applications</li>
                        <li>Monitor memory usage with <code className="bg-gray-100 px-1 rounded">scripts/check_memory.sh</code> or <code className="bg-gray-100 px-1 rounded">scripts/check_memory.ps1</code></li>
                      </ul>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </section>

          {/* Best Practices */}
          <section id="bestPractices" className="bg-white rounded-xl shadow-lg border-2 border-gray-200 p-8">
            <button
              onClick={() => toggleSection('bestPractices')}
              className="w-full flex items-center justify-between text-left"
            >
              <h2 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
                <div className="bg-[#C8102E]/10 rounded-xl p-3">
                  <CheckCircle2 className="h-6 w-6 text-[#C8102E]" />
                </div>
                Best Practices
              </h2>
              {expandedSections.bestPractices ? (
                <ChevronUp className="h-5 w-5 text-gray-400" />
              ) : (
                <ChevronDown className="h-5 w-5 text-gray-400" />
              )}
            </button>

            {expandedSections.bestPractices && (
              <div className="mt-8 space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="bg-white border-2 border-gray-200 rounded-xl p-6">
                    <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
                      <Settings className="h-5 w-5 text-[#C8102E]" />
                      Chunking Best Practices
                    </h3>
                    <ul className="space-y-2 text-sm text-gray-700">
                      <li>• Use fixed-size chunking for general content (800-1000 tokens)</li>
                      <li>• Use semantic chunking for documents with clear structure</li>
                      <li>• Set chunk overlap to 10-20% for better context preservation</li>
                      <li>• Avoid chunks smaller than 100 tokens or larger than 2000 tokens</li>
                    </ul>
                  </div>

                  <div className="bg-white border-2 border-gray-200 rounded-xl p-6">
                    <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
                      <Database className="h-5 w-5 text-[#C8102E]" />
                      Embedding Best Practices
                    </h3>
                    <ul className="space-y-2 text-sm text-gray-700">
                      <li>• Use OpenAI embeddings for production (better quality, saves memory)</li>
                      <li>• Use local models (MiniLM) for development/testing</li>
                      <li>• Ensure embedding dimension matches your vector database configuration</li>
                      <li>• Monitor embedding success rate - should be close to 100%</li>
                    </ul>
                  </div>

                  <div className="bg-white border-2 border-gray-200 rounded-xl p-6">
                    <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
                      <FileText className="h-5 w-5 text-[#C8102E]" />
                      Content Quality Best Practices
                    </h3>
                    <ul className="space-y-2 text-sm text-gray-700">
                      <li>• Remove boilerplate and navigation elements before processing</li>
                      <li>• Ensure consistent formatting across documents</li>
                      <li>• Add metadata (titles, sections, authors) where possible</li>
                      <li>• Use appropriate playbooks for your content type (legal, financial, technical)</li>
                    </ul>
                  </div>

                  <div className="bg-white border-2 border-gray-200 rounded-xl p-6">
                    <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
                      <Target className="h-5 w-5 text-[#C8102E]" />
                      Quality Targets
                    </h3>
                    <ul className="space-y-2 text-sm text-gray-700">
                      <li>• AI Trust Score: Aim for 80%+ for production use</li>
                      <li>• Security Score: Must be 100% (no PII detected)</li>
                      <li>• Semantic Search Readiness: Aim for 85%+ for RAG applications</li>
                      <li>• Embedding Success Rate: Should be 100% (all chunks embedded)</li>
                    </ul>
                  </div>
                </div>
              </div>
            )}
          </section>
        </div>
        </div>

        {/* Footer */}
        <div className="mt-12 text-center">
          <p className="text-gray-600 mb-4">Need more help?</p>
          <Link href="/app/settings">
            <Button className="bg-[#C8102E] text-white hover:bg-[#A00D24]">
              Contact Support
            </Button>
          </Link>
        </div>
      </div>
    </div>
  )
}
