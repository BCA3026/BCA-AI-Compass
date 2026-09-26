import pandas as pd, numpy as np, pickle, os
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score
from mlxtend.frequent_patterns import apriori, association_rules
from mlxtend.preprocessing import TransactionEncoder

data = {
    'python':   [5,5,4,3,2,1,1,2,3,4,5,5,4,3,2,1,1,2,3,4,5,4,3,2,1,3,4,5,2,1,4,5,3,2,1,3,4,2,1,5],
    'ml':       [5,5,4,2,1,1,1,1,2,5,5,5,4,2,1,1,1,1,2,4,5,4,2,1,1,2,5,5,1,1,4,5,2,1,1,3,5,1,1,5],
    'stats':    [4,5,5,2,1,1,1,1,3,5,4,5,5,2,1,1,1,1,3,4,4,5,3,1,1,2,4,5,1,1,4,5,2,1,1,3,4,1,1,5],
    'sql':      [3,4,5,3,2,3,2,3,5,3,3,4,5,3,2,3,2,3,5,3,3,4,5,3,2,3,3,4,3,3,3,4,3,3,3,3,3,3,3,3],
    'web':      [2,1,1,5,5,3,2,2,1,1,2,1,1,5,5,3,2,2,1,1,2,1,1,5,5,3,2,1,5,5,2,1,5,5,5,3,1,5,5,1],
    'mobile':   [1,1,1,3,5,2,1,2,1,1,1,1,1,3,5,2,1,2,1,1,1,1,1,3,5,2,1,1,5,5,1,1,3,5,5,2,1,5,5,1],
    'security': [1,1,1,1,2,5,5,3,1,1,1,1,1,1,2,5,5,3,1,1,1,1,1,1,2,5,1,1,2,2,1,1,1,2,2,5,1,2,2,1],
    'cloud':    [2,2,2,2,2,3,4,5,2,2,2,2,2,2,2,3,4,5,2,2,2,2,2,2,2,3,2,2,2,2,2,2,2,2,2,3,2,2,2,2],
    'career':['ML Engineer','Data Scientist','Data Analyst','Web Developer','Android Developer','Cybersecurity Analyst','Cloud Engineer','MLOps Engineer','Database Administrator','LLM Engineer','ML Engineer','Data Scientist','Data Analyst','Web Developer','iOS Developer','Cybersecurity Analyst','Cloud Engineer','MLOps Engineer','Database Administrator','AI Developer','ML Engineer','Data Scientist','Data Analyst','Full Stack Developer','Android Developer','Cybersecurity Analyst','Prompt Engineer','LLM Engineer','iOS Developer','Full Stack Developer','ML Engineer','Data Scientist','Web Developer','Android Developer','iOS Developer','Cybersecurity Analyst','AI Developer','Full Stack Developer','Android Developer','Data Scientist']
}

df = pd.DataFrame(data)
X = df[['python','ml','stats','sql','web','mobile','security','cloud']]
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)
kmeans = KMeans(n_clusters=8, random_state=42, n_init=10)
kmeans.fit(X_scaled)
score = silhouette_score(X_scaled, kmeans.labels_)
print(f"Silhouette Score: {score:.3f}")
cluster_map = {c: df[kmeans.labels_==c]['career'].mode()[0] for c in range(8) if len(df[kmeans.labels_==c])>0}
print("Cluster Map:", cluster_map)

transactions = [['python','ml','stats'],['python','ml','cloud'],['sql','stats','python'],['web','mobile'],['web','sql'],['python','ml','stats','cloud'],['sql','web'],['python','stats'],['ml','stats','cloud'],['web','sql','python'],['security','cloud'],['security','sql'],['mobile','web'],['python','ml'],['stats','sql']]
te = TransactionEncoder()
te_array = te.fit_transform(transactions)
df_t = pd.DataFrame(te_array, columns=te.columns_)
fi = apriori(df_t, min_support=0.15, use_colnames=True)
rules = association_rules(fi, metric="confidence", min_threshold=0.5)

os.makedirs('models', exist_ok=True)
with open('models/kmeans_model.pkl','wb') as f: pickle.dump(kmeans,f)
with open('models/scaler.pkl','wb') as f: pickle.dump(scaler,f)
with open('models/cluster_map.pkl','wb') as f: pickle.dump(cluster_map,f)
with open('models/apriori_rules.pkl','wb') as f: pickle.dump(rules,f)
print("✅ All models saved!")
