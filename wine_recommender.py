import pandas as pd
import re

def interpret_strength(user_text):
    """
    Interprets descriptive terms for alcohol strength or specific ABV ranges.
    Returns an ABV string like '11-12%', '12-13%', '13-14%', '14-15%'
    or None if nothing matched.
    """
    text = user_text.lower()
    
    # 1) Handle "less than X%"
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
        
    # 2) Handle descriptive terms
    if any(word in text for word in ["strong", "heavy", "high"]):
        return "14-15%"
    if any(word in text for word in ["light", "low"]):
        return "11-12%"
    if "medium" in text:
        return "12-13%"
    
    # 3) Direct ABV input like "13-14%"
    match_abv = re.search(r"(\d{1,2}-\d{1,2}%)", text)
    if match_abv:
        return match_abv.group(1)
    
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
        
        # Initialize criteria with all slots as None
        self.criteria = {
            "Color": None,
            "AlcoholLevel": None,
            "Country": None,
            "PriceRange": None,
        }
        
        # Track the current slot being prompted
        self.pending_slot = None
        
        # Define the fallback priority order
        self.fallback_order = ["PriceRange", "AlcoholLevel", "Country", "Color"]
        
        # Track removed constraints during fallback
        self.removed_constraints = []
        
    def reset(self):
        """Reset all user preferences."""
        for slot in self.criteria:
            self.criteria[slot] = None
        self.pending_slot = None
        self.removed_constraints = []
        
    def handle_message(self, user_text):
        """Main logic to handle user messages."""
        user_text = user_text.strip()
        
        # 1) Handle pending slot if any
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
                
        # 2) Parse free text to fill any slots
        self.parse_free_text(user_text)
        
        # 3) Count filled slots
        filled_count = sum(bool(v) for v in self.criteria.values())
        
        # 4) Determine next action based on filled slots
        if filled_count == 0:
            # Greet and ask the first preference
            first_step = self.steps[0]
            self.pending_slot = first_step["key"]
            return {
                "message": "Hello! Let's start with your preference.\n" + first_step["question"],
                "options": first_step["options"]
            }
        
        # 5) If not all slots are filled, ask for the next unfilled slot
        if filled_count < 4:
            next_slot = self.find_unfilled_slot()
            if next_slot:
                self.pending_slot = next_slot["key"]
                return {
                    "message": f"Got it. {next_slot['question']}",
                    "options": next_slot["options"]
                }
            
        # 6) If all slots are filled, attempt to filter and recommend
        df_result, removed = self.filter_data_with_fallback(self.data, self.criteria)
        self.removed_constraints = removed
        
        if df_result.empty:
            # No matches even after fallback
            c = self.criteria
            msg = (
                "No wines matched your preferences, even after relaxing some constraints.\n"
                f"(Color={c['Color'] or 'Any'}, ABV={c['AlcoholLevel'] or 'Any'}, "
                f"Country={c['Country'] or 'Any'}, Price={c['PriceRange'] or 'Any'})\n"
                "Try changing or removing a constraint (e.g., 'Change ABV to 13-14%' or 'Remove country filter')."
            )
            return {"message": msg, "options": []}
        else:
            # We have at least one match
            row = df_result.iloc[0]
            rec_text = self.format_recommendation(row)
            
            if self.removed_constraints:
                removed_str = ", ".join(self.removed_constraints)
                rec_text += f"\n\nNote: We relaxed the following constraints to find this match: {removed_str}."
                
            return {
                "message": rec_text,
                "options": []
            }
        
    def parse_free_text(self, user_text):
        """Parse free-form user input to fill in any criteria."""
        text = user_text.lower()
        
        # Attempt to fill AlcoholLevel
        if self.criteria["AlcoholLevel"] is None:
            abv_guess = interpret_strength(user_text)
            if abv_guess:
                self.criteria["AlcoholLevel"] = abv_guess
                
        # Attempt to fill Color
        if self.criteria["Color"] is None:
            if "red" in text:
                self.criteria["Color"] = "Red"
            elif "white" in text:
                self.criteria["Color"] = "White"
            elif "rosé" in text or "rose" in text:
                self.criteria["Color"] = "Rosé"
            elif "sparkling" in text:
                self.criteria["Color"] = "Sparkling"
                
        # Attempt to fill Country
        if self.criteria["Country"] is None:
            if "france" in text:
                self.criteria["Country"] = "France"
            elif "spain" in text:
                self.criteria["Country"] = "Spain"
            elif "italy" in text:
                self.criteria["Country"] = "Italy"
            elif "other" in text or "others" in text:
                self.criteria["Country"] = "Others"
                
        # Attempt to fill PriceRange
        if self.criteria["PriceRange"] is None:
            for opt in ["$10-20", "$20-30", "$30-40", "$40-50"]:
                if opt.lower() in text:
                    self.criteria["PriceRange"] = opt
                    break
            # Handle "under X" price
            match = re.search(r"under\s+\$?(\d+)", text)
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
        """Validate user input for a specific slot."""
        step_info = self.get_step_by_key(slot_key)
        valid_opts = step_info["options"]
        lower_opts = [opt.lower() for opt in valid_opts]
        t = user_text.lower().strip()
        
        # Handle numerical input (e.g., "1" for first option)
        if t.isdigit():
            idx = int(t) - 1
            if 0 <= idx < len(valid_opts):
                return {"valid": True, "choice": valid_opts[idx]}
            else:
                return {"valid": False, "error": f"Invalid choice. Please choose one of: {', '.join(valid_opts)}"}
            
        # Handle direct match
        if t in lower_opts:
            i = lower_opts.index(t)
            return {"valid": True, "choice": valid_opts[i]}
        
        # Handle partial matches or common misspellings
        for opt in valid_opts:
            if opt.lower().startswith(t):
                return {"valid": True, "choice": opt}
            
        # If no valid option matched
        return {
            "valid": False,
            "error": f"I didn't understand. Please choose one of: {', '.join(valid_opts)}"
        }
    
    def get_step_by_key(self, slot_key):
        """Retrieve step information based on slot key."""
        for s in self.steps:
            if s["key"] == slot_key:
                return s
        return None
    
    def find_unfilled_slot(self):
        """Find the next unfilled slot based on the defined order."""
        for step in self.steps:
            if self.criteria[step["key"]] is None:
                return step
        return None
    
    # -------------------------------------------------------------------------
    # Filtering logic
    # -------------------------------------------------------------------------
    def strict_filter_data(self, df, c):
        """Apply all current criteria to filter the DataFrame."""
        filt = df.copy()
        
        # Filter by Color
        color = c["Color"]
        if color:
            if "Colour of Wine" in filt.columns:
                filt = filt[filt["Colour of Wine"].str.lower().str.contains(color.lower(), na=False)]
            elif "Color" in filt.columns:
                filt = filt[filt["Color"].str.lower().str.contains(color.lower(), na=False)]
                
        # Filter by Alcohol Level
        abv_choice = c["AlcoholLevel"]
        if abv_choice:
            abv_range = abv_choice.replace('%','').split('-')
            if len(abv_range) == 2:
                abv_min, abv_max = float(abv_range[0]), float(abv_range[1])
                if "Alcohol Level (ABV)" in filt.columns:
                    filt["Alcohol Level (ABV)"] = pd.to_numeric(filt["Alcohol Level (ABV)"], errors='coerce').fillna(-1)
                    filt = filt[(filt["Alcohol Level (ABV)"] >= abv_min) & 
                                (filt["Alcohol Level (ABV)"] <= abv_max)]
                    
        # Filter by Country
        ctry = c["Country"]
        if ctry:
            if ctry.lower() == "others":
                filt = filt[~filt["Country"].str.lower().isin(["france", "spain", "italy"])]
            else:
                filt = filt[filt["Country"].str.lower() == ctry.lower()]
                
        # Filter by Price Range
        price = c["PriceRange"]
        if price:
            prange = price.replace('$','').split('-')
            if len(prange) == 2:
                pmin, pmax = float(prange[0]), float(prange[1])
                # Clean and convert Price column
                pcol = filt["Price"].astype(str).str.replace('[\\$,€]', '', regex=True).str.replace(',', '')
                pcol = pd.to_numeric(pcol, errors='coerce')
                # No need to divide by 100; assume prices are in dollars
                filt["PriceNumeric"] = pcol
                filt = filt[(filt["PriceNumeric"] >= pmin) & (filt["PriceNumeric"] <= pmax)]
                print(f"Filtering wines with Price between ${pmin} and ${pmax}: Found {len(filt)} wines.")
                
        return filt
    
    def filter_data_with_fallback(self, df, c):
        """
        Attempt to filter data with all criteria.
        If no match, relax constraints based on fallback_order.
        Returns the filtered DataFrame and a list of removed constraints.
        """
        # 1) Attempt strict filtering
        df_strict = self.strict_filter_data(df, c)
        if not df_strict.empty:
            return df_strict, []
        
        # 2) Attempt fallback by removing constraints in fallback_order
        temp_criteria = c.copy()
        removed = []
        
        for slot in self.fallback_order:
            if temp_criteria[slot] is not None:
                # Remove this constraint temporarily
                removed.append(slot)
                temp_criteria[slot] = None
                df_partial = self.strict_filter_data(df, temp_criteria)
                if not df_partial.empty:
                    print(f"Fallback: Removed '{slot}' constraint to find matches.")
                    return df_partial, removed
                
        # 3) No matches found even after fallback
        return pd.DataFrame(), removed
    
    def format_recommendation(self, row):
        """Format the recommendation message based on the DataFrame row."""
        winery = row.get("Winery", "Unknown Winery")
        name = row.get("Name", "Unnamed Wine")
        vintage = row.get("Vintage", "N/A")
        abv = row.get("Alcohol Level (ABV)", "N/A")
        price = row.get("Price", "N/A")
        country = row.get("Country", "Unknown Country")
        
        # Format vintage if it's numeric
        if pd.notnull(vintage):
            try:
                vintage = int(vintage)
            except ValueError:
                vintage = vintage
                
        rec_lines = [
            "Based on your current preferences, here's a suggestion:",
            f"Winery: {winery}, {country}",
            f"{name} {vintage}".strip(),
            f"{abv}% Alc./vol.",
            f"${price}"
        ]
        
        return "\n".join(rec_lines)
    





    