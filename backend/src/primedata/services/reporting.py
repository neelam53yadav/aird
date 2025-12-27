"""
Reporting service for PrimeData.

Generates validation summaries (CSV) and trust reports (PDF) from metrics.
"""

import io
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

try:
    import pandas as pd

    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False
    logger.warning("pandas not available, CSV generation will be limited")

try:
    import matplotlib

    matplotlib.use("Agg")  # Non-GUI backend
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages

    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    logger.warning("matplotlib not available, PDF generation will be disabled")


def generate_validation_summary(
    metrics: List[Dict[str, Any]],
    threshold: float = 70.0,
) -> str:
    """
    Generate validation summary CSV from metrics.

    Args:
        metrics: List of metric dictionaries (one per chunk)
        threshold: AI Trust Score threshold for categorization

    Returns:
        CSV content as string
    """
    if not HAS_PANDAS:
        raise RuntimeError("pandas is required for validation summary generation")

    if not metrics:
        logger.warning("No metrics provided for validation summary")
        return ""

    df = pd.DataFrame(metrics)

    # Categorize: AI Ready if score >= threshold
    df["Category"] = df["AI_Trust_Score"].apply(lambda x: "AI Ready" if x >= threshold else "Non-AI Ready")

    # Compute summary stats
    summary = (
        df.groupby("Category")
        .agg(
            {
                "AI_Trust_Score": "mean",
                "GPT_Confidence": "mean",
                "Completeness": "mean",
                "Accuracy": "mean",
                "Quality": "mean",
                "Secure": "mean",
                "Timeliness": "mean",
                "Metadata_Presence": "mean",
                "Audience_Intentionality": "mean",
                "Diversity": "mean",
                "Context_Quality": "mean",
                "Audience_Accessibility": "mean",
                "KnowledgeBase_Ready": "mean",
            }
        )
        .rename(
            columns={
                "AI_Trust_Score": "Avg Trust Score",
                "GPT_Confidence": "Avg GPT Confidence",
                "Completeness": "Avg Completeness",
                "Accuracy": "Avg Accuracy",
                "Quality": "Avg Quality",
                "Secure": "Avg Secure",
                "Timeliness": "Avg Timeliness",
                "Metadata_Presence": "Avg Metadata %",
                "Audience_Intentionality": "Avg Audience Intent",
                "Diversity": "Avg Diversity",
                "Context_Quality": "Avg Context Quality",
                "Audience_Accessibility": "Avg Audience Access",
                "KnowledgeBase_Ready": "Avg KB Readiness",
            }
        )
    )

    # Convert to CSV string
    csv_buffer = io.StringIO()
    summary.to_csv(csv_buffer, index=True)
    csv_content = csv_buffer.getvalue()
    csv_buffer.close()

    logger.info(f"Generated validation summary with {len(summary)} categories")
    return csv_content


def generate_trust_report(
    metrics: List[Dict[str, Any]],
    threshold: float = 75.0,
) -> bytes:
    """
    Generate PDF trust report from metrics.

    Args:
        metrics: List of metric dictionaries (one per chunk)
        threshold: AI Trust Score threshold for categorization (0-100 scale)

    Returns:
        PDF content as bytes
    """
    if not HAS_MATPLOTLIB:
        raise RuntimeError("matplotlib is required for PDF report generation")

    if not metrics:
        logger.warning("No metrics provided for trust report")
        return b""

    # Choose the labels to plot
    labels = ["Completeness", "Accuracy", "Secure", "Quality", "Timeliness"]

    ai_vals, non_vals = [], []

    # Compute average per-metric for AI-ready vs non-ready
    for m in labels:
        ai_list = [x[m] for x in metrics if x.get("AI_Trust_Score", 0) >= threshold]
        non_list = [x[m] for x in metrics if x.get("AI_Trust_Score", 0) < threshold]

        ai_vals.append(sum(ai_list) / len(ai_list) if ai_list else 0)
        non_vals.append(sum(non_list) / len(non_list) if non_list else 0)

    # Prepare bar chart
    x = range(len(labels))
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar([i - 0.2 for i in x], ai_vals, width=0.4, label="AI Ready")
    ax.bar([i + 0.2 for i in x], non_vals, width=0.4, label="Non-AI Ready")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Avg Score")
    ax.set_title("AI Trust Metric Comparison")
    ax.legend()

    # Save to PDF bytes
    pdf_buffer = io.BytesIO()
    with PdfPages(pdf_buffer) as out:
        out.savefig(fig, bbox_inches="tight")
        plt.close(fig)

        # Second page with recommendations
        fig2, ax2 = plt.subplots(figsize=(8, 4))
        ax2.axis("off")
        report = "\n".join(
            [
                "🟢 AI-Ready Data: Score ≥ 75% — Recommended for AI/chatbot ingestion.",
                "🟡 Medium Trust: Score 50–74% — Needs cleanup or review.",
                "🔴 Non-AI-Ready: Score < 50% — Not suitable without transformation.",
            ]
        )
        ax2.text(0, 1, report, va="top", fontsize=12, transform=ax2.transAxes)
        out.savefig(fig2, bbox_inches="tight")
        plt.close(fig2)

    pdf_bytes = pdf_buffer.getvalue()
    pdf_buffer.close()

    logger.info(f"Generated trust report PDF ({len(pdf_bytes)} bytes)")
    return pdf_bytes
