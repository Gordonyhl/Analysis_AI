# AI-Powered Platform for Automated RNA-Seq Data Analysis

### Core Vision
To create a fully automated, intelligent, and interactive AI system that empowers bioinformaticians to perform comprehensive RNA sequencing data analysis with unprecedented speed, accuracy, and insight, leveraging cutting-edge **AI agents**, robust **R scripting**, and a user-friendly web interface.

### Target Audience
Bioinformaticians, especially those frequently analyzing RNA sequencing count data.

### Technology Stack
Pydantic AI for structured data and agent outputs, Langgraph for orchestrating complex multi-agent workflows, and FastAPI for linking the frontend and backend.

### Technical Architecture

#### R Integration Strategy
* **Containerized R Environment:** All R/Bioconductor packages (DESeq2, edgeR, limma-voom, clusterProfiler, etc.) will be containerized to ensure reproducibility across different environments.
* **Python-R Communication:** Integration options include:
  * **rpy2** for direct Python-R calls with tight coupling
  * **Subprocess calls** to standalone R scripts within Docker containers
  * **Plumber API** treating R as a microservice for looser coupling
* **Pre-validated R Scripts:** Maintain a library of tested, robust R scripts that the AI agents can invoke with dynamically generated parameters.

#### Database Architecture
* **PostgreSQL Database:** Primary storage for:
  * User sessions and conversation history
  * Experimental metadata and design parameters
  * Analysis pipeline configurations and results
  * AI agent reasoning logs and decision trees
* **Large File Handling:** Count tables and generated plots stored efficiently, potentially using object storage patterns for scalability.

#### Real-time Communication
* **WebSocket Integration:** FastAPI's built-in WebSocket support enables:
  * Real-time AI conversation interface
  * Live progress updates during long-running analyses
  * Interactive plot modification requests
  * Streaming of analysis results as they become available

#### Frontend Technology Stack
* **React + Plotly:** Modern, interactive frontend for data visualization and user interaction (backend-focused development initially)
* **Real-time Updates:** WebSocket-driven live updates for plots and analysis progress

---

## Desired Workflow & Key Differentiating Features

### Intuitive Data Upload & Initial Context Gathering
* Users upload their RNA sequencing count tables (and optional metadata files) via the FastAPI web platform.
* The platform initiates an initial set of intelligent, context-aware questions to understand the user's high-level goals (e.g., "Are you looking for differentially expressed genes?", "Are you investigating specific pathways?", "Do you have particular hypotheses in mind?") and initial experimental design (e.g., "What are your primary comparison groups?", "Are there batch effects to consider?").

---

### Intelligent Data Understanding & Pre-processing Agents

* **Automated Data Profiling:** An AI agent automatically inspects the uploaded data. This includes detecting data types, potential outliers, identifying sample and gene counts, and inferring the likely structure of the metadata.
* **Intelligent Metadata Interpretation:** Agents analyze metadata headers and values to infer experimental design (e.g., control vs. treatment groups, time points, replicates, covariates). It proactively identifies potential inconsistencies or ambiguities, prompting the user for clarification only when necessary.
* **Automated Quality Control (QC) & Interpretation:** AI agents execute standard RNA-seq QC pipelines (e.g., generating count distributions, PCA/MDS plots for sample similarity, outlier detection). Crucially, the AI doesn't just present plots; it interprets them, flagging potential issues like sample swaps, strong batch effects, or low-quality samples, and suggesting corrective actions or considerations for downstream analysis.

---

### Dynamic & Adaptive Analysis Planning with Controlled R Execution

* **Goal-Oriented Reasoning & Method Selection:** Based on user input, data characteristics, and QC results, an "Analysis Planning Agent" dynamically constructs a step-by-step analysis pipeline. This agent will reason about the most appropriate statistical methods (e.g., DESeq2, edgeR, limma-voom for differential expression; various GSEA tools for pathway analysis) and parameters for the specific dataset and user's scientific question.
* **Controlled R Script Application:** While the AI dynamically chooses the methods and sequence, it will then select and apply pre-defined, robust, and validated R scripts for executing each step. This ensures quality control, reproducibility, and prevents "hallucinated" R code while still allowing the AI to be highly flexible in its analytical strategy. For example, if it decides on DESeq2, it will call the pre-vetted `run_deseq2.R` script with dynamically generated parameters.

---

### Rich Interpretation, Hypothesis Generation, and External Knowledge Integration

* **Narrative Generation:** Beyond raw results and plots, an "Interpretation Agent" generates a comprehensive, human-readable narrative. This includes summarizing key findings, highlighting top differentially expressed genes, and significant pathways.
* **Deep Gene & Pathway Insights (Research Agent):** For key differentially expressed genes or enriched pathways, a specialized "Research Agent" will search relevant scholarly databases like PubMed, Google Scholar, or specific bioinformatics repositories (e.g., NCBI Gene, Ensembl, GO, KEGG). It will then integrate this external knowledge into the narrative, providing:
    * Known functions and biological roles of the genes.
    * Associations with diseases or biological processes.
* **Hypothesis Generation:** Based on the data findings and external research, the agent will propose plausible biological hypotheses for observed changes, citing its sources (e.g., "Gene X, found to be highly upregulated, is implicated in immune response pathways [PubMed ID: YYYYMMDD.N] and its increased expression here suggests...").

---

### Interactive Plot Customization

* **Natural Language Plot Modification:** Users can request modifications to generated plots using natural language (e.g., "Change the color of upregulated genes to blue," "Add a title 'Differential Expression in Cancer Cells'," "Adjust the x-axis limits to -3 and 3," "Show only the top 20 genes on the heatmap").
* **AI-Driven Plot Regeneration:** An "Plot Customization Agent" interprets these requests and modifies the underlying R plotting code (e.g., ggplot2 parameters) to regenerate the desired visualization in real-time.

---

### Robust Error Handling & Dynamic Debugging

* **Intelligent R Error Interpretation:** If an R script encounters an error, the AI system will intercept the error message, interpret it in a user-friendly manner, and provide context-specific guidance.
* **Proposed Solutions:** The AI can suggest common causes for the error in bioinformatics (e.g., "Missing metadata column," "Invalid sample names," "Convergence issues due to low counts") and propose specific solutions or parameter adjustments, potentially even attempting to fix minor issues automatically (e.g., data type conversions).

---

### Explainable AI (XAI) & Full Reproducibility

* **Transparent Reasoning Logs:** The platform will maintain and expose complete, detailed logs of the AI agents' reasoning process. This includes every decision made by the planning agent, every tool call, every parameter chosen, and the justification for these choices.
* **Process Summary:** For easier user comprehension, the platform will generate a high-level summary of the entire analytical workflow performed, detailing the methods chosen, the rationale behind them, and key findings.
* **Reproducible Outputs:** All generated R code, parameter settings, package versions, results, and plots will be available for download, ensuring full scientific reproducibility.
