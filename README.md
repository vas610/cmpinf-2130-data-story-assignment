# The Unseen Epidemic — Fatal Accidental Overdoses in Allegheny County

**Course:** CMPINF 2130 – *The Art of Data Visualization*  
**Assignment:** Module 14 — Data Story  
**Student:** Vasanth Madhavan Srinivasa Raghavan  
**Professor:** Dr. Philip J. Grosse  
**Date:** August 9, 2025  

---

## 📖 Introduction
This project is an interactive Streamlit data story exploring fatal accidental overdoses in Allegheny County, PA.  
It uses live data from the Western Pennsylvania Regional Data Center (WPRDC) and presents four complementary visualizations with clear narratives, filters, and a takeaway.  

---

## ✨ Features

- **Data Loaded from API**
- **Filters** for year, sex, and ZIP code (with “ALL” option)  
- **Four core visualizations**:
  1. **Yearly fatalities** (Total/Male/Female trends)  
  2. **Substance composition over time** (stacked area chart)  
  3. **Drug combinations** (treemap)  
  4. **ZIP-level map** of cases (choropleth)  


---

## 🗂️ Repository Structure

```
.
├── streamlit_app.py      # Streamlit application
├── requirements.txt      # Python dependencies
├── README.md             # This file
└── data/
    └── data-dictionary.csv      # Data Dictionary of the columns in the dataset
    └── Fatal-Accidental-Overdoses.csv      # Dataset (Offline copy in case the data API doesn't work)
```

---

## 📦 Installation

**Prerequisites:** Python 3.10+

```bash
# Clone the repo
git clone https://github.com/vas610/cmpinf-2130-data-story-assignment.git
cd cmpinf-2130-data-story-assignment

# Optional virtual environment
python -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

---

## 🚀 Running the App

```bash
streamlit run streamlit_app.py --server.address 0.0.0.0 --server.port 8000
```

---

🧭 How to Use
1. Set filters at the top: choose a year range, sex groups, and optionally a single ZIP (or “ALL ZIPs”).
2. Read KPIs for a quick summary (records, year span, active filters).
3. Explore visuals:
   * Viz 1 (Line): Total/Male/Female trends (toggle series you want to see).
   * Viz 2 (Stacked Area): Substance composition over time.
   * Viz 3 (Treemap): Common drug combinations.
   * Viz 4 (Map): ZIP-level counts (auto-zoom to Allegheny County).
4. Main Takeaway box summarizes recommended actions.
5. References and About sections document methods and sources.

---
## 📺 Live App Hosted on Streamlit Cloud

🖱️ [Streamlit App](https://cmpinf-2130-data-story-assignment-etbn5mfl6kcpdsiyvwf7h3.streamlit.app)

---
## 📝 License
Apache-2.0 license

