# File: wine_recommender.py
import pandas as pd

class WineRecommender:
    def __init__(self, csv_path):
        self.data = pd.read_csv(csv_path)

        # Steps define the Q&A sequence
        # We use an array of dicts, each step has 'key', 'question', 'options'
        self.steps = [
            {
                "key": "Color",
                "question": "1. What color wine do you prefer?",
                "options": ["Red", "White", "Rosé", "Sparkling"],
            },
            {
                "key": "AlcoholLevel",
                "question": "2. What is your preferred alcohol range?",
                "options": ["11-12%", "12-13%", "13-14%", "14-15%"]
            },
            {
                "key": "Country",
                "question": "3. Which country do you prefer?",
                "options": ["France", "Spain", "Italy", "Others"]
            },
            {
                "key": "PriceRange",
                "question": "4. Which price range do you want?",
                "options": ["$10-20", "$20-30", "$30-40", "$40-50"]
            },
        ]

        self.criteria = {}
        self.current_step = 0
        self.done = False

    def get_current_question(self):
        """
        Return the text of the current question + options (if any).
        If we have no more questions, return the final recommendation.
        """
        if self.done:
            return "Based on your preferences, here is your recommended wine."

        if self.current_step >= len(self.steps):
            # We have no more steps; finalize
            self.done = True
            return self.recommend_wines()

        step = self.steps[self.current_step]
        question_text = f"{step['question']}\nOptions: {', '.join(step['options'])}"
        return question_text

    def process_answer(self, user_answer):
        """
        Store the user's answer for the current step, handle invalid input, 
        move to the next step if valid. If at the end, produce recommendations.
        """
        if self.done:
            return "We’re already done. Reset if you want to start over."

        # Grab the current step details
        step = self.steps[self.current_step]
        valid_options = [opt.lower() for opt in step["options"]]

        # Basic attempt at handling numeric or partial input
        user_answer_lower = user_answer.strip().lower()

        # If user typed something like "1" or "2", interpret that as an index
        if user_answer_lower.isdigit():
            index = int(user_answer_lower) - 1
            if 0 <= index < len(valid_options):
                user_answer_lower = valid_options[index]

        # Now check if the user_answer_lower is in valid options
        if user_answer_lower not in valid_options:
            # Invalid input => re-ask the same question
            return f"Invalid choice. Please pick one of these: {', '.join(step['options'])}"

        # If valid, store it in criteria with the original capitalized form
        matched_option = step["options"][valid_options.index(user_answer_lower)]
        self.criteria[step["key"]] = matched_option
        self.current_step += 1

        if self.current_step >= len(self.steps):
            # We have reached the end
            self.done = True
            return self.recommend_wines()
        else:
            # Return next question
            return self.get_current_question()

    def recommend_wines(self):
        recommended = self.filter_data(self.data, self.criteria)
        if recommended.empty:
           return "No wines matched your preferences. Try different criteria!"
   
        # Just take the first matching row for simplicity
        row = recommended.iloc[0]
    
        # Safely handle potential missing columns or NaN values
        winery = row.get("Winery", "")
        name = row.get("Name", "")
        vintage = row.get("Vintage", "")
        abv = row.get("Alcohol Level (ABV)", "")
        price = row.get("Price", "")
        country = row.get("Country", "")
    
        # Convert numeric fields as needed (e.g., float to int or round)
        if pd.notnull(vintage):
            # If vintage is float-like, cast to int if it’s a .0
            vintage_str = str(int(vintage)) if float(vintage).is_integer() else str(vintage)
        else:
            vintage_str = ""
    
        # Format a multiline string
        lines = [
            "Based on your preferences, we recommend:",
            f"Winery: {winery}, {country}\n",
            f"{name} {vintage_str}\n".strip(),
            f"{abv}% Alc./vol.\n",
            f"${price}\n"
        ]
        return "\n".join(lines)



    def filter_data(self, data, criteria):
        filtered = data.copy()

        # 1. Filter by color
        # In filter_data()
        if "Color" in criteria:
            color_choice = criteria["Color"].lower()
            filtered = filtered[
                filtered["Colour of Wine"]   # <-- use the real column name
                    .str.lower()
                    .str.contains(color_choice, na=False)
            ]

        # 2. Filter by alcohol range
        if "AlcoholLevel" in criteria:
            # e.g. "14-15%"
            abv_range = criteria["AlcoholLevel"].replace('%', '').split('-')
            if len(abv_range) == 2:
                abv_min, abv_max = float(abv_range[0]), float(abv_range[1])
                filtered["Alcohol Level (ABV)"] = pd.to_numeric(filtered["Alcohol Level (ABV)"], errors='coerce').fillna(-1)
                filtered = filtered[(filtered["Alcohol Level (ABV)"] >= abv_min) & 
                                    (filtered["Alcohol Level (ABV)"] <= abv_max)]

        # 3. Filter by country
        if "Country" in criteria:
            country_choice = criteria["Country"].lower()
            if country_choice == "others":
                filtered = filtered[~filtered["Country"].str.lower().isin(["france", "spain", "italy"])]
            else:
                filtered = filtered[filtered["Country"].str.lower() == country_choice]

        # 4. Filter by price range
        if "PriceRange" in criteria:
            # e.g. "$10-20"
            prange = criteria["PriceRange"].replace('$', '').split('-')
            if len(prange) == 2:
                price_min, price_max = float(prange[0]), float(prange[1])
                # Clean up Price col
                price_col = filtered["Price"].astype(str).str.replace('[\\$,€]', '', regex=True).str.replace(',', '')
                price_col = pd.to_numeric(price_col, errors='coerce')
                price_col = price_col.apply(lambda x: x / 100 if x > 100 else x)
                filtered["PriceNumeric"] = price_col
                # Keep rows in range
                filtered = filtered[
                    (filtered["PriceNumeric"] >= price_min) & 
                    (filtered["PriceNumeric"] <= price_max)
                ]

        return filtered
