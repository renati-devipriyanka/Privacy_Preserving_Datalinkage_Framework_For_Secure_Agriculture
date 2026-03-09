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


# ============================================================
# NEW FUNCTION: Sensitive Attribute Detection
# Flask can call this separately
# ============================================================

def detect_sensitive_attributes(dataset_path):

    df = pd.read_csv(dataset_path)
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

    heuristic_sensitive=set()
    row_count=len(df)

    for col in df.columns:
        if df[col].nunique()/row_count > 0.95:
            heuristic_sensitive.add(col)

    sensitive_columns=list(rule_based_sensitive | heuristic_sensitive)

    return sensitive_columns


# ============================================================
# MAIN FRAMEWORK FUNCTION
# ============================================================

def run_privacy_framework(dataset_path, ui_sensitive_cols=None):

    print("🌾 Privacy-Preserving Agriculture Data Framework")

    if not os.path.exists(dataset_path):
        print("❌ Dataset file does not exist")
        return "Dataset file not found"

    df = pd.read_csv(dataset_path)
    raw_df = df.copy()

    print("✅ Dataset loaded successfully")
    print("Dataset shape:", df.shape)

    # ============================================================
    # Sensitive Attribute Detection
    # ============================================================

    print("\n🔐 Sensitive Attribute Detection")

    auto_detected = set(detect_sensitive_attributes(dataset_path))

    print("✔ Automatically detected attributes:")
    print(auto_detected)

    user_selected_sensitive=set()

    if ui_sensitive_cols:
        user_selected_sensitive=set(ui_sensitive_cols)

        print("✔ User selected attributes:")
        print(user_selected_sensitive)

    SENSITIVE_COLUMNS = auto_detected | user_selected_sensitive

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
    # Final Dataset
    # ============================================================

    final_df=raw_df.copy()
    final_df['Cluster']=gmm_labels

    OUTPUT_DIR="outputs"
    os.makedirs(OUTPUT_DIR,exist_ok=True)

    dataset_name=os.path.splitext(os.path.basename(dataset_path))[0]

    output_path=os.path.join(
        OUTPUT_DIR,
        f"{dataset_name}_privacy_preserved.csv"
    )

    final_df.to_csv(output_path,index=False)

    print("\n🎉 OUTPUT SAVED:",output_path)

    return output_path
if __name__ == "__main__":

    if len(sys.argv) >= 2:

        dataset_path = sys.argv[1]

        sensitive_cols = None

        if len(sys.argv) >= 3:
            sensitive_cols = sys.argv[2].split(",")

        run_privacy_framework(dataset_path, sensitive_cols)

    else:
        print("Please provide dataset path")