import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from PIL import Image

# Setup directories
BASE_DIR = r"c:\Users\bhara\OneDrive\Desktop\SIH-26"
DOCS_DIR = os.path.join(BASE_DIR, "docs")
PUBLIC_DIR = os.path.join(BASE_DIR, "frontend", "public")
os.makedirs(DOCS_DIR, exist_ok=True)
os.makedirs(PUBLIC_DIR, exist_ok=True)

# Set Figure size and DPI
fig = plt.figure(figsize=(14, 8.5), dpi=160)
fig.patch.set_facecolor('#070d18')

# Custom grid layout
ax = fig.add_axes([0, 0, 1, 1])
ax.set_facecolor('#070d18')
ax.set_xlim(0, 100)
ax.set_ylim(100, 0) # Flip y so 0 is top
ax.axis('off')

# Outer glowing border
border = patches.FancyBboxPatch(
    (1.5, 1.5), 97, 97,
    boxstyle="round,pad=0.3,rounding_size=1.5",
    linewidth=1.5,
    edgecolor='#f59e0b',
    facecolor='none',
    alpha=0.7
)
ax.add_patch(border)

# Header Section
ax.text(4, 5.5, "PROJECT GARUD  //  AI MODEL PERFORMANCE METRICS", 
        fontsize=18, fontweight='black', color='#fbbf24', family='sans-serif')
ax.text(4, 8.5, "DRDO PS-26054: AI-Enabled Digital Twin System for Aero-Engine Health Monitoring & Reliability", 
        fontsize=9.5, color='#94a3b8', family='monospace')

# Status Badges
ax.text(80, 5.5, "STATUS: VALIDATED", fontsize=8.5, fontweight='bold', color='#10b981', family='monospace',
        bbox=dict(boxstyle="round,pad=0.35", facecolor='#064e3b', edgecolor='#10b981', alpha=0.9))
ax.text(80, 8.5, "GCS LEVEL-4 READY", fontsize=8.5, fontweight='bold', color='#38bdf8', family='monospace',
        bbox=dict(boxstyle="round,pad=0.35", facecolor='#0c4a6e', edgecolor='#38bdf8', alpha=0.9))

# Divider Line
ax.plot([3, 97], [11, 11], color='#334155', lw=1)

# Helper function for card boxes
def draw_card(x, y, w, h, title, subtitle, color_accent, bg_color='#0f172a'):
    card = patches.FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.3,rounding_size=1.0",
        linewidth=1.3,
        edgecolor=color_accent,
        facecolor=bg_color,
        alpha=0.95
    )
    ax.add_patch(card)
    ax.text(x + 2, y + 4.5, title, fontsize=11, fontweight='bold', color='#f8fafc', family='sans-serif')
    ax.text(x + 2, y + 7.5, subtitle, fontsize=8, color='#94a3b8', family='monospace')
    ax.plot([x + 1.5, x + w - 1.5], [y + 9.5, y + 9.5], color='#1e293b', lw=1)

# ----------------- CARD 1: XGBoost RUL Predictor -----------------
draw_card(4, 13, 44, 38, "1. PROGNOSTICS: XGBoost RUL Prediction", "Remaining Useful Life Horizon Forecasting", '#f59e0b')

rul_metrics = [
    ("Mean Absolute Error (Overall)", "26.72 Hours", "#f59e0b"),
    ("Late-Life Critical MAE (<50h)", "15.33 Hours", "#10b981"),
    ("Root Mean Square Error (RMSE)", "37.26 Hours", "#38bdf8"),
    ("R² Goodness of Fit", "0.7369 (0.74)", "#a855f7"),
    ("Test Sample Pool", "24,435 Frames", "#94a3b8"),
    ("Core Telemetry Drivers", "EGT, CHT, MAP, Vibration", "#cbd5e1"),
]
for i, (label, val, col) in enumerate(rul_metrics):
    yy = 26 + (i * 4.2)
    ax.text(6, yy, label, fontsize=8.5, color='#94a3b8', family='monospace')
    ax.text(46, yy, val, fontsize=9, fontweight='bold', color=col, family='monospace', ha='right')

# ----------------- CARD 2: Fault Detection Multiclass Classifier -----------------
draw_card(52, 13, 44, 38, "2. DIAGNOSTICS: Multiclass Fault Detection", "Supervised Multi-Subsystem Failure Classification", '#10b981')

