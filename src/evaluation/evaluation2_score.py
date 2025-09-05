import pandas as pd
from bert_score import score

df = pd.read_excel("https://raw.githubusercontent.com/Andrzej-Tezyk/KNF_Tool/main/src/Q_A_total_completed.xlsx")
bert_scores = []

real_answers = df["A_real"].astype(str).tolist()
tool_answers = df["A_tool"].astype(str).tolist()
P, R, F1 = score(tool_answers, real_answers, lang="pl") #BERT
for real, generated, bert_f1 in zip(real_answers, tool_answers, F1):
    bert_scores.append(bert_f1.item())

df["bertscore_f1"] = bert_scores

df["label_bert"] = (df["bertscore_f1"] >= 0.7).astype(int)

df.to_excel("Q_A_total_scored.xlsx", index=False)