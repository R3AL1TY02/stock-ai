from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

def train_model(df):
    df["target"] = (df["Close"].shift(-5) > df["Close"]).astype(int)

    features = ["rsi", "macd", "sma_50", "sma_200"]
    X = df[features]
    y = df["target"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, shuffle=False
    )

    model = RandomForestClassifier(n_estimators=200, random_state=42)
    model.fit(X_train, y_train)

    return model
