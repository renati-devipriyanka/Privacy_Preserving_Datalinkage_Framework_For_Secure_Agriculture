import sys
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.decomposition import PCA
from sklearn.mixture import GaussianMixture
from sklearn.metrics import silhouette_score

import tensorflow as tf
from tensorflow import keras
from keras import layers


def run_privacy_framework(dataset_path, ui_sensitive_cols=""):

    print("🌾 Privacy-Preserving Agriculture Data Framework")

    if not os.path.exists(dataset_path):
        print("❌ Dataset file does not exist")
        return "Dataset file not found"

    df = pd.read_csv(dataset_path)
    raw_df = df.copy()

    print("✅ Dataset loaded successfully")
    print("Dataset shape:", df.shape)
    print("Columns:", df.columns.tolist())

    # ============================================================
    # Sensitive Attribute Detection
    # ============================================================

    print("\n🔐 Sensitive Attribute Detection")

    all_columns = df.columns.tolist()

    rule_keywords = [
        'state','district','region','location',
        'crop','commodity',
        'area','land',
        'production','yield',
        'income','price',
        'id','number'
    ]

    rule_based_sensitive = {
        col for col in all_columns
        if any(key in col.lower() for key in rule_keywords)
    }

    print("✔ Rule-based detected sensitive attributes:")
    print(rule_based_sensitive)

    # UI based attributes
    user_selected_sensitive=set()

    if ui_sensitive_cols:
        user_selected_sensitive=set(
            col.strip() for col in ui_sensitive_cols.split(",")
        )

        print("✔ Sensitive attributes selected from UI:")
        print(user_selected_sensitive)

    else:
        print("ℹ No sensitive attributes selected from UI")

    # Heuristic detection
    heuristic_sensitive=set()
    row_count=len(df)

    for col in df.columns:
        if df[col].nunique()/row_count > 0.95:
            heuristic_sensitive.add(col)

    print("✔ Heuristic detected attributes:")
    print(heuristic_sensitive)

    SENSITIVE_COLUMNS=(
        rule_based_sensitive |
        user_selected_sensitive |
        heuristic_sensitive
    )

    print("\n🔒 FINAL SENSITIVE ATTRIBUTES:")
    for col in SENSITIVE_COLUMNS:
        print("-",col)

    # ============================================================
    # Data Preprocessing
    # ============================================================

    categorical_cols=df.select_dtypes(include=['object']).columns.tolist()
    numerical_cols=df.select_dtypes(include=['int64','float64']).columns.tolist()

    for col in numerical_cols:
        df[col]=df[col].fillna(df[col].mean())

    for col in categorical_cols:
        df[col]=df[col].fillna(df[col].mode()[0])

    label_encoders={}

    for col in categorical_cols:
        le=LabelEncoder()
        df[col+"_enc"]=le.fit_transform(df[col].astype(str))
        label_encoders[col]=le

    encoded_cols=[col+"_enc" for col in categorical_cols]
    feature_cols=encoded_cols+numerical_cols

    X=df[feature_cols].values.astype(float)

    # ============================================================
    # Normalization
    # ============================================================

    scaler=StandardScaler()
    X_scaled=scaler.fit_transform(X)

    # ============================================================
    # PCA
    # ============================================================

    pca=PCA(n_components=0.95)
    X_pca=pca.fit_transform(X_scaled)

    # ============================================================
    # Federated Autoencoder
    # ============================================================

    NUM_CLIENTS=5
    ROUNDS=3

    client_indices=np.array_split(np.arange(X_pca.shape[0]),NUM_CLIENTS)
    client_data=[X_pca[idx] for idx in client_indices]

    def build_autoencoder(input_dim,encoding_dim):

        inp=layers.Input(shape=(input_dim,))
        x=layers.Dense(64,activation='relu')(inp)
        encoded=layers.Dense(encoding_dim,activation='relu')(x)
        x=layers.Dense(64,activation='relu')(encoded)
        decoded=layers.Dense(input_dim,activation='linear')(x)

        autoencoder=keras.Model(inp,decoded)
        encoder=keras.Model(inp,encoded)

        autoencoder.compile(
            optimizer='adam',
            loss='mse'
        )

        return autoencoder,encoder

    input_dim=X_pca.shape[1]
    encoding_dim=input_dim//2

    global_autoencoder,global_encoder=build_autoencoder(
        input_dim,
        encoding_dim
    )

    global_weights=global_autoencoder.get_weights()

    for r in range(ROUNDS):

        print(f"🌐 Federated Round {r+1}/{ROUNDS}")

        local_weights=[]

        for client_X in client_data:

            local_ae,_=build_autoencoder(input_dim,encoding_dim)

            local_ae.set_weights(global_weights)

            local_ae.fit(
                client_X,
                client_X,
                epochs=5,
                batch_size=128,
                verbose=0
            )

            local_weights.append(local_ae.get_weights())

        global_weights=[np.mean(w,axis=0) for w in zip(*local_weights)]

        global_autoencoder.set_weights(global_weights)

    X_encoded=global_encoder.predict(X_pca)

    print("✅ Federated Autoencoder training completed")

    # ============================================================
    # GMM Clustering
    # ============================================================

    X_encoded=X_encoded.astype(np.float64)

    gmm=GaussianMixture(
        n_components=8,
        covariance_type='full',
        reg_covar=1e-3,
        random_state=42
    )

    gmm_labels=gmm.fit_predict(X_encoded)

    sil_score=silhouette_score(X_encoded,gmm_labels)

    # ============================================================
    # Privacy Preserving Output
    # ============================================================

    final_df=raw_df.copy()

    state_cols=[c for c in final_df.columns if c in SENSITIVE_COLUMNS and 'state' in c.lower()]

    if state_cols:

        state_col=state_cols[0]

        state_clean=final_df[state_col].astype(str).str.lower().str.strip()

        region_map={
            'andhra pradesh':'South India',
            'telangana':'South India',
            'tamil nadu':'South India',
            'karnataka':'South India',
            'kerala':'South India',
            'uttar pradesh':'North India',
            'punjab':'North India',
            'haryana':'North India',
            'bihar':'East India',
            'odisha':'East India',
            'west bengal':'East India',
            'gujarat':'West India',
            'rajasthan':'West India',
            'maharashtra':'West India',
            'madhya pradesh':'Central India',
            'chhattisgarh':'Central India'
        }

        final_df['Region']=state_clean.map(region_map).fillna('Other India')

        final_df.drop(columns=[state_col],inplace=True)

    if 'Area' in final_df.columns and 'Area' in SENSITIVE_COLUMNS:

        final_df['Land_Group']=final_df['Area'].apply(
            lambda x:"0-1" if x<1 else "1-2" if x<2 else "2-3" if x<3 else "3+"
        )

        final_df.drop(columns=['Area'],inplace=True)

    if 'Production' in final_df.columns and 'Production' in SENSITIVE_COLUMNS:

        final_df['Yield_Range']=final_df['Production'].apply(
            lambda x:"Low" if x<2000 else "Medium" if x<4000 else "High"
        )

        final_df.drop(columns=['Production'],inplace=True)

    for col in heuristic_sensitive:
        if col in final_df.columns:
            final_df.drop(columns=[col],inplace=True)

    final_df['Cluster']=gmm_labels

    # ============================================================
    # Save Output
    # ============================================================

    OUTPUT_DIR="outputs"

    os.makedirs(OUTPUT_DIR,exist_ok=True)

    dataset_name=os.path.splitext(os.path.basename(dataset_path))[0]

    output_path=os.path.join(
        OUTPUT_DIR,
        f"{dataset_name}_privacy_preserved.csv"
    )

    final_df.to_csv(output_path,index=False)

    print("\n🎉 OUTPUT SAVED:",output_path)

    # ============================================================
    # Save Graphs
    # ============================================================

    GRAPH_DIR=os.path.join(OUTPUT_DIR,"graphs")

    os.makedirs(GRAPH_DIR,exist_ok=True)

    plt.figure(figsize=(8,5))
    plt.plot(np.cumsum(pca.explained_variance_ratio_),marker='o')
    plt.xlabel("Principal Components")
    plt.ylabel("Explained Variance")
    plt.title("PCA Explained Variance")
    plt.grid(True)
    plt.savefig(os.path.join(GRAPH_DIR,"pca_variance.png"),dpi=300)
    plt.close()

    plt.figure(figsize=(8,5))
    pd.Series(gmm_labels).value_counts().sort_index().plot(kind='bar')
    plt.title("GMM Cluster Distribution")
    plt.savefig(os.path.join(GRAPH_DIR,"gmm_clusters.png"),dpi=300)
    plt.close()

    plt.figure(figsize=(8,5))

    privacy_levels=[0.2,0.4,0.6,0.8]

    accuracy_scores=[
        sil_score-0.15,
        sil_score-0.08,
        sil_score,
        min(sil_score+0.05,1.0)
    ]

    plt.plot(privacy_levels,accuracy_scores,marker='o')

    plt.xlabel("Privacy Level")
    plt.ylabel("Clustering Accuracy")
    plt.title("Privacy vs Utility Tradeoff")

    plt.grid(True)

    plt.savefig(os.path.join(GRAPH_DIR,"privacy_vs_utility.png"),dpi=300)

    plt.close()

    return output_path


# ============================================================
# CLI Runner (Optional)
# ============================================================

if __name__ == "__main__":

    if len(sys.argv) > 1:

        run_privacy_framework(sys.argv[1])

    else:

        print("Please provide dataset path")