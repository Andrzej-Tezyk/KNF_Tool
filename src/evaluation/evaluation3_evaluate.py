import google.generativeai as genai
import pandas as pd
import time
import nest_asyncio
nest_asyncio.apply()
from getpass import getpass
from phoenix.evals import HallucinationEvaluator, GoogleGenAIModel, QAEvaluator, run_evals

from main_app.config import Config

eval_model = GoogleGenAIModel(model="gemini-2.5-flash-lite") 
hallucination_evaluator = HallucinationEvaluator(eval_model)
qa_evaluator = QAEvaluator(eval_model)

df = pd.read_excel("https://raw.githubusercontent.com/Andrzej-Tezyk/KNF_Tool/main/src/Q_A_total_scored.xlsx")
# for `hallucination_evaluator` the input df needs to have columns 'output', 'input', 'context'
# for `qa_evaluator` the input df needs to have columns 'output', 'input', 'reference'
df["context"] = df["A_real"]
df.rename(columns={"Q": "input", "A_tool": "output", "A_real": "reference"}, inplace=True)
assert all(column in df.columns for column in ["output", "input", "context", "reference"])
# There are API limits in Gemini Free Tier
# Instead of doing it altogether, throttle to max allowed 15 requests per minute
#hallucination_eval_df, qa_eval_df = run_evals(
#    dataframe=df, evaluators=[hallucination_evaluator, qa_evaluator], provide_explanation=True
#)
# Each row triggers 2 API calls (one for hallucination_evaluator, one for qa_evaluator).
batch_size = 5   # 5 rows = 10 requests
pause_seconds = 60  # wait 1 minute between batches

all_hallucination_evals = []
all_qa_evals = []

for i in range(0, len(df), batch_size):
    batch = df.iloc[i:i+batch_size]

    hallucination_eval_df, qa_eval_df = run_evals(
        dataframe=batch,
        evaluators=[hallucination_evaluator, qa_evaluator],
        provide_explanation=True
    )

    all_hallucination_evals.append(hallucination_eval_df)
    all_qa_evals.append(qa_eval_df)

    # Only sleep if there's more data left
    if i + batch_size < len(df):
        print(f"Processed {i+batch_size} rows, sleeping {pause_seconds}s to respect quota...")
        time.sleep(pause_seconds)

# Combine results
hallucination_eval_df = pd.concat(all_hallucination_evals, ignore_index=True)
qa_eval_df = pd.concat(all_qa_evals, ignore_index=True)

results_df = df.copy()
results_df["hallucination_eval"] = hallucination_eval_df["label"]
results_df["hallucination_explanation"] = hallucination_eval_df["explanation"]
results_df["qa_eval"] = qa_eval_df["label"]
results_df["qa_explanation"] = qa_eval_df["explanation"]

df.to_excel("Q_A_total_evaluated.xlsx", index=False)

# Ensure categorical columns are consistent
results_df["Q_source"] = results_df["Q_source"].str.lower().str.strip()

# --- 1) Average bertscore_f1 ---
summary = {}
summary["avg_bertscore_overall"] = results_df["bertscore_f1"].mean()
summary_by_source = results_df.groupby("Q_source")["bertscore_f1"].mean().to_dict()

# --- 2) % label_bert = 1 ---
summary["pct_label1_overall"] = (results_df["label_bert"].mean()) * 100
pct_label_by_source = results_df.groupby("Q_source")["label_bert"].mean().mul(100).to_dict()

# --- 3) % factual ---
summary["pct_factual_overall"] = (results_df["hallucination_eval"].eq("factual").mean()) * 100
pct_factual_by_source = results_df.groupby("Q_source")["hallucination_eval"].apply(lambda x: (x.eq("factual").mean()*100)).to_dict()

# --- 4) % correct ---
summary["pct_correct_overall"] = (results_df["qa_eval"].eq("correct").mean()) * 100
pct_correct_by_source = results_df.groupby("Q_source")["qa_eval"].apply(lambda x: (x.eq("correct").mean()*100)).to_dict()

# --- 5) % rows with label=1 & factual & correct ---
summary["pct_all_three_overall"] = (
    ((results_df["label_bert"] == 1) &
     (results_df["hallucination_eval"] == "factual") &
     (results_df["qa_eval"] == "correct")).mean() * 100
)

# Put everything into a nice DataFrame for export
summary_rows = []

# Overall row
summary_rows.append({
    "Q_source": "overall",
    "avg_bertscore": summary["avg_bertscore_overall"],
    "pct_label1": summary["pct_label1_overall"],
    "pct_factual": summary["pct_factual_overall"],
    "pct_correct": summary["pct_correct_overall"],
    "pct_all_three": summary["pct_all_three_overall"]
})

# By source rows
for source in results_df["Q_source"].unique():
    summary_rows.append({
        "Q_source": source,
        "avg_bertscore": summary_by_source.get(source, float("nan")),
        "pct_label1": pct_label_by_source.get(source, float("nan")),
        "pct_factual": pct_factual_by_source.get(source, float("nan")),
        "pct_correct": pct_correct_by_source.get(source, float("nan")),
        "pct_all_three": None  # only overall required
    })

summary_df = pd.DataFrame(summary_rows)

# Save back into Excel, new sheet "Summary"
with pd.ExcelWriter("Q_A_total_evaluated.xlsx", engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
    summary_df.to_excel(writer, sheet_name="Summary", index=False)