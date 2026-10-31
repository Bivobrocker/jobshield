from pathlib import Path
import json

import joblib
import pandas as pd
import numpy as np

from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score, balanced_accuracy_score,
    classification_report, confusion_matrix,
    roc_auc_score, average_precision_score,
    precision_score, recall_score, fbeta_score
)

ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / "data" / "fake_job_postings.csv"
MODEL_DIR = ROOT / "models"

RANDOM_STATE = 42

TEXT_COLUMNS = [
    "title", "company_profile", "description",
    "requirements", "benefits"
]

CATEGORICAL_COLUMNS = [
    "location", "department", "employment_type",
    "required_experience", "required_education",
    "industry", "function"
]

NUMERIC_COLUMNS = [
    "telecommuting", "has_company_logo", "has_questions"
]

FEATURE_COLUMNS = TEXT_COLUMNS + CATEGORICAL_COLUMNS + NUMERIC_COLUMNS


def prepare_features(df):
    X = df[FEATURE_COLUMNS].copy()

    for col in TEXT_COLUMNS + CATEGORICAL_COLUMNS:
        X[col] = X[col].fillna("").astype(str)

    for col in NUMERIC_COLUMNS:
        X[col] = pd.to_numeric(X[col], errors="coerce")

    return X


def build_model():

    transformers = []

    for col in TEXT_COLUMNS:
        transformers.append((
            f"tfidf_{col}",
            TfidfVectorizer(
                lowercase=True,
                stop_words=None,
                ngram_range=(1, 2),
                max_features=20000,
                min_df=2,
                sublinear_tf=True
            ),
            col
        ))

    transformers.extend([
        (
            "categorical",
            Pipeline([
                ("imputer", SimpleImputer(
                    strategy="constant", fill_value="missing"
                )),
                ("encoder", OneHotEncoder(handle_unknown="ignore"))
            ]),
            CATEGORICAL_COLUMNS
        ),
        (
            "numeric",
            Pipeline([
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler(with_mean=False))
            ]),
            NUMERIC_COLUMNS
        )
    ])

    features = ColumnTransformer(transformers)

    return Pipeline([
        ("features", features),
        ("classifier", LogisticRegression(
            max_iter=1500,
            class_weight="balanced",
            random_state=RANDOM_STATE
        ))
    ])


def select_threshold(y_true, probabilities):
    best_threshold = 0.5
    best_f2 = -1
    best_precision = -1

    for threshold in np.arange(0.05, 0.96, 0.01):
        predictions = (probabilities >= threshold).astype(int)

        precision = precision_score(
            y_true, predictions, zero_division=0
        )
        f2 = fbeta_score(
            y_true, predictions, beta=2, zero_division=0
        )

        if f2 > best_f2 or (
            f2 == best_f2 and precision > best_precision
        ):
            best_f2 = f2
            best_precision = precision
            best_threshold = float(round(threshold, 2))

    return best_threshold


def evaluate(y_true, probabilities, threshold):
    predictions = (probabilities >= threshold).astype(int)

    return {
        "threshold": threshold,
        "accuracy": float(accuracy_score(y_true, predictions)),
        "balanced_accuracy": float(
            balanced_accuracy_score(y_true, predictions)
        ),
        "fraud_precision": float(
            precision_score(y_true, predictions, zero_division=0)
        ),
        "fraud_recall": float(
            recall_score(y_true, predictions, zero_division=0)
        ),
        "fraud_f2": float(
            fbeta_score(y_true, predictions, beta=2, zero_division=0)
        ),
        "roc_auc": float(roc_auc_score(y_true, probabilities)),
        "average_precision": float(
            average_precision_score(y_true, probabilities)
        ),
        "confusion_matrix": confusion_matrix(
            y_true, predictions, labels=[0, 1]
        ).tolist(),
        "classification_report": classification_report(
            y_true,
            predictions,
            labels=[0, 1],
            target_names=["LEGITIMATE", "FRAUDULENT"],
            output_dict=True,
            zero_division=0
        )
    }


def main():

    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Dataset missing: {DATA_PATH}")

    df = pd.read_csv(DATA_PATH)

    required = set(FEATURE_COLUMNS + ["fraudulent"])

    if not required.issubset(df.columns):
        raise ValueError(
            f"Missing columns: {required - set(df.columns)}"
        )

    df = df.copy()
    df["fraudulent"] = pd.to_numeric(
        df["fraudulent"], errors="coerce"
    )
    df = df.dropna(subset=["fraudulent"])
    df = df[df["fraudulent"].isin([0, 1])]

    X = prepare_features(df)
    y = df["fraudulent"].astype(int)

    print("Dataset rows:", len(df))
    print("\nClass distribution:")
    print(y.value_counts().to_string())

    X_train, X_temp, y_train, y_temp = train_test_split(
        X, y,
        test_size=0.40,
        random_state=RANDOM_STATE,
        stratify=y
    )

    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp,
        test_size=0.50,
        random_state=RANDOM_STATE,
        stratify=y_temp
    )

    print("\nTraining:", len(X_train))
    print("Validation:", len(X_val))
    print("Testing:", len(X_test))

    model = build_model()

    print("\nTraining multi-feature model...")
    model.fit(X_train, y_train)

    val_probabilities = model.predict_proba(X_val)[:, 1]

    threshold = select_threshold(y_val, val_probabilities)

    validation_metrics = evaluate(
        y_val, val_probabilities, threshold
    )

    test_probabilities = model.predict_proba(X_test)[:, 1]

    test_metrics = evaluate(
        y_test, test_probabilities, threshold
    )

    MODEL_DIR.mkdir(exist_ok=True)

    joblib.dump(model, MODEL_DIR / "jobshield_model.joblib")

    with open(MODEL_DIR / "model_threshold.json", "w") as f:
        json.dump({
            "threshold": threshold,
            "selection_method": "validation_maximum_f2",
            "beta": 2
        }, f, indent=4)

    metrics = {
        "dataset": "EMSCAD-based Kaggle dataset",
        "dataset_period": "2012-2014",
        "features": FEATURE_COLUMNS,
        "random_state": RANDOM_STATE,
        "split": {
            "training_rows": len(X_train),
            "validation_rows": len(X_val),
            "test_rows": len(X_test)
        },
        "threshold_selection": {
            "method": "maximum_validation_f2",
            "selected_threshold": threshold,
            "validation_metrics": validation_metrics
        },
        "final_test_metrics": test_metrics,
        "limitations": [
            "Historical dataset from 2012-2014.",
            "Random holdout does not establish modern scam performance.",
            "Scores are not calibrated probabilities.",
            "Synthetic API tests are not independent validation."
        ]
    }

    with open(MODEL_DIR / "model_metrics.json", "w") as f:
        json.dump(metrics, f, indent=4)

    print("\n========== TRAINING COMPLETE ==========")
    print("\nSELECTED THRESHOLD:", threshold)
    print("\nFINAL TEST RESULTS")
    print(json.dumps(test_metrics, indent=2))


if __name__ == "__main__":
    main()