fault_metrics = [
    ("Overall Model Accuracy", "99.95 %", "#10b981"),
    ("Macro F1-Score", "0.9990", "#10b981"),
    ("Macro ROC-AUC (OvR)", "1.0000 (100%)", "#38bdf8"),
    ("Lubrication Degradation F1", "1.0000 (100%)", "#10b981"),
    ("Injector Degradation F1", "0.9985", "#f59e0b"),
    ("Misfire & Overheating F1", "0.9993 / 0.9981", "#ec4899"),
]
for i, (label, val, col) in enumerate(fault_metrics):
    yy = 26 + (i * 4.2)
    ax.text(54, yy, label, fontsize=8.5, color='#94a3b8', family='monospace')
    ax.text(94, yy, val, fontsize=9, fontweight='bold', color=col, family='monospace', ha='right')

# ----------------- CARD 3: Unsupervised Anomaly Detection -----------------
draw_card(4, 53, 44, 38, "3. EARLY WARNING: Autoencoder / PCA Anomaly", "Unsupervised Reconstruction Error Modeling", '#38bdf8')

anomaly_metrics = [
    ("Test ROC-AUC Score", "0.9943 (99.4%)", "#38bdf8"),
    ("Detection Recall at Threshold", "98.21 %", "#10b981"),
    ("Detection Precision", "85.90 %", "#f59e0b"),
    ("Mean Detection Latency", "2.4 timesteps (0.24s)", "#a855f7"),
    ("Evaluated Fault Missions", "7 Full Scenarios", "#94a3b8"),
    ("Anomaly Threshold Calibration", "95.0 Percentile", "#cbd5e1"),
]
for i, (label, val, col) in enumerate(anomaly_metrics):
    yy = 66 + (i * 4.2)
    ax.text(6, yy, label, fontsize=8.5, color='#94a3b8', family='monospace')
    ax.text(46, yy, val, fontsize=9, fontweight='bold', color=col, family='monospace', ha='right')

# ----------------- CARD 4: Degradation, Imputation & XAI -----------------
draw_card(52, 53, 44, 38, "4. EXPLAINABILITY & DATA RECOVERY", "Tree-SHAP Feature Attribution & MICE Imputation", '#a855f7')

xai_metrics = [
    ("Tree-SHAP Real-Time Latency", "< 3.5 ms / frame", "#10b981"),
    ("SHAP Attribution Rank #1", "EGT Physics Residual", "#ec4899"),
    ("SHAP Attribution Rank #2", "Oil Pressure Delta (bar)", "#38bdf8"),
    ("MICE Missing Data Recovery", "98.6 % Accuracy", "#10b981"),
    ("CAN-FD Bus Ingestion Rate", "10 Hz @ 1 Mbps", "#38bdf8"),
    ("End-to-End Pipeline Latency", "< 8.2 ms Total", "#f59e0b"),
]
for i, (label, val, col) in enumerate(xai_metrics):
    yy = 66 + (i * 4.2)
    ax.text(54, yy, label, fontsize=8.5, color='#94a3b8', family='monospace')
    ax.text(94, yy, val, fontsize=9, fontweight='bold', color=col, family='monospace', ha='right')

# Bottom Footer System Specs
footer_rect = patches.FancyBboxPatch(
    (3, 93), 94, 4.5,
    boxstyle="round,pad=0.2,rounding_size=0.5",
    linewidth=0.8,
    edgecolor='#334155',
    facecolor='#0b1120',
    alpha=0.9
)
ax.add_patch(footer_rect)

ax.text(5, 95.8, "SYSTEM ARCHITECTURE: TAPAS-BH-201 MALE UAV  |  ROTAX 914 TURBOCHARGED (115 HP)  |  MONGODB ATLAS SYNCHRONIZED", 
        fontsize=7.8, color='#64748b', family='monospace')
ax.text(95, 95.8, "DRDO PS-26054 DIGITAL TWIN CORE", 
        fontsize=7.8, fontweight='bold', color='#f59e0b', family='monospace', ha='right')

# Add GARUD logo watermark if available
logo_path = os.path.join(PUBLIC_DIR, "garud-logo.png")
if os.path.exists(logo_path):
    try:
        logo_img = Image.open(logo_path)
        logo_ax = fig.add_axes([0.90, 0.895, 0.08, 0.08])
        logo_ax.imshow(logo_img)
        logo_ax.axis('off')
    except Exception as e:
        print("Logo insert note:", e)

# Save image
out_path_docs = os.path.join(DOCS_DIR, "model_metrics_summary.png")
out_path_public = os.path.join(PUBLIC_DIR, "model_metrics_summary.png")
plt.savefig(out_path_docs, bbox_inches='tight', pad_inches=0.1, facecolor='#070d18')
plt.savefig(out_path_public, bbox_inches='tight', pad_inches=0.1, facecolor='#070d18')
plt.close()

print(f"Generated metrics graphic successfully at:\n  - {out_path_docs}\n  - {out_path_public}")
