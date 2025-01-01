import pandas as pd
import re

def interpret_strength(user_text):
    """
    Interprets 'light', 'strong', 'less than 13%', etc. 
    Returns an ABV string like '11-12%', '12-13%', '13-14%', '14-15%'
    or None if nothing matched.
    """
    text = user_text.lower()

    # "less than X%"
    match_less = re.search(r"less\s+than\s+(\d+)%", text)
    if match_less:
        limit = int(match_less.group(1))
        if limit <= 12:
            return "11-12%"
        elif limit <= 13:
            return "12-13%"
        elif limit <= 14:
            return "13-14%"
        else:
            return "14-15%"

    # synonyms: 'light', 'strong', 'medium'
    if any(word in text for word in ["strong","heavy","high"]):
        return "14-15%"
    if any(word in text for word in ["light","low"]):
        return "11-12%"
    if "medium" in text:
        return "12-13%"

    return None

class WineRecommender:
    def __init__(self, csv_path):
        self.data = pd.read_csv(csv_path)

        self.steps = [
            {
                "key": "Color",
                "question": "What color wine do you prefer?",
                "options": ["Red", "White", "Rosé", "Sparkling"],
            },
            {
                "key": "AlcoholLevel",
                "question": "What is your preferred alcohol range?",
                "options": ["11-12%", "12-13%", "13-14%", "14-15%"]
            },
            {
                "key": "Country",
                "question": "Which country do you prefer?",
                "options": ["France", "Spain", "Italy", "Others"]
            },
            {
                "key": "PriceRange",
                "question": "Which price range do you want?",
                "options": ["$10-20", "$20-30", "$30-40", "$40-50"]
            },
        ]

        # We track each slot’s value here
        self.criteria = {
            "Color": None,
            "AlcoholLevel": None,
            "Country": None,
            "PriceRange": None,
        }

        # The slot we specifically asked last
        self.pending_slot = None

        # If no exact match is found, we remove constraints in this order:
        self.fallback_order = ["PriceRange", "AlcoholLevel", "Country", "Color"]

    def reset(self):
        for slot in self.criteria:
            self.criteria[slot] = None
        self.pending_slot = None

    def handle_message(self, user_text):
        """Main conversation logic."""
        # 1) If there's a pending slot
        if self.pending_slot:
            validation = self.validate_slot_choice(user_text, self.pending_slot)
            if not validation["valid"]:
                step_info = self.get_step_by_key(self.pending_slot)
                return {
                    "message": validation["error"],
                    "options": step_info["options"]
                }
            else:
                self.criteria[self.pending_slot] = validation["choice"]
                self.pending_slot = None

        # 2) parse free text
        self.parse_free_text(user_text)

        # 3) How many slots are filled?
        filled_count = sum(bool(v) for v in self.criteria.values())

        if filled_count == 0:
            # ask first question
            first_step = self.steps[0]
            self.pending_slot = first_step["key"]
            return {
                "message": "Hello! Let's start with your preference.\n" + first_step["question"],
                "options": first_step["options"]
            }

        # If not all 4 are filled, ask the next unfilled step
        if filled_count < 4:
            next_slot = self.find_unfilled_slot()
            if next_slot is not None:
                # Prompt for that slot
                self.pending_slot = next_slot["key"]
                return {
                    "message": f"Got it. {next_slot['question']}",
                    "options": next_slot["options"]
                }
            # If there's no unfilled but somehow filled_count<4, we do a partial filter
            # (rare corner case)

        # If we have all 4 (or partial corner case), attempt strict filter + fallback
        df_result = self.filter_data_with_fallback(self.data, self.criteria)
        if df_result.empty:
            # no match => disclaim
            c = self.criteria
            msg = (
                "No wines matched your preferences, even with partial relaxation.\n"
                f"(Color={c['Color'] or 'None'}, ABV={c['AlcoholLevel'] or 'None'}, "
                f"Country={c['Country'] or 'None'}, Price={c['PriceRange'] or 'None'})\n"
                "Try changing or removing a constraint (e.g. 'Change ABV to 13-14%' or 'Remove country filter')."
            )
            return {"message": msg, "options": []}
        else:
            # We have a row or more
            row = df_result.iloc[0]
            rec_text = self.format_recommendation(row)
            return {
                "message": rec_text,
                "options": []
            }

    def parse_free_text(self, user_text):
        text = user_text.lower()

        # ABV
        if self.criteria["AlcoholLevel"] is None:
            guess = interpret_strength(user_text)
            if guess:
                self.criteria["AlcoholLevel"] = guess
            else:
                for opt in ["11-12%", "12-13%", "13-14%", "14-15%"]:
                    if opt in text:
                        self.criteria["AlcoholLevel"] = opt
                        break

        # Color
        if self.criteria["Color"] is None:
            if "red" in text:
                self.criteria["Color"] = "Red"
            elif "white" in text:
                self.criteria["Color"] = "White"
            elif "rosé" in text or "rose" in text:
                self.criteria["Color"] = "Rosé"
            elif "sparkling" in text:
                self.criteria["Color"] = "Sparkling"

        # Country
        if self.criteria["Country"] is None:
            if "france" in text:
                self.criteria["Country"] = "France"
            elif "spain" in text:
                self.criteria["Country"] = "Spain"
            elif "italy" in text:
                self.criteria["Country"] = "Italy"
            elif "other" in text:
                self.criteria["Country"] = "Others"

        # Price
        if self.criteria["PriceRange"] is None:
            for opt in ["$10-20", "$20-30", "$30-40", "$40-50"]:
                if opt in text:
                    self.criteria["PriceRange"] = opt
                    break
            match = re.search(r"under\s+(\d+)", text)
            if match and self.criteria["PriceRange"] is None:
                num = int(match.group(1))
                if num <= 20:
                    self.criteria["PriceRange"] = "$10-20"
                elif num <= 30:
                    self.criteria["PriceRange"] = "$20-30"
                elif num <= 40:
                    self.criteria["PriceRange"] = "$30-40"
                else:
                    self.criteria["PriceRange"] = "$40-50"

    def validate_slot_choice(self, user_text, slot_key):
        step_info = self.get_step_by_key(slot_key)
        valid_opts = step_info["options"]
        lower_opts = [v.lower() for v in valid_opts]
        t = user_text.lower().strip()

        # number?
        if t.isdigit():
            idx = int(t) - 1
            if 0 <= idx < len(valid_opts):
                return {"valid": True, "choice": valid_opts[idx]}
            else:
                return {"valid": False, "error": f"Invalid choice. Choose one of: {', '.join(valid_opts)}"}
        # direct match?
        if t in lower_opts:
            i = lower_opts.index(t)
            return {"valid": True, "choice": valid_opts[i]}

        return {
            "valid": False,
            "error": f"I didn't understand. Please choose one of: {', '.join(valid_opts)}"
        }

    def get_step_by_key(self, slot_key):
        for s in self.steps:
            if s["key"] == slot_key:
                return s
        return None

    def find_unfilled_slot(self):
        for s in self.steps:
            if self.criteria[s["key"]] is None:
                return s
        return None

    # -------------------------------------------------------------------------
    # Filtering logic
    # -------------------------------------------------------------------------
    def strict_filter_data(self, df, c):
        filt = df.copy()

        color = c["Color"]
        if color:
            if "Colour of Wine" in filt.columns:
                filt = filt[filt["Colour of Wine"].str.lower().str.contains(color.lower(), na=False)]
            elif "Color" in filt.columns:
                filt = filt[filt["Color"].str.lower().str.contains(color.lower(), na=False)]

        abv_choice = c["AlcoholLevel"]
        if abv_choice:
            abv_range = abv_choice.replace('%','').split('-')
            if len(abv_range) == 2:
                abv_min, abv_max = float(abv_range[0]), float(abv_range[1])
                if "Alcohol Level (ABV)" in filt.columns:
                    filt["Alcohol Level (ABV)"] = pd.to_numeric(filt["Alcohol Level (ABV)"], errors='coerce').fillna(-1)
                    filt = filt[(filt["Alcohol Level (ABV)"] >= abv_min) & 
                                (filt["Alcohol Level (ABV)"] <= abv_max)]

        ctry = c["Country"]
        if ctry:
            if ctry.lower() == "others":
                filt = filt[~filt["Country"].str.lower().isin(["france","spain","italy"])]
            else:
                filt = filt[filt["Country"].str.lower() == ctry.lower()]

        price = c["PriceRange"]
        if price:
            prange = price.replace('$','').split('-')
            if len(prange) == 2:
                pmin, pmax = float(prange[0]), float(prange[1])
                pcol = filt["Price"].astype(str).str.replace('[\\$,€]', '', regex=True).str.replace(',', '')
                pcol = pd.to_numeric(pcol, errors='coerce')
                pcol = pcol.apply(lambda x: x/100 if x>100 else x)
                filt["PriceNumeric"] = pcol
                filt = filt[(filt["PriceNumeric"] >= pmin) & (filt["PriceNumeric"] <= pmax)]

        return filt

    def filter_data_with_fallback(self, df, c):
        # 1) Try full constraints
        df_strict = self.strict_filter_data(df, c)
        if not df_strict.empty:
            return df_strict

        # 2) Fallback approach
        temp = dict(c)
        for slot in self.fallback_order:
            if temp[slot] is not None:
                # remove this constraint
                saved_val = temp[slot]
                temp[slot] = None
                df_part = self.strict_filter_data(df, temp)
                if not df_part.empty:
                    return df_part
                # restore and keep going
                temp[slot] = saved_val

        return pd.DataFrame()  # truly empty

    def format_recommendation(self, row):
        winery = row.get("Winery","")
        name = row.get("Name","")
        vintage = row.get("Vintage","")
        abv = row.get("Alcohol Level (ABV)","")
        price = row.get("Price","")
        country = row.get("Country","")

        if pd.notnull(vintage):
            vintage_str = str(int(vintage)) if float(vintage).is_integer() else str(vintage)
        else:
            vintage_str = ""

        lines = [
            "Based on your current preferences, here's a suggestion:",
            f"Winery: {winery}, {country}",
            f"{name} {vintage_str}".strip(),
            f"{abv}% Alc./vol.",
            f"${price}"
        ]
        return "\n".join(lines)




