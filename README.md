# Datalyst: Your AI Data Analyst Agent

Datalyst is a powerful, AI-driven API that automates the entire data analysis workflow. Simply provide a question and your data files, and Datalyst's AI agent will generate a step-by-step plan, execute Python code, and return the precise analysis, visualizations, and answers you need—all in a single API call.

**This project is live and accessible at:** `https://datalyst-production.up.railway.app/api`

## Core Features

*   **🧠 Dynamic Planning:** Datalyst uses a sophisticated AI planner to interpret your questions and create a custom, multi-step strategy for solving them.
*   **🐍 Code Generation & Execution:** The agent writes and runs Python code in a sandboxed environment, leveraging powerful libraries like Pandas, NetworkX, and Matplotlib to perform complex analysis.
*   **🌐 Web Scraping:** If your data is on a webpage, the agent can be instructed to fetch the URL, extract the relevant tables, and convert them to a usable format before analysis.
*   **📊 Data Analysis & Visualization:** From calculating correlations and network density to generating complex plots and histograms, the agent can perform a wide range of analytical tasks. All plots are returned as base64-encoded data URIs, ready for embedding.
*   **📁 Flexible File Handling:** The API is designed to handle multipart file uploads, accepting a primary `questions.txt` file and any number of accompanying data files (e.g., `.csv`).

## How It Works: The Planner-Executor Architecture

Datalyst operates on a robust two-stage model that mimics how a human data analyst works:

1.  **The Planner (The Brain):** When a request is received, the Planner AI analyzes the user's question and the available files. It formulates a high-level strategy and generates a structured JSON "plan" of action. This plan might involve fetching data, extracting tables, or writing a custom Python script.

2.  **The Executor (The Hands):** The Executor takes this JSON plan and executes each step in sequence. It provides a secure environment for running the AI-generated Python code, handles file I/O, and captures the final output.

```
User Request (Question + Files)  -->  [Planner AI]  -->  JSON Plan  -->  [Executor]  -->  Final JSON Response
```

This architecture makes the agent incredibly flexible and capable of solving novel, multi-step problems it has never seen before.

## How to Use the Live API

Interact with the agent by sending a `POST` request to the live endpoint with `multipart/form-data`.

**Endpoint:** `https://datalyst-production.up.railway.app/api`

You must always include a form part named `questions.txt` containing your instructions. You can include any other necessary data files by naming the form part after the filename itself.

---

### **Example 1: Network Analysis**

Let's ask the agent to analyze a network from a provided `edges.csv` file.

**`questions.txt`:**
```
Use the undirected network in `edges.csv`.

Return a JSON object with keys:
- `edge_count`: number
- `highest_degree_node`: string
- `average_degree`: number
- `density`: number
- `shortest_path_alice_eve`: number
- `network_graph`: base64 PNG string under 100kB
- `degree_histogram`: base64 PNG string under 100kB
```

**`edges.csv`:**
```csv
source,target
Alice,Bob
Alice,Carol
Bob,Carol
Bob,David
Bob,Eve
Carol,David
David,Eve
```

**cURL Command:**
```bash
curl -X POST "https://datalyst-production.up.railway.app/api" \
-F "questions.txt=@path/to/your/questions.txt" \
-F "edges.csv=@path/to/your/edges.csv"
```

---

### **Example 2: Sales Data Analysis**

Let's ask the agent to analyze sales data from `sample-sales.csv`.

**`questions.txt`:**
```
Analyze `sample-sales.csv`.

Return a JSON object with keys:
- `total_sales`: number
- `top_region`: string
- `bar_chart`: base64 PNG string under 100kB
```

**`sample-sales.csv`:**```csv
order_id,date,region,sales
1,2024-01-01,East,100
2,2024-01-02,West,200
3,2024-01-03,East,150
4,2024-01-04,North,50
5,2024-01-05,South,120
6,2024-01-06,West,220
7,2024-01-07,East,130
8,2024-01-08,South,170
```

**cURL Command:**
```bash
curl -X POST "https://datalyst-production.up.railway.app/api" \
-F "questions.txt=@path/to/your/questions.txt" \
-F "sample-sales.csv=@path/to/your/sample-sales.csv"
```

## Technology Stack

*   **Backend:** Python 3.11+ with FastAPI
*   **AI Planner:** OpenAI models via AI Pipe / OpenRouter
*   **Data Manipulation:** Pandas
*   **Plotting:** Matplotlib
*   **Network Analysis:** NetworkX
*   **Deployment:** Railway

## License

This project is licensed under the MIT License.
