# Used Car Value Forecasting: High-Dimensional Depreciation Modeling

**Domain:** Quantitative Valuation, Asset Pricing, Statistical Modeling  
**Repository:** [https://github.com/prak05/Used-Car-Value-Forecasting](https://github.com/prak05/Used-Car-Value-Forecasting)  

---

## 📌 Executive Overview
Secondary vehicle markets are characterized by high price volatility, regional valuation variance, and non-linear asset depreciation curves influenced by mileage, brand prestige, vehicle history, and macroeconomic factors.

**Used Car Value Forecasting** is an end-to-end regression modeling suite that captures non-linear vehicle depreciation patterns across multi-categorical automotive datasets with high predictive accuracy.

---

## ⚡ Technical Architecture & Tooling
- **Modeling Suite:** LightGBM, CatBoost, Scikit-Learn HistGradientBoostingRegressor, Ridge / Lasso baselines.
- **Feature Engineering:** Target encoding for high-cardinality vehicle makes/models, polynomial mileage decay curves, interaction terms.
- **Stack:** Jupyter Notebooks, Python 3.10+, Pandas, Scikit-Learn, Matplotlib.

---

## 📊 Key Highlights & Goodness-of-Fit
- **R² > 0.91 Accuracy:** Consistently achieves over 0.91 coefficient of determination on holdout validation partitions.
- **Robust Outlier Handling:** Winsorization and log-transformations stabilizing residual variances across premium sports trims.
- **Instant Valuation API:** Lightweight model serializations exportable for real-time web pricing engines.